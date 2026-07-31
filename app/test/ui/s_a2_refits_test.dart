// S-A2 refit widget tests: optimistic send (bubble + typing indicator appear
// immediately), the ticking recording timer (fake clock), dismissible themed
// banner, and sequential TTS playback invoked via an injected mock player.
import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/adapters/audio_playback.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ports/session_api.dart';
import 'package:study_tutor_app/ui/session_screen.dart';

/// Wraps a SessionApi and gates `turn` on a Completer so a test can observe the
/// optimistic UI while the reply is still in flight.
class GatedSessionApi implements SessionApi {
  GatedSessionApi(this._inner);
  final SessionApi _inner;
  final Completer<void> gate = Completer<void>();

  @override
  Future<TurnResult> turn(String sessionId, String userMessage) async {
    await gate.future;
    return _inner.turn(sessionId, userMessage);
  }

  @override
  Future<StartSessionResult> startSession(
          {String? subject, String? topic, bool resumeIfActive = false}) =>
      _inner.startSession(
          subject: subject, topic: topic, resumeIfActive: resumeIfActive);

  @override
  Future<List<SessionSummary>> listSessions({SessionStatus? status, int? limit}) =>
      _inner.listSessions(status: status, limit: limit);

  @override
  Future<ResumeSessionResult> resumeSession(String sessionId) =>
      _inner.resumeSession(sessionId);

  @override
  Future<TurnsSinceResult> turnsSince(String sessionId, int since) =>
      _inner.turnsSince(sessionId, since);

  @override
  Future<SessionStatusResult> sessionStatus(String sessionId) =>
      _inner.sessionStatus(sessionId);

  @override
  Future<EndSessionResult> endSession(String sessionId) =>
      _inner.endSession(sessionId);
}

/// Records playback invocations without touching platform channels.
class MockAudioPlayback implements AudioPlayback {
  final List<List<Uint8List>> played = [];
  int stopCalls = 0;

  @override
  Future<void> playSequential(List<Uint8List> chunks) async =>
      played.add(chunks);

  @override
  Future<void> stop() async => stopCalls++;

  @override
  Future<void> dispose() async {}
}

void main() {
  late FakeIdentityProvider identity;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn();
  });

  testWidgets('optimistic send: user bubble + typing indicator appear before '
      'the reply arrives', (tester) async {
    final inner = FakeSessionApi(identity: identity);
    final started = await inner.startSession(subject: 'english');
    final gated = GatedSessionApi(inner);

    await tester.pumpWidget(MaterialApp(
      home: SessionScreen(
        identity: identity,
        sessionApi: gated,
        voiceApi: FakeVoiceApi(),
        sessionId: started.sessionId,
        subject: 'english',
      ),
    ));

    await tester.enterText(find.byType(TextField), 'hello there');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pump(); // one frame — the turn is still gated

    // The optimistic bubble and the typing indicator are already on screen.
    expect(find.text('hello there'), findsOneWidget,
        reason: 'the user bubble shows immediately, no frozen wall');
    expect(find.byKey(const Key('typing-indicator')), findsOneWidget,
        reason: 'a typing indicator shows while awaiting the reply');

    // Let the reply land.
    gated.gate.complete();
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('typing-indicator')), findsNothing,
        reason: 'the indicator clears once the reply arrives');
    expect(find.text(FakeSessionApi.cannedReplies[0]), findsOneWidget);
    // The user message is still there exactly once (optimistic → confirmed).
    expect(find.text('hello there'), findsOneWidget);
  });

  testWidgets('recording timer ticks via the injected clock', (tester) async {
    var now = DateTime(2026, 7, 12, 9, 0, 0);

    await tester.pumpWidget(MaterialApp(
      home: SessionScreen(
        identity: identity,
        sessionApi: FakeSessionApi(identity: identity),
        voiceApi: FakeVoiceApi(),
        sessionId: 'test-session',
        voiceRecorder: FakeVoiceRecorder(),
        clock: () => now,
      ),
    ));

    // Start recording — elapsed starts at 0s.
    await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
    await tester.pump();
    expect(find.text('0s'), findsOneWidget);

    // Advance the clock and let the periodic ticker fire.
    now = now.add(const Duration(seconds: 3));
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('3s'), findsOneWidget,
        reason: 'Timer.periodic re-reads the clock and updates the label');

    // Stop recording so no timers/tickers outlive the test.
    await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
    await tester.pumpAndSettle();
  });

  testWidgets('a themed banner is dismissible', (tester) async {
    final flaky = FlakyVoiceApi(FakeVoiceApi());
    flaky.failing.add('voiceTurn');
    flaky.errorToThrow = const UnsupportedAudioFormat();

    await tester.pumpWidget(MaterialApp(
      home: SessionScreen(
        identity: identity,
        sessionApi: FakeSessionApi(identity: identity),
        voiceApi: flaky,
        sessionId: 'test-session',
        voiceRecorder: FakeVoiceRecorder(),
      ),
    ));

    // Trigger a voice error → banner.
    await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
    await tester.pump();
    await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
    await tester.pumpAndSettle();

    expect(find.byType(MaterialBanner), findsOneWidget);
    expect(
      find.text("That audio format isn't supported — try recording again"),
      findsOneWidget,
    );

    // Dismiss it.
    await tester.tap(find.widgetWithText(TextButton, 'Dismiss'));
    await tester.pumpAndSettle();

    expect(find.byType(MaterialBanner), findsNothing);
    expect(
      find.text("That audio format isn't supported — try recording again"),
      findsNothing,
    );
  });

  testWidgets('TTS: audio parts are fetched and played sequentially via the '
      'injected player', (tester) async {
    final player = MockAudioPlayback();

    await tester.pumpWidget(MaterialApp(
      home: SessionScreen(
        identity: identity,
        sessionApi: FakeSessionApi(identity: identity),
        voiceApi: FakeVoiceApi(),
        sessionId: 'test-session',
        voiceRecorder: FakeVoiceRecorder(),
        player: player,
      ),
    ));

    // Do a voice turn: the fake recorder returns canned bytes on stop().
    await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
    await tester.pump();
    await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
    await tester.pumpAndSettle();

    // The fake returns exactly one AudioAnswerPart → one playback call, one
    // chunk fetched.
    expect(player.played, hasLength(1),
        reason: 'playSequential invoked once for the spoken answer');
    expect(player.played.single, hasLength(1),
        reason: 'the single audio chunk was fetched and handed to the player');
  });
}
