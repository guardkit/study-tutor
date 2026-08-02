// Phase-2 scope §3.2: TransportError → the fourth treatment — a non-crashing
// "connection problem — try again" surface that navigates nowhere and
// preserves unsent input. Induced with a throwing SessionApi decorator (no
// network, hermetic): the flake is per-verb and reversible, so every test
// can also prove the retry works once the "connection" returns.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ports/session_api.dart';
import 'package:study_tutor_app/ui/app.dart';
import 'package:study_tutor_app/ui/home_screen.dart';
import 'package:study_tutor_app/ui/session_screen.dart';

/// Delegates to the wrapped fake, except that verbs named in [failing]
/// throw TransportError — the hermetic stand-in for "the network died on
/// this call". Mutate [failing] mid-test to break and then restore the
/// connection.
class FlakySessionApi implements SessionApi {
  FlakySessionApi(this._inner);

  final SessionApi _inner;
  final Set<String> failing = {};

  Future<T> _call<T>(String verb, Future<T> Function() body) async {
    if (failing.contains(verb)) {
      throw const TransportError();
    }
    return body();
  }

  @override
  Future<StartSessionResult> startSession({
    String? subject,
    String? topic,
    bool resumeIfActive = false,
  }) =>
      _call(
          'startSession',
          () => _inner.startSession(
              subject: subject, topic: topic, resumeIfActive: resumeIfActive));

  @override
  Future<List<SessionSummary>> listSessions(
          {SessionStatus? status, int? limit}) =>
      _call('listSessions',
          () => _inner.listSessions(status: status, limit: limit));

  @override
  Future<ResumeSessionResult> resumeSession(String sessionId) =>
      _call('resumeSession', () => _inner.resumeSession(sessionId));

  @override
  Future<TurnsSinceResult> turnsSince(String sessionId, int since) =>
      _call('turnsSince', () => _inner.turnsSince(sessionId, since));

  @override
  Future<TurnResult> turn(String sessionId, String userMessage) =>
      _call('turn', () => _inner.turn(sessionId, userMessage));

  @override
  Future<SessionStatusResult> sessionStatus(String sessionId) =>
      _call('sessionStatus', () => _inner.sessionStatus(sessionId));

  @override
  Future<EndSessionResult> endSession(String sessionId) =>
      _call('endSession', () => _inner.endSession(sessionId));
}

void main() {
  late FakeIdentityProvider identity;
  late FlakySessionApi sessionApi;
  late FakeVoiceApi voiceApi;

  Future<void> boot(WidgetTester tester) async {
    identity = FakeIdentityProvider();
    sessionApi = FlakySessionApi(FakeSessionApi(identity: identity));
    voiceApi = FakeVoiceApi();
    await tester
        .pumpWidget(StudyTutorApp(identity: identity, sessionApi: sessionApi, voiceApi: voiceApi));
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
  }

  Future<void> dismissDialog(WidgetTester tester) async {
    expect(find.text('Connection problem'), findsOneWidget);
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
  }

  testWidgets('session send: dialog, unsent input preserved, retry sends it',
      (tester) async {
    await boot(tester);
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    sessionApi.failing.add('turn');
    await tester.enterText(find.byType(TextField), 'are you there?');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    await dismissDialog(tester);
    // Still on the session screen, nothing appended, message still typed.
    expect(find.text('English'), findsOneWidget);
    expect(
      find.descendant(
          of: find.byType(ListView), matching: find.text('are you there?')),
      findsNothing,
      reason: 'the failed turn must not be appended to the transcript',
    );
    expect(tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'are you there?',
        reason: 'the unsent input is preserved for the retry');
    expect(find.text('Session ended'), findsNothing,
        reason: 'a transport failure is not an ended session');

    // The connection returns: tapping send again delivers the same message.
    sessionApi.failing.remove('turn');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();
    expect(
      find.descendant(
          of: find.byType(ListView), matching: find.text('are you there?')),
      findsOneWidget,
    );
  });

  testWidgets('session end: dialog, session NOT ended, retry ends it',
      (tester) async {
    await boot(tester);
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    sessionApi.failing.add('endSession');
    await tester.tap(find.text('End session'));
    await tester.pumpAndSettle();

    await dismissDialog(tester);
    expect(find.text('End session'), findsOneWidget,
        reason: 'the end never happened — the affordance must survive');
    expect(find.text('Session ended'), findsNothing);
    expect(tester.widget<TextField>(find.byType(TextField)).enabled, isTrue,
        reason: 'still an active session — input stays usable');

    sessionApi.failing.remove('endSession');
    await tester.tap(find.text('End session'));
    await tester.pumpAndSettle();
    expect(find.text('Session ended'), findsOneWidget);
  });

  testWidgets('home refresh: dialog, home survives, pull-to-refresh retries',
      (tester) async {
    identity = FakeIdentityProvider();
    final inner = FakeSessionApi(identity: identity);
    sessionApi = FlakySessionApi(inner);
    voiceApi = FakeVoiceApi();
    // Seed one active session "server-side" before the app ever lists.
    await identity.signIn();
    await inner.startSession(subject: 'maths');
    await identity.signOut();
    await tester
        .pumpWidget(StudyTutorApp(identity: identity, sessionApi: sessionApi, voiceApi: voiceApi));

    // The list call fails from the very first refresh (home's initState).
    sessionApi.failing.add('listSessions');
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();

    await dismissDialog(tester);
    expect(find.text('Hi, Lilymay'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Start new session'),
        findsOneWidget,
        reason: 'home is intact and usable behind the dismissed dialog');
    expect(find.text(homeEmptyState), findsOneWidget,
        reason: 'the failed refresh leaves the (stale) empty state');

    // The connection returns: pull-to-refresh is the retry gesture for the
    // list call — the seeded session must now appear.
    sessionApi.failing.remove('listSessions');
    await tester.fling(find.byType(ListView), const Offset(0, 300), 1000);
    await tester.pumpAndSettle();
    expect(find.text('Resume'), findsOneWidget,
        reason: 'retry re-lists and surfaces the active session');
  });

  testWidgets('home start: dialog, stays home, retry opens the session',
      (tester) async {
    await boot(tester);

    sessionApi.failing.add('startSession');
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    await dismissDialog(tester);
    expect(find.text('Hi, Lilymay'), findsOneWidget);
    // Scoped to the screen type: Home's own subject picker legitimately shows
    // 'English' since Lane 1 step 2, so the bare text is no longer proof.
    expect(find.byType(SessionScreen), findsNothing,
        reason: 'nothing was started — no session screen was pushed');

    // `_busy` must have been released for the retry to work at all.
    sessionApi.failing.remove('startSession');
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    expect(find.text('English'), findsOneWidget);
  });

  testWidgets(
      'home resume: connection dialog (not "can\'t open"), row kept, '
      'retry resumes with the transcript intact', (tester) async {
    await boot(tester);
    // Seed an active session with one exchange, then come back home.
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'first question');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Resume'), findsOneWidget);

    sessionApi.failing.add('resumeSession');
    await tester.tap(find.text('Resume'));
    await tester.pumpAndSettle();

    expect(find.text("Can't open this session"), findsNothing,
        reason: 'a dead network is not the forbidden/not-found surface');
    await dismissDialog(tester);
    expect(find.text('Resume'), findsOneWidget,
        reason: 'the session may be perfectly resumable — the row stays');

    sessionApi.failing.remove('resumeSession');
    await tester.tap(find.text('Resume'));
    await tester.pumpAndSettle();
    expect(find.text('English'), findsOneWidget);
    expect(
      find.descendant(
          of: find.byType(ListView), matching: find.text('first question')),
      findsOneWidget,
      reason: 'resume after retry loads the ordered transcript',
    );
  });
}
