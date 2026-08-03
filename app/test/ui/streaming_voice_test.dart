// Streaming voice widget tests (TASK-STREAM-001): the session screen consumes
// VoiceApi.voiceTurnStream so the transcript, answer tokens, and audio parts
// arrive live — replacing the batch "Recording sent…" wall. Also covers the
// batch fallback (stream error → the existing voiceTurn safety net) and that
// batch stays the default when the streamVoice gate is off.
import 'dart:async';
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

/// A stream that ends mid-turn WITHOUT §7's terminal `done` and throws
/// nothing — the server-closed-mid-turn shape that stranded the typing
/// indicator on the 2026-08-03 live walk. Batch stays canned via the parent.
class NoDoneVoiceApi extends FakeVoiceApi {
  @override
  Stream<VoiceTurnEvent> voiceTurnStream(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  }) async* {
    yield TranscriptEvent(
      transcript: 'What is the quadratic formula?',
      isFinal: true,
    );
    yield TextTokenEvent(token: 'Half an ');
  }
}

/// A stream that stays open but never emits — the silent-stall strand shape.
class StalledVoiceApi extends FakeVoiceApi {
  final _controller = StreamController<VoiceTurnEvent>();

  @override
  Stream<VoiceTurnEvent> voiceTurnStream(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  }) =>
      _controller.stream;
}

/// A player whose playSequential does not complete until the test opens its
/// gate — models a piece that is still audibly playing (Rich's 2026-08-03
/// walk: pieces are 8–15s of audio, frames arrive ~3s apart).
class GatedAudioPlayback implements AudioPlayback {
  final List<List<Uint8List>> played = [];
  final List<Completer<void>> gates = [];
  int stopCalls = 0;

  @override
  Future<void> playSequential(List<Uint8List> chunks) {
    played.add(chunks);
    final gate = Completer<void>();
    gates.add(gate);
    return gate.future;
  }

  @override
  Future<void> stop() async => stopCalls++;

  @override
  Future<void> dispose() async {}
}

/// Emits two audio_ref pieces (then done); chunk-a's FETCH can be delayed
/// past chunk-b's to model the fetch-completion race the frame-order pin
/// closes.
class TwoAudioRefVoiceApi extends FakeVoiceApi {
  TwoAudioRefVoiceApi({this.chunkAFetchDelay = Duration.zero});

  final Duration chunkAFetchDelay;

  @override
  Stream<VoiceTurnEvent> voiceTurnStream(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  }) async* {
    yield TranscriptEvent(
      transcript: 'What is the quadratic formula?',
      isFinal: true,
    );
    yield TextTokenEvent(token: 'Answer ');
    yield AudioPartEvent(seq: 0, chunkId: 'chunk-a');
    yield AudioPartEvent(seq: 1, chunkId: 'chunk-b');
    yield const TurnCompleteEvent();
  }

  @override
  Future<Uint8List> fetchAudioChunk(String sessionId, String chunkId) async {
    if (chunkId == 'chunk-a') {
      if (chunkAFetchDelay > Duration.zero) {
        await Future<void>.delayed(chunkAFetchDelay);
      }
      return Uint8List.fromList([0xA]);
    }
    return Uint8List.fromList([0xB]);
  }
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
    Duration streamEventTimeout = const Duration(seconds: 90),
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
        streamEventTimeout: streamEventTimeout,
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

    testWidgets('a second audio_ref queues behind the playing piece — it '
        'NEVER interrupts (2026-08-03 walk: piece 2 cut piece 1 off)', (
      tester,
    ) async {
      final player = GatedAudioPlayback();
      await tester.pumpWidget(
        makeScreen(voice: TwoAudioRefVoiceApi(), player: player),
      );

      await doVoiceTurn(tester);
      await tester.pump(const Duration(milliseconds: 50));
      await tester.pump(const Duration(milliseconds: 50));

      // Both frames have arrived and fetched; piece 1 is mid-play (its gate
      // is still shut). Piece 2 must be waiting, not playing.
      expect(player.played, hasLength(1),
          reason: 'the second piece waits for the first to FINISH');
      expect(player.played.single.single, [0xA]);

      // Piece 1 finishes → piece 2 plays, in order.
      player.gates[0].complete();
      await tester.pump();
      await tester.pump();
      expect(player.played, hasLength(2));
      expect(player.played[1].single, [0xB]);

      player.gates[1].complete();
      await tester.pumpAndSettle();
    });

    testWidgets('audio plays in FRAME order even when the first fetch '
        'completes second', (tester) async {
      final player = GatedAudioPlayback();
      await tester.pumpWidget(makeScreen(
        voice: TwoAudioRefVoiceApi(
          chunkAFetchDelay: const Duration(milliseconds: 300),
        ),
        player: player,
      ));

      await doVoiceTurn(tester);
      await tester.pump(const Duration(milliseconds: 50));

      // chunk-b's fetch has landed; chunk-a's is still in flight. Nothing
      // may play yet — frame order, not fetch-completion order.
      expect(player.played, isEmpty,
          reason: 'a later piece that fetched first must still wait its turn');

      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump();
      expect(player.played, hasLength(1));
      expect(player.played.single.single, [0xA],
          reason: 'piece 1 plays first regardless of fetch timing');

      player.gates[0].complete();
      await tester.pump();
      await tester.pump();
      expect(player.played[1].single, [0xB]);

      player.gates[1].complete();
      await tester.pumpAndSettle();
    });

    testWidgets('a stream that ends WITHOUT the terminal done falls back to '
        'batch — never a stranded turn (2026-08-03 live strand)', (
      tester,
    ) async {
      await tester.pumpWidget(
        makeScreen(voice: NoDoneVoiceApi(), player: MockAudioPlayback()),
      );

      await doVoiceTurn(tester);
      await tester.pumpAndSettle();

      // The batch safety net committed the turn; nothing half-streamed left.
      expect(find.text('What is the quadratic formula?'), findsOneWidget);
      expect(
        find.textContaining("Let's break that down together"),
        findsOneWidget,
      );
      expect(find.byKey(const Key('streaming-answer')), findsNothing);
      final mic = tester.widget<IconButton>(
        find.widgetWithIcon(IconButton, Icons.mic),
      );
      expect(mic.onPressed, isNotNull,
          reason: 'no permanently-stuck typing indicator');
    });

    testWidgets('a stream that goes silent hits the event timeout and falls '
        'back to batch', (tester) async {
      await tester.pumpWidget(makeScreen(
        voice: StalledVoiceApi(),
        player: MockAudioPlayback(),
        streamEventTimeout: const Duration(milliseconds: 200),
      ));

      await doVoiceTurn(tester);
      await tester.pump(const Duration(milliseconds: 250));
      await tester.pumpAndSettle();

      expect(
        find.textContaining("Let's break that down together"),
        findsOneWidget,
        reason: 'the stall is bounded by streamEventTimeout, then batch runs',
      );
      expect(find.byKey(const Key('streaming-answer')), findsNothing);
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
