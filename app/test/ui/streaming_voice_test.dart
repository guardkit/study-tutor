// Streaming voice widget tests (TASK-STREAM-001): the session screen consumes
// VoiceApi.voiceTurnStream so the transcript, answer tokens, and audio parts
// arrive live — replacing the batch "Recording sent…" wall. Also covers the
// batch fallback (stream error → the existing voiceTurn safety net) and that
// batch stays the default when the streamVoice gate is off.
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/adapters/audio_playback.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ports/voice_api.dart';
import 'package:study_tutor_app/ui/session_screen.dart';

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
  late FakeSessionApi sessionApi;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn();
    sessionApi = FakeSessionApi(identity: identity);
  });

  Widget makeScreen({
    required VoiceApi voice,
    AudioPlayback? player,
    bool streamVoice = true,
    String sessionId = 'test-session',
  }) {
    return MaterialApp(
      home: SessionScreen(
        identity: identity,
        sessionApi: sessionApi,
        sessionId: sessionId,
        voiceApi: voice,
        voiceRecorder: FakeVoiceRecorder(),
        player: player,
        streamVoice: streamVoice,
      ),
    );
  }

  Future<void> doVoiceTurn(WidgetTester tester) async {
    await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
    await tester.pump();
    await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
  }

  group('streaming voice turn', () {
    testWidgets('transcript finalizes, tokens accumulate, audio plays, '
        'turn_complete commits the exchange', (tester) async {
      final player = MockAudioPlayback();
      await tester.pumpWidget(makeScreen(voice: FakeVoiceApi(), player: player));

      await doVoiceTurn(tester);
      await tester.pumpAndSettle();

      // The finalized transcript is the committed user turn.
      expect(find.text('What is the quadratic formula?'), findsOneWidget);
      // The streamed tokens accumulated into the tutor answer.
      expect(
        find.textContaining("Let's break that down together"),
        findsOneWidget,
      );
      // turn_complete finalized: no live streaming bubble remains.
      expect(find.byKey(const Key('streaming-answer')), findsNothing);

      // The single AudioPartEvent was fetched and handed to the player.
      expect(player.played, isNotEmpty,
          reason: 'audio parts start playing as they arrive');
      expect(player.played.expand((c) => c).length, 1,
          reason: 'the fake emits exactly one audio chunk');

      // Mic is re-enabled after the turn finalizes.
      final mic = tester.widget<IconButton>(
        find.widgetWithIcon(IconButton, Icons.mic),
      );
      expect(mic.onPressed, isNotNull);
    });

    testWidgets('the tutor answer streams in live — a growing bubble appears '
        'before the turn is committed', (tester) async {
      await tester.pumpWidget(
        makeScreen(voice: FakeVoiceApi(), player: MockAudioPlayback()),
      );

      await doVoiceTurn(tester);
      await tester.pump(); // transcript event lands
      // The transcript already shows as the user bubble, mid-stream.
      expect(find.text('What is the quadratic formula?'), findsOneWidget);

      // Step through a couple of the fake's 10 ms token gaps: the live answer
      // bubble is on screen and growing before turn_complete.
      await tester.pump(const Duration(milliseconds: 12));
      await tester.pump(const Duration(milliseconds: 12));
      expect(find.byKey(const Key('streaming-answer')), findsOneWidget,
          reason: 'the answer renders token-by-token, not all at once');

      // Once the stream completes, the live bubble is committed and cleared.
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('streaming-answer')), findsNothing);
      expect(
        find.textContaining("Let's break that down together"),
        findsOneWidget,
      );
    });
  });

  group('fallback to batch', () {
    testWidgets('a stream error falls back to the batch voiceTurn path', (
      tester,
    ) async {
      final flaky = FlakyVoiceApi(FakeVoiceApi());
      // Only the STREAM fails — the batch voiceTurn safety net stays healthy.
      flaky.failing.add('voiceTurnStream');
      flaky.errorToThrow = const TransportError();

      await tester.pumpWidget(
        makeScreen(voice: flaky, player: MockAudioPlayback()),
      );

      await doVoiceTurn(tester);
      await tester.pumpAndSettle();

      // The batch path produced the canned transcript + answer — the turn
      // still lands despite the streaming failure.
      expect(find.text('What is the quadratic formula?'), findsOneWidget);
      expect(
        find.textContaining("Let's break that down together"),
        findsOneWidget,
      );
      // No half-streamed bubble left behind.
      expect(find.byKey(const Key('streaming-answer')), findsNothing);

      // Mic is usable again after the fallback settles.
      final mic = tester.widget<IconButton>(
        find.widgetWithIcon(IconButton, Icons.mic),
      );
      expect(mic.onPressed, isNotNull);
    });

    testWidgets('a stream VoiceUnavailable falls back to batch, which surfaces '
        'the degraded-voice banner', (tester) async {
      final flaky = FlakyVoiceApi(FakeVoiceApi());
      // Both paths report unavailable: the stream errors, batch confirms it.
      flaky.failing.addAll({'voiceTurnStream', 'voiceTurn'});
      flaky.errorToThrow = const VoiceUnavailable();

      await tester.pumpWidget(
        makeScreen(voice: flaky, player: MockAudioPlayback()),
      );

      await doVoiceTurn(tester);
      await tester.pumpAndSettle();

      expect(
        find.text(
          "Spoken answers aren't available right now — text still works",
        ),
        findsOneWidget,
      );
    });
  });

  group('gate: batch is the default', () {
    testWidgets('with streamVoice off, a failing stream is never touched — the '
        'batch path runs', (tester) async {
      final flaky = FlakyVoiceApi(FakeVoiceApi());
      // If the screen wrongly used the stream, this would blow up the turn.
      flaky.failing.add('voiceTurnStream');
      flaky.errorToThrow = const TransportError();

      await tester.pumpWidget(
        makeScreen(voice: flaky, player: MockAudioPlayback(), streamVoice: false),
      );

      await doVoiceTurn(tester);
      await tester.pumpAndSettle();

      // Batch was used (default): the turn succeeds and no stream bubble shows.
      expect(find.text('What is the quadratic formula?'), findsOneWidget);
      expect(find.byKey(const Key('streaming-answer')), findsNothing);
    });
  });
}
