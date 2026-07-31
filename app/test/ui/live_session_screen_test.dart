// live-mirror (spec: BUILD): a read-only mirror of the session the Reachy robot
// is driving. Two FakeSessionApi clients over ONE shared InMemorySessionStore
// model the two devices — the "robot" advances the session, the "phone"
// (LiveSessionScreen) polls and mirrors it. Fully hermetic: no real network, no
// wall-clock timers (polling runs on the injectable interval, driven by pump).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ports/session_api.dart';
import 'package:study_tutor_app/ui/live_session_screen.dart';
import 'package:study_tutor_app/ui/transcript_view.dart';

void main() {
  const interval = Duration(seconds: 3);

  late FakeIdentityProvider identity;
  late InMemorySessionStore store;
  late FakeSessionApi robot; // the device driving the session (Reachy)
  late FakeSessionApi phone; // the watcher's own client over the same store
  late FakeVoiceApi voiceApi;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn();
    store = InMemorySessionStore();
    robot = FakeSessionApi(identity: identity, store: store);
    phone = FakeSessionApi(identity: identity, store: store);
    voiceApi = FakeVoiceApi();
  });

  Widget wrap(String sessionId, {SessionApi? api}) => MaterialApp(
        home: LiveSessionScreen(
          identity: identity,
          sessionApi: api ?? phone,
          voiceApi: voiceApi,
          sessionId: sessionId,
          subject: 'english',
          pollInterval: interval,
        ),
      );

  // Fire one poll cycle: advance the fake clock to the periodic tick, then let
  // the status + resume futures resolve and the tree rebuild.
  Future<void> tick(WidgetTester tester) async {
    await tester.pump(interval);
    await tester.pump();
  }

  testWidgets('mirrors a growing session then stops gracefully on end',
      (tester) async {
    final started = await robot.startSession(subject: 'english');
    await robot.turn(started.sessionId, 'q0'); // one turn before watching

    await tester.pumpWidget(wrap(started.sessionId));
    await tester.pump(); // build
    await tester.pump(); // initial resume resolves

    // Initial transcript is mirrored, read-only (no input bar), LIVE badge on.
    expect(find.text('q0'), findsOneWidget);
    expect(find.text(FakeSessionApi.cannedReplies[0]), findsOneWidget);
    expect(find.text('LIVE'), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
    expect(find.byIcon(Icons.send), findsNothing);

    // The transcript view instance we will assert survives the appends.
    final transcriptState = tester.state(find.byType(TranscriptView));

    // The robot takes another turn; the poll should append it.
    await robot.turn(started.sessionId, 'q1');
    await tick(tester);

    expect(find.text('q0'), findsOneWidget, reason: 'old turn kept');
    expect(find.text('q1'), findsOneWidget, reason: 'new turn appended');
    expect(find.text(FakeSessionApi.cannedReplies[1]), findsOneWidget);
    expect(
      identical(transcriptState, tester.state(find.byType(TranscriptView))),
      isTrue,
      reason: 'turns append into the SAME TranscriptView — no full rebuild',
    );

    // A quiet tick (no new turns) must not disturb the transcript.
    await tick(tester);
    expect(find.text('q1'), findsOneWidget);

    // The robot ends the session: the mirror stops and shows the ended note,
    // keeping the last transcript.
    await robot.endSession(started.sessionId);
    await tick(tester);

    expect(find.text('Session ended'), findsOneWidget);
    expect(find.text('LIVE'), findsNothing);
    expect(find.text('q0'), findsOneWidget);
    expect(find.text('q1'), findsOneWidget);

    // Polling has stopped: even after many more intervals nothing changes and —
    // crucially — no timer is left pending (the framework fails teardown on a
    // leaked timer, so reaching the end of the test IS the assertion).
    await tick(tester);
    await tick(tester);
    expect(find.text('Session ended'), findsOneWidget);
    await tester.pumpAndSettle();
  });

  testWidgets('opens an already-ended session read-only, without polling',
      (tester) async {
    final started = await robot.startSession(subject: 'english');
    await robot.turn(started.sessionId, 'q0');
    await robot.endSession(started.sessionId);

    await tester.pumpWidget(wrap(started.sessionId));
    await tester.pump();
    await tester.pump();

    // Transcript is shown, ended note present, no LIVE badge, no input bar.
    expect(find.text('q0'), findsOneWidget);
    expect(find.text('Session ended'), findsOneWidget);
    expect(find.text('LIVE'), findsNothing);
    expect(find.byType(TextField), findsNothing);

    // No polling was started (no pending timer) — advancing the clock is inert
    // and teardown would fail if a timer had leaked.
    await tick(tester);
    await tester.pumpAndSettle();
  });

  testWidgets('a transient transport error mid-poll keeps the last transcript '
      'and keeps polling', (tester) async {
    final started = await robot.startSession(subject: 'english');
    await robot.turn(started.sessionId, 'q0');

    final flaky = _FlakyStatusApi(phone);
    await tester.pumpWidget(wrap(started.sessionId, api: flaky));
    await tester.pump();
    await tester.pump();
    expect(find.text('q0'), findsOneWidget);

    // Next status poll throws TransportError: no dialog, transcript unchanged.
    flaky.failNextStatus = true;
    await robot.turn(started.sessionId, 'q1');
    await tick(tester);
    expect(find.text('Connection problem'), findsNothing,
        reason: 'a watcher is not nagged on a single flaky beat');
    expect(find.text('q1'), findsNothing,
        reason: 'the dropped poll did not fetch the new turn yet');
    expect(find.text('q0'), findsOneWidget, reason: 'last transcript kept');

    // The next (recovered) poll catches up.
    await tick(tester);
    expect(find.text('q1'), findsOneWidget);

    // Unmount to cancel the live timer cleanly.
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
  });

  testWidgets('cancels the poll timer on dispose while still active',
      (tester) async {
    final started = await robot.startSession(subject: 'english');
    await robot.turn(started.sessionId, 'q0');

    await tester.pumpWidget(wrap(started.sessionId));
    await tester.pump();
    await tester.pump();
    expect(find.text('LIVE'), findsOneWidget); // polling is live

    // Navigate away: dispose must cancel the timer, or teardown fails on a
    // leaked pending timer.
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
  });
}

/// A [SessionApi] decorator over a real [FakeSessionApi] that can be told to
/// throw a [TransportError] on the very next [sessionStatus] — modelling a
/// single dropped poll beat. Every other verb delegates unchanged.
class _FlakyStatusApi implements SessionApi {
  _FlakyStatusApi(this._inner);

  final SessionApi _inner;
  bool failNextStatus = false;

  @override
  Future<SessionStatusResult> sessionStatus(String sessionId) {
    if (failNextStatus) {
      failNextStatus = false;
      throw const TransportError();
    }
    return _inner.sessionStatus(sessionId);
  }

  @override
  Future<ResumeSessionResult> resumeSession(String sessionId) =>
      _inner.resumeSession(sessionId);

  @override
  Future<StartSessionResult> startSession({
    String? subject,
    String? topic,
    bool resumeIfActive = false,
  }) =>
      _inner.startSession(
          subject: subject, topic: topic, resumeIfActive: resumeIfActive);

  @override
  Future<List<SessionSummary>> listSessions({
    SessionStatus? status,
    int? limit,
  }) =>
      _inner.listSessions(status: status, limit: limit);

  @override
  Future<TurnResult> turn(String sessionId, String userMessage) =>
      _inner.turn(sessionId, userMessage);

  @override
  Future<EndSessionResult> endSession(String sessionId) =>
      _inner.endSession(sessionId);
}
