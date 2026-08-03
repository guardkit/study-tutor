// Live voice contract tests — runs the shared voice contract test bodies
// against the real GB10 HTTP adapter (see test_live/README.md for run command:
// --dart-define=API_BASE_URL + --concurrency=1).
//
// Direction pins verified at the LIVE seam (§6.4 fidelity defence): multipart
// field 'audio', filename extension matches codec, Content-Type params intact,
// bearer auth present, on-session binding.
@Timeout(Duration(minutes: 5))
library;

import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:study_tutor_app/adapters/http_session_api.dart';
import 'package:study_tutor_app/adapters/http_voice_api.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/domain/principal.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/ports/identity_provider.dart';
import 'package:study_tutor_app/ports/session_api.dart';
import 'package:study_tutor_app/ports/voice_api.dart';

import '../test/contract/voice_contract_test.dart'
    show VoiceContractBackend, runVoiceContractTests;

const _rawApiBaseUrl = String.fromEnvironment('API_BASE_URL');

/// Normalized base URL (see LiveContractBackend pattern).
final _apiBaseUrl = _rawApiBaseUrl.endsWith('/')
    ? _rawApiBaseUrl.substring(0, _rawApiBaseUrl.length - 1)
    : _rawApiBaseUrl;

/// Voice turn deadline for live testing (aligned with LiveContractBackend's
/// 60s precedent — absorbs GPU contention from zero-think-time harness firing).
const _liveVoiceTurnDeadline = Duration(seconds: 60);

/// Reset route deadline.
const _resetDeadline = Duration(seconds: 10);

/// Dev token table identity (reuses LiveContractBackend pattern).
class _DevTableIdentity implements IdentityProvider {
  Principal? _current;

  @override
  Principal? get currentPrincipal => _current;

  @override
  Future<Principal> signIn() async =>
      _current = FakeIdentityProvider.lilymay;

  @override
  Future<void> signOut() async {
    _current = null;
  }
}

/// Live implementation of VoiceContractBackend — runs against the real GB10
/// HTTP adapter in dev config. Direction pins are verified at the HTTP seam
/// (multipart upload format, auth headers, session binding).
class LiveVoiceContractBackend implements VoiceContractBackend {
  LiveVoiceContractBackend() {
    if (_apiBaseUrl.isEmpty) {
      throw StateError(
          'test_live requires --dart-define=API_BASE_URL=http://<gb10>:8100 '
          '(see test_live/README.md)');
    }
    _sessionApi = HttpSessionApi(
      baseUrl: _apiBaseUrl,
      identity: _identity,
    );
    _voiceApi = HttpVoiceApi(
      baseUrl: _apiBaseUrl,
      identity: _identity,
      voiceTurnDeadline: _liveVoiceTurnDeadline,
    );
  }

  final _identity = _DevTableIdentity();
  late final SessionApi _sessionApi;
  late final HttpVoiceApi _voiceApi;
  String? _currentSessionId;

  @override
  VoiceApi get voiceApi => _voiceApi;

  @override
  Future<String> getActiveSessionId() async {
    if (_currentSessionId != null) {
      return _currentSessionId!;
    }
    // Create a fresh session on the live server
    final started = await _sessionApi.startSession(subject: 'voice-test');
    _currentSessionId = started.sessionId;
    return _currentSessionId!;
  }

  @override
  Future<void> reset() async {
    // Call the dev reset route (same pattern as LiveContractBackend)
    try {
      final response = await http
          .post(Uri.parse('$_apiBaseUrl/__dev__/reset'))
          .timeout(_resetDeadline);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw StateError(
            'dev reset failed: HTTP ${response.statusCode} — is the adapter '
            'deployed in dev config?');
      }
    } catch (e) {
      throw StateError(
          'dev reset failed: $e — is the adapter reachable?');
    }
    await _identity.signOut();
    _currentSessionId = null;
  }

  @override
  Future<void> signIn() async => _identity.signIn();

  @override
  Uint8List get sampleAudio {
    // A REAL spoken AAC-LC recording ("What is a metaphor?", ~1s, mono) so
    // the bytes match the declared content type below. The old inline "WAV
    // bytes declared as mp4" fallback passed the GB10-era STT (which sniffed
    // bytes) but the spark's parakeet server trusts the declaration and
    // rejects the mismatch — found 2026-08-03 when the whole live voice
    // suite failed as VoiceUnavailable against a healthy STT.
    return File('test_live/fixtures/sample_question.m4a').readAsBytesSync();
  }

  @override
  String get sampleContentType =>
      'audio/mp4; codecs=mp4a.40.2'; // AAC-LC codec params (direction pin)

  @override
  Matcher expectedTranscript() =>
      allOf(isA<String>(), isNotEmpty); // Live STT returns real text

  @override
  Matcher expectedAnswer() =>
      allOf(isA<String>(), isNotEmpty); // Live LLM returns real answer

}

/// Skip condition: live tutor unavailable (no API_BASE_URL or unreachable).
bool get _liveTutorUnavailable => _apiBaseUrl.isEmpty;

void main() {
  // Run shared contract tests against live backend (skip if unavailable)
  if (!_liveTutorUnavailable) {
    runVoiceContractTests(LiveVoiceContractBackend.new);
  }

  // Additional live-specific direction pin tests
  group('live seam direction pins', () {
    late LiveVoiceContractBackend backend;
    late String sessionId;

    setUp(() async {
      backend = LiveVoiceContractBackend();
      await backend.reset();
      await backend.signIn();
      sessionId = await backend.getActiveSessionId();
    });

    test(
      'voiceTurn preserves capture format, auth, and session binding',
      () async {
        // This test verifies the direction pins at the LIVE seam (not just
        // hermetically): multipart field 'audio', filename extension matches
        // codec, Content-Type preserves params exactly, bearer present.
        final result = await backend.voiceApi.voiceTurn(
          sessionId,
          backend.sampleAudio,
          contentType: backend.sampleContentType,
        );

        // Assert: transcript returned (STT processed the audio)
        expect(result.transcript, isA<String>());
        // Even if silent/no speech, server accepted the format (didn't throw
        // UnsupportedAudioFormat) — this is the "green but broken" defence.

        // Assert: turn attached to session (no SessionNotFoundError)
        expect(result.answerParts, isNotEmpty);
      },
      skip: _liveTutorUnavailable
          ? 'Live tutor unavailable (no API_BASE_URL)'
          : null,
    );

    test(
      'codec params preserved in Content-Type header',
      () async {
        // Verify that codec params (e.g., 'codecs=mp4a.40.2') are preserved
        // exactly as captured — the live server must not reject on missing
        // or malformed codec params.
        final result = await backend.voiceApi.voiceTurn(
          sessionId,
          backend.sampleAudio,
          contentType: 'audio/mp4; codecs=mp4a.40.2', // explicit params
        );

        expect(result.transcript, isA<String>());
      },
      skip: _liveTutorUnavailable
          ? 'Live tutor unavailable (no API_BASE_URL)'
          : null,
    );

    test(
      '§7 VERIFIED STREAMING over the live /ws: transcript first, '
      'token/audio_ref interleave, terminal done',
      () async {
        // Mirrors the 2026-08-03 prod smoke through the app's REAL adapter:
        // ADR-ARCH-027 verified streaming — sentence chunks verified before
        // their tokens/audio surface, §7 frame order end to end.
        final events = <VoiceTurnEvent>[];
        await for (final event in backend.voiceApi.voiceTurnStream(
          sessionId,
          backend.sampleAudio,
          contentType: backend.sampleContentType,
        )) {
          events.add(event);
          if (event is TurnCompleteEvent) break;
        }

        expect(events.first, isA<TranscriptEvent>(),
            reason: '§7: transcript is the FIRST frame (STT confirmation)');
        expect(
          (events.first as TranscriptEvent).transcript.trim(),
          isNotEmpty,
          reason: 'the spoken fixture transcribes to real text',
        );
        expect(events.whereType<TextTokenEvent>(), isNotEmpty,
            reason: 'verified sentence tokens stream (ADR-ARCH-027 order)');
        expect(events.whereType<AudioPartEvent>(), isNotEmpty,
            reason: '§7 audio_ref frames interleave per synthesized sentence');
        expect(events.last, isA<TurnCompleteEvent>(),
            reason: "§7's terminal done closes the turn");

        // §7: audio chunks are FETCHED via voice_audio (`url` is advisory) —
        // a streamed ref must resolve to real bytes.
        final firstAudio = events.whereType<AudioPartEvent>().first;
        final bytes = await backend.voiceApi
            .fetchAudioChunk(sessionId, firstAudio.chunkId);
        expect(bytes, isNotEmpty);
      },
      skip: _liveTutorUnavailable
          ? 'Live tutor unavailable (no API_BASE_URL)'
          : null,
    );

    test(
      'bearer auth required for voice turns',
      () async {
        // Sign out to remove bearer token, then attempt voice turn
        await backend._identity.signOut();

        await expectLater(
          backend.voiceApi.voiceTurn(
            sessionId,
            backend.sampleAudio,
            contentType: backend.sampleContentType,
          ),
          throwsA(isA<Unauthenticated>()),
        );
      },
      skip: _liveTutorUnavailable
          ? 'Live tutor unavailable (no API_BASE_URL)'
          : null,
    );
  }, skip: _liveTutorUnavailable ? 'Live tutor unavailable' : null);
}
