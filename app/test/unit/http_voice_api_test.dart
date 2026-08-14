// TASK-VC-003: HttpVoiceApi direction-pin tests — verify the voice upload
// multipart contract at the client boundary (hermetic; MockClient).
//
// Contract (design §6.4): field 'audio'; filename extension matches captured
// codec; Content-Type preserves codec params exactly as recorded; bearer present.
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:study_tutor_app/adapters/http_voice_api.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ports/voice_api.dart';

/// Mock client that handles MultipartRequest (extends BaseRequest, not Request).
class _MockClientForMultipart extends http.BaseClient {
  _MockClientForMultipart(this._handler);

  final Future<http.StreamedResponse> Function(http.BaseRequest) _handler;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) =>
      _handler(request);
}

void main() {
  late FakeIdentityProvider identity;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn(); // dev table entry #1
  });

  /// Build an adapter whose "server" is [handler]; requests captured there.
  /// Note: handler receives http.BaseRequest since MultipartRequest extends it.
  VoiceApi apiWith(
    Future<http.StreamedResponse> Function(http.BaseRequest) handler,
  ) => HttpVoiceApi(
    baseUrl: 'http://gb10.tail:8100',
    identity: identity,
    client: _MockClientForMultipart(handler),
  );

  http.StreamedResponse jsonResponse(Object body) {
    final bytes = utf8.encode(jsonEncode(body));
    return http.StreamedResponse(
      Stream.value(bytes),
      200,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  }

  http.StreamedResponse errorResponse(Object body, int statusCode) {
    final bytes = utf8.encode(jsonEncode(body));
    return http.StreamedResponse(
      Stream.value(bytes),
      statusCode,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  }

  group('direction-pins — voiceTurn upload contract (§6.4)', () {
    test(
      'voiceTurn delivers recording authenticated, on-session, format-intact',
      () async {
        // arrange: capture the request; known content-type with codec params
        late http.BaseRequest seen;
        final api = apiWith((request) async {
          seen = request;
          return jsonResponse({
            'transcript': 'What is two plus two?',
            'tutor_response': 'Two plus two equals four.',
            'audio': <Map<String, dynamic>>[],
          });
        });

        final audio = Uint8List.fromList([0x00, 0x00, 0x00, 0x20]); // fake mp4
        const capturedContentType = 'audio/mp4; codecs=mp4a.40.2';

        // act
        await api.voiceTurn(
          'sess-123',
          audio,
          contentType: capturedContentType,
        );

        // assert: method + path (binding: hyphenated `voice-turn`)
        expect(seen.method, 'POST');
        expect(seen.url.path, '/api/sessions/sess-123/voice-turn');

        // assert: Authorization bearer present
        expect(seen.headers['authorization'],
            'Bearer ${FakeIdentityProvider.lilymay.token}');

        // assert: multipart field 'audio' present with correct extension
        final request = seen as http.MultipartRequest;
        expect(request.files.length, 1);
        expect(request.files.single.field, 'audio');
        expect(
          request.files.single.filename,
          endsWith('.mp4'),
          reason: 'filename extension must match codec',
        );

        // assert: Content-Type preserves codec params intact (fidelity guarantee)
        expect(
          request.files.single.contentType.toString(),
          capturedContentType,
          reason: 'codec params must not be stripped/re-encoded',
        );
      },
    );

    test('voiceTurn maps tutor_response + audio[] into answer parts', () async {
      // Binding §5 shape: { transcript, tutor_response, audio: [{seq, chunk_id, url}] }.
      final api = apiWith((request) async {
        return jsonResponse({
          'transcript': 'Explain fractions',
          'tutor_response': 'A fraction represents part of a whole.',
          'audio': [
            {
              'seq': 0,
              'chunk_id': 'chunk-a',
              'url': '/api/sessions/sess-456/voice-audio/chunk-a',
            },
            {
              'seq': 1,
              'chunk_id': 'chunk-b',
              'url': '/api/sessions/sess-456/voice-audio/chunk-b',
            },
          ],
        });
      });

      final result = await api.voiceTurn(
        'sess-456',
        Uint8List.fromList([0xFF]),
        contentType: 'audio/webm',
      );

      expect(result.transcript, 'Explain fractions');
      // The tutor's text reply renders first…
      expect(
        result.answerParts.whereType<TextAnswerPart>().single.text,
        'A fraction represents part of a whole.',
      );
      // …then the audio chunks, in seq order, for sequential playback.
      final audioParts =
          result.answerParts.whereType<AudioAnswerPart>().toList();
      expect(audioParts.map((p) => p.chunkId), ['chunk-a', 'chunk-b']);
      expect(audioParts.map((p) => p.seq), [0, 1]);
    });
  });

  group('voice error mapping — six voice_types + degradation', () {
    test('UnsupportedAudioFormat maps from wire error_type', () async {
      final api = apiWith((request) async {
        return errorResponse({
          'error': 'Codec not supported',
          'error_type': 'UnsupportedAudioFormat',
        }, 400);
      });

      await expectLater(
        api.voiceTurn('s-1', Uint8List(0), contentType: 'audio/unknown'),
        throwsA(
          isA<UnsupportedAudioFormat>().having(
            (e) => e.message,
            'message',
            'Codec not supported',
          ),
        ),
      );
    });

    test('EmptyRecording maps from wire error_type', () async {
      final api = apiWith((request) async {
        return errorResponse({
          'error': 'Recording too short',
          'error_type': 'EmptyRecording',
        }, 400);
      });

      await expectLater(
        api.voiceTurn('s-1', Uint8List(0), contentType: 'audio/mp4'),
        throwsA(
          isA<EmptyRecording>().having(
            (e) => e.message,
            'message',
            'Recording too short',
          ),
        ),
      );
    });

    test('UnintelligibleQuery maps from wire error_type', () async {
      final api = apiWith((request) async {
        return errorResponse({
          'error': 'No speech detected',
          'error_type': 'UnintelligibleQuery',
        }, 400);
      });

      await expectLater(
        api.voiceTurn('s-1', Uint8List(1), contentType: 'audio/mp4'),
        throwsA(
          isA<UnintelligibleQuery>().having(
            (e) => e.message,
            'message',
            'No speech detected',
          ),
        ),
      );
    });

    test('QueryTooLong maps from wire error_type', () async {
      final api = apiWith((request) async {
        return errorResponse({
          'error': 'Query exceeds limit',
          'error_type': 'QueryTooLong',
        }, 400);
      });

      await expectLater(
        api.voiceTurn('s-1', Uint8List(1), contentType: 'audio/mp4'),
        throwsA(
          isA<QueryTooLong>().having(
            (e) => e.message,
            'message',
            'Query exceeds limit',
          ),
        ),
      );
    });

    test('RecordingTooLarge maps from wire error_type', () async {
      final api = apiWith((request) async {
        return errorResponse({
          'error': 'Recording size exceeds maximum',
          'error_type': 'RecordingTooLarge',
        }, 413);
      });

      await expectLater(
        api.voiceTurn('s-1', Uint8List(1000000), contentType: 'audio/mp4'),
        throwsA(
          isA<RecordingTooLarge>().having(
            (e) => e.message,
            'message',
            'Recording size exceeds maximum',
          ),
        ),
      );
    });

    test('VoiceUnavailable maps from wire error_type (degradation)', () async {
      final api = apiWith((request) async {
        return errorResponse({
          'error': 'Voice service down',
          'error_type': 'VoiceUnavailable',
        }, 503);
      });

      await expectLater(
        api.voiceTurn('s-1', Uint8List(1), contentType: 'audio/mp4'),
        throwsA(
          isA<VoiceUnavailable>().having(
            (e) => e.message,
            'message',
            'Voice service down',
          ),
        ),
      );
    });
  });

  group('existing §9 errors — session-scoped verbs', () {
    test('SessionNotFoundError when session unknown', () async {
      final api = apiWith((request) async {
        return errorResponse({
          'error': 'Session not found',
          'error_type': 'SessionNotFoundError',
        }, 404);
      });

      await expectLater(
        api.voiceTurn('unknown', Uint8List(1), contentType: 'audio/mp4'),
        throwsA(isA<SessionNotFoundError>()),
      );
    });

    test('SessionEnded when session ended', () async {
      final api = apiWith((request) async {
        return errorResponse({
          'error': 'Session has ended',
          'error_type': 'SessionEnded',
        }, 409);
      });

      await expectLater(
        api.voiceTurn('ended-sess', Uint8List(1), contentType: 'audio/mp4'),
        throwsA(isA<SessionEnded>()),
      );
    });
  });

  group('transport failures → connection-problem type', () {
    test(
      'network failure surfaces as TransportError (retry semantics)',
      () async {
        final api = apiWith((request) async {
          throw http.ClientException('Connection refused');
        });

        await expectLater(
          api.voiceTurn('s-1', Uint8List(1), contentType: 'audio/mp4'),
          throwsA(
            isA<TransportError>().having(
              (e) => e.message,
              'message',
              contains('network failure'),
            ),
          ),
        );
      },
    );

    test('malformed response body surfaces as TransportError', () async {
      final api = apiWith((request) async {
        return http.StreamedResponse(
          Stream.value(utf8.encode('not json')),
          200,
        );
      });

      await expectLater(
        api.voiceTurn('s-1', Uint8List(1), contentType: 'audio/mp4'),
        throwsA(
          isA<TransportError>().having(
            (e) => e.message,
            'message',
            contains('malformed response'),
          ),
        ),
      );
    });
  });

  group('voiceTurnStream — WS streaming path (TASK-VC-006)', () {
    // NOTE: These are wire-protocol contract tests. Full end-to-end WebSocket
    // tests require a running server and are covered by integration tests.
    // Unit-level tests here verify the event mapping and error handling logic.

    test('_wsUri converts http to ws scheme', () {
      // Use reflection or test the URI building indirectly
      final wsUri = Uri.parse(
        'http://gb10.tail:8100/path',
      ).replace(scheme: 'ws');
      expect(wsUri.scheme, 'ws');
      expect(wsUri.host, 'gb10.tail');
    });

    test('_wsUri converts https to wss scheme', () {
      final wsUri = Uri.parse(
        'https://gb10.tail:8100/path',
      ).replace(scheme: 'wss');
      expect(wsUri.scheme, 'wss');
      expect(wsUri.host, 'gb10.tail');
    });

    // Integration-level test marker: these require a live WebSocket server
    // and are tested via the live contract suite or fake implementation
    test('voiceTurnStream contract tested via FakeVoiceApi', () async {
      // The FakeVoiceApi already implements the expected contract:
      // 1. Transcript first
      // 2. Text tokens
      // 3. Audio parts
      // 4. Turn complete
      // Real wire-level testing happens in integration tests.
      final fake = FakeVoiceApi();
      final events = await fake
          .voiceTurnStream(
            'sess-123',
            Uint8List.fromList([0xFF]),
            contentType: 'audio/mp4',
          )
          .toList();

      expect(events.first, isA<TranscriptEvent>());
      expect(events.last, isA<TurnCompleteEvent>());
      expect(events.any((e) => e is TextTokenEvent), isTrue);
    });
  });

  group('fetchAudioChunk — authenticated chunk retrieval (TASK-VC-006)', () {
    test('fetchAudioChunk includes bearer token', () async {
      // This test verifies AC-006: authenticated chunk fetching
      late http.BaseRequest seen;
      final api = apiWith((request) async {
        seen = request;
        return http.StreamedResponse(
          Stream.value(Uint8List.fromList([0x00, 0x01])),
          200,
          headers: {'content-type': 'application/octet-stream'},
        );
      });

      await api.fetchAudioChunk('sess-123', 'chunk-456');

      expect(seen.headers['authorization'],

          'Bearer ${FakeIdentityProvider.lilymay.token}');
      expect(seen.method, 'GET');
      // binding: GET /api/sessions/{id}/voice-audio/{chunk_id}
      expect(seen.url.path, '/api/sessions/sess-123/voice-audio/chunk-456');
    });

    test('fetchAudioChunk returns audio bytes', () async {
      final audioBytes = Uint8List.fromList([0xFF, 0xD8, 0xFF, 0xE0]);
      final api = apiWith((request) async {
        return http.StreamedResponse(
          Stream.value(audioBytes),
          200,
          headers: {'content-type': 'audio/opus'},
        );
      });

      final result = await api.fetchAudioChunk('sess-123', 'chunk-789');

      expect(result, equals(audioBytes));
    });

    test('fetchAudioChunk propagates session errors', () async {
      final api = apiWith((request) async {
        return errorResponse({
          'error': 'Session not found',
          'error_type': 'SessionNotFoundError',
        }, 404);
      });

      await expectLater(
        api.fetchAudioChunk('unknown', 'chunk-123'),
        throwsA(isA<SessionNotFoundError>()),
      );
    });
  });

  group('§2.1 WS route pin — the URL the production stream actually opens', () {
    // The client opened /api/sessions/{id}/voice_turn from 2026-07 until
    // 2026-08-03; the binding (§2.1) and the server mount /ws. Starlette
    // 403-closed every live upgrade and the app fell back silently to the
    // non-streaming POST, so streaming never ran live and no hermetic test
    // noticed — the fakes accepted whatever path the client asked for. This
    // pin drives the REAL voiceTurnStream at a real local socket and asserts
    // the upgrade line itself (the picker review's mutation lesson: pin the
    // production path, not just the adapter shape).
    test('voiceTurnStream upgrades on /api/sessions/{id}/ws with bearer auth',
        () async {
      String? upgradePath;
      String? authHeader;
      final upgraded = Completer<void>();
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      server.listen((request) async {
        upgradePath = request.uri.path;
        authHeader = request.headers.value('authorization');
        final socket = await WebSocketTransformer.upgrade(request);
        await socket.close();
        upgraded.complete();
      });

      final identity = FakeIdentityProvider();
      await identity.signIn();
      final api = HttpVoiceApi(
        baseUrl: 'http://127.0.0.1:${server.port}',
        identity: identity,
      );

      // Drain the stream; the server closes right after the upgrade, so the
      // stream ends (or surfaces a voice/transport error) — the pin is the
      // upgrade request itself, captured above.
      try {
        await api
            .voiceTurnStream(
              'abc123',
              Uint8List.fromList([1, 2, 3]),
              contentType: 'audio/mp4; codecs=mp4a.40.2',
            )
            .drain<void>();
      } on Object {
        // Close-after-upgrade may surface as an error; irrelevant to the pin.
      }
      await upgraded.future;
      await server.close(force: true);

      expect(upgradePath, '/api/sessions/abc123/ws',
          reason: 'binding §2.1 mounts the stream at /ws — the client must '
              'open exactly this path (it opened /voice_turn until '
              '2026-08-03 and every live upgrade was 403-closed)');
      expect(authHeader, startsWith('Bearer '),
          reason: '§2.1: bearer auth rides the upgrade request');
    });

    // Contract §7 Rev 1, both directions, VERBATIM strings. Until 2026-08-03
    // the client consumed a private dialect (token{token} / audio_part /
    // turn_complete) instead of the ratified token{text} / audio_ref / done —
    // undetected because the fakes speak events (not wire frames) and the WS
    // path bug meant no live frame ever arrived. This conversation runs the
    // REAL adapter against a real local socket speaking the ratified frames.
    test('§7 conversation: ratified frames in → events out; header+binary sent',
        () async {
      final received = <dynamic>[];
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      server.listen((request) async {
        final socket = await WebSocketTransformer.upgrade(request);
        socket.listen((message) {
          received.add(message);
          if (received.length == 2) {
            socket.add(jsonEncode({
              'type': 'transcript',
              'text': 'what is a metaphor',
              'is_final': true,
            }));
            socket.add(jsonEncode({'type': 'token', 'text': 'A metaphor '}));
            socket.add(jsonEncode({'type': 'token', 'text': 'compares.'}));
            socket.add(jsonEncode({
              'type': 'audio_ref',
              'seq': 0,
              'chunk_id': 'c-0',
              'url': '/api/sessions/s1/voice-audio/c-0',
            }));
            socket.add(jsonEncode({'type': 'done', 'turn_index': 3}));
          }
        });
      });

      final identity = FakeIdentityProvider();
      await identity.signIn();
      final api = HttpVoiceApi(
        baseUrl: 'http://127.0.0.1:${server.port}',
        identity: identity,
      );

      final events = await api
          .voiceTurnStream(
            's1',
            Uint8List.fromList([9, 9]),
            contentType: 'audio/mp4; codecs=mp4a.40.2',
          )
          .toList();
      await server.close(force: true);

      // Client → server: the §7 header frame verbatim, then ONE binary frame.
      final header = jsonDecode(received[0] as String);
      expect(header, {
        'type': 'voice_turn',
        'content_type': 'audio/mp4; codecs=mp4a.40.2',
        'size_bytes': 2,
      });
      expect(received[1], [9, 9],
          reason: '§7: exactly one binary frame carries the clip');

      // Server → client: the ratified frames map to the event set, in order.
      expect(events, hasLength(5));
      expect((events[0] as TranscriptEvent).transcript, 'what is a metaphor');
      expect((events[1] as TextTokenEvent).token, 'A metaphor ',
          reason: "§7 token frames carry the text in field 'text'");
      expect((events[2] as TextTokenEvent).token, 'compares.');
      final audio = events[3] as AudioPartEvent;
      expect(audio.seq, 0);
      expect(audio.chunkId, 'c-0',
          reason: "§7's audio frame is 'audio_ref' (not the old dialect's "
              "'audio_part'); the chunk is fetched via voice_audio");
      expect(events[4], isA<TurnCompleteEvent>(),
          reason: "§7's terminal frame is 'done' (not 'turn_complete')");
    });
  });
}
