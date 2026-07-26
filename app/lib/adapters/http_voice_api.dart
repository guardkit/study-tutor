/// HttpVoiceApi — real transport adapter behind the `VoiceApi` port.
///
/// TASK-VC-003: Implements MVP HTTP `voiceTurn` path, reusing HttpSessionApi
/// seams (base-URL normalization, `_headers()` bearer injection, §9 envelope
/// → sealed-exception mapping) extended with the six voice `error_type`s.
/// Carries the "green but broken" fidelity defence (design §6.4) — the LPA
/// MockClient direction-pins ported to the Dart seam.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io' as io;
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:web_socket_channel/io.dart';

import '../domain/errors.dart';
import '../ports/identity_provider.dart';
import '../ports/voice_api.dart';

class HttpVoiceApi implements VoiceApi {
  HttpVoiceApi({
    required String baseUrl,
    required this._identity,
    http.Client? client,
    Duration? voiceTurnDeadline,
  }) : _base = baseUrl.endsWith('/')
           ? baseUrl.substring(0, baseUrl.length - 1)
           : baseUrl,
       _client = client ?? http.Client(),
       _voiceTurnDeadline = voiceTurnDeadline ?? _defaultVoiceTurnBudget;

  /// Per-request deadline for voice turns. 90s, matching
  /// HttpSessionApi.turnBudget: the voice turn CONTAINS a full tutor
  /// completion (STT + LLM + TTS), so it can never budget less than a text
  /// turn — the design §6.3 30s figure assumed an unloaded GB10, and a
  /// factory-loaded box was measured at ~40s server-side on 2026-07-25
  /// (server returned 200 after the app had given up). Constructor override
  /// exists for tests only.
  static const _defaultVoiceTurnBudget = Duration(seconds: 90);

  final String _base;
  final IdentityProvider _identity;
  final http.Client _client;
  final Duration _voiceTurnDeadline;

  /// Release the underlying connection pool. The composed app holds one
  /// adapter for its whole lifetime and never needs this; tests might.
  void close() => _client.close();

  Uri _uri(String path) => Uri.parse('$_base$path');

  /// Reused from HttpSessionApi seam (§3): bearer token from credential header
  /// ONLY. When signed out no header is sent — server answers 401 → Unauthenticated.
  Map<String, String> _headers() {
    final token = _identity.currentPrincipal?.token;
    return {if (token != null) 'authorization': 'Bearer $token'};
  }

  @override
  Future<VoiceTurnResult> voiceTurn(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  }) async {
    // Build multipart request: field 'audio' with filename extension matching
    // the captured codec (fidelity guarantee per design §6.4).
    final uri = _uri(
      '/api/sessions/${Uri.encodeComponent(sessionId)}/voice-turn',
    );
    final request = http.MultipartRequest('POST', uri);
    request.headers.addAll(_headers());

    // Extract file extension from content-type (e.g., 'audio/mp4' → '.mp4')
    final extension = _extensionFromContentType(contentType);

    // Preserve codec params intact: parse the content-type to preserve params
    // like 'codecs=mp4a.40.2' (fidelity guarantee).
    final parsedContentType = MediaType.parse(contentType);

    request.files.add(
      http.MultipartFile.fromBytes(
        'audio',
        audio,
        filename: 'recording$extension',
        contentType: parsedContentType,
      ),
    );

    // Execute request with deadline → envelope → shape mapping
    http.Response response;
    try {
      final streamedResponse = await _client
          .send(request)
          .timeout(_voiceTurnDeadline);
      response = await http.Response.fromStream(streamedResponse);
    } on TimeoutException {
      throw const TransportError('request deadline exceeded');
    } on http.ClientException catch (e) {
      throw TransportError('network failure: ${e.message}');
    }

    // Check for wire errors (§9 + voice errors)
    _throwWireError(response);

    // Decode response body
    dynamic json;
    try {
      json = jsonDecode(utf8.decode(response.bodyBytes));
    } on FormatException {
      throw const TransportError('malformed response body');
    }

    // Map response to VoiceTurnResult. Binding §5 (Rev 1): the voice_turn
    // response is { transcript, tutor_response, audio: [{seq, chunk_id, url}] }.
    // The tutor's text reply renders as the answer; the audio chunks are
    // fetched + played in seq order. `audio` may be empty (TTS degraded to
    // text-only, ASSUM-005).
    try {
      final map = json as Map<String, dynamic>;
      final transcript = map['transcript'] as String;
      final tutorResponse = map['tutor_response'] as String;
      final audioJson = (map['audio'] as List<dynamic>?) ?? const [];

      final answerParts = <AnswerPart>[
        TextAnswerPart(seq: 0, text: tutorResponse),
        ...audioJson.map((part) {
          final partMap = part as Map<String, dynamic>;
          return AudioAnswerPart(
            seq: partMap['seq'] as int,
            chunkId: partMap['chunk_id'] as String,
          );
        }),
      ];

      return VoiceTurnResult(transcript: transcript, answerParts: answerParts);
    } on TypeError {
      throw const TransportError('response body does not fit the §5 shape');
    } on ArgumentError {
      throw const TransportError('response body does not fit the §5 shape');
    }
  }

  /// Extract file extension from content-type (e.g., 'audio/mp4' → '.mp4').
  String _extensionFromContentType(String contentType) {
    final mimeType = contentType.split(';').first.trim();
    final subtype = mimeType.split('/').last;
    return '.$subtype';
  }

  /// Reused from HttpSessionApi seam (§4): non-2xx with §9 envelope → typed
  /// exception. Extended with six voice error_types (FEAT-VOICE-003 §6.2).
  void _throwWireError(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) return;

    Object? decoded;
    try {
      decoded = jsonDecode(utf8.decode(response.bodyBytes));
    } on FormatException {
      decoded = null;
    }

    final envelope = decoded is Map<String, dynamic> ? decoded : null;
    final error = envelope?['error'];
    final envelopeMessage = error is String ? error : null;
    final message = envelopeMessage ?? 'HTTP ${response.statusCode}';

    // Map wire error_type to sealed exception (§9 errors + voice errors)
    switch (envelope?['error_type']) {
      // Session §9 errors
      case 'SessionNotFoundError':
        throw SessionNotFoundError(message);
      case 'SessionEnded':
        throw SessionEnded(message);
      case 'SessionForbidden':
        throw SessionForbidden(message);
      case 'Unauthenticated':
        throw Unauthenticated(message);

      // Voice-specific errors (FEAT-VOICE-003 §6.2)
      case 'UnsupportedAudioFormat':
        throw UnsupportedAudioFormat(message);
      case 'EmptyRecording':
        throw EmptyRecording(message);
      case 'UnintelligibleQuery':
        throw UnintelligibleQuery(message);
      case 'QueryTooLong':
        throw QueryTooLong(message);
      case 'RecordingTooLarge':
        throw RecordingTooLarge(message);
      case 'VoiceUnavailable':
        throw VoiceUnavailable(message);
    }

    // No recognized error_type → TransportError (binding §4.2)
    throw TransportError(
      envelopeMessage == null
          ? 'HTTP ${response.statusCode}'
          : 'HTTP ${response.statusCode}: $envelopeMessage',
    );
  }

  @override
  Stream<VoiceTurnEvent> voiceTurnStream(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  }) async* {
    // Build WebSocket URI from base URL (http→ws, https→wss)
    final wsUri = _wsUri(
      '/api/sessions/${Uri.encodeComponent(sessionId)}/voice_turn',
    );

    IOWebSocketChannel? channel;
    try {
      // Connect to WebSocket with authorization header
      // Use io.WebSocket.connect to pass custom headers (bearer token)
      final token = _identity.currentPrincipal?.token;
      final headers = {if (token != null) 'authorization': 'Bearer $token'};

      final socket =
          await io.WebSocket.connect(
            wsUri.toString(),
            headers: headers,
          ).timeout(
            const Duration(seconds: 5),
            onTimeout: () =>
                throw const TransportError('WebSocket connection timeout'),
          );

      channel = IOWebSocketChannel(socket);

      // Send header frame: {type:"voice_turn", content_type, size_bytes}
      final headerFrame = jsonEncode({
        'type': 'voice_turn',
        'content_type': contentType,
        'size_bytes': audio.length,
      });
      channel.sink.add(headerFrame);

      // Send binary frame with audio data
      channel.sink.add(audio);

      // Process incoming frames
      await for (final message in channel.stream) {
        if (message is String) {
          // Parse JSON frame
          dynamic json;
          try {
            json = jsonDecode(message);
          } on FormatException {
            throw const TransportError('malformed WebSocket frame');
          }

          if (json is! Map<String, dynamic>) {
            throw const TransportError('WebSocket frame is not a JSON object');
          }

          final type = json['type'] as String?;

          // Handle error frames
          if (type == 'error') {
            final errorType = json['error_type'] as String?;
            final errorMessage = json['error'] as String? ?? 'Unknown error';
            _throwWireErrorFromType(errorType, errorMessage);
          }

          // Map frame type to event
          switch (type) {
            case 'transcript':
              final text = json['text'] as String? ?? '';
              final isFinal = json['is_final'] as bool? ?? true;
              yield TranscriptEvent(transcript: text, isFinal: isFinal);

            case 'token':
              final token = json['token'] as String? ?? '';
              yield TextTokenEvent(token: token);

            case 'audio_part':
              final seq = json['seq'] as int? ?? 0;
              final chunkId = json['chunk_id'] as String? ?? '';
              yield AudioPartEvent(seq: seq, chunkId: chunkId);

            case 'turn_complete':
              yield const TurnCompleteEvent();
              await channel.sink.close();
              return;

            default:
              // Unknown frame type - ignore per robustness principle
              continue;
          }
        }
      }
    } on io.SocketException catch (e) {
      throw TransportError('WebSocket connection failed: ${e.message}');
    } on TimeoutException {
      throw const TransportError('WebSocket operation timeout');
    } on io.WebSocketException catch (e) {
      throw TransportError('WebSocket error: ${e.message}');
    } finally {
      await channel?.sink.close();
    }
  }

  /// Build WebSocket URI from HTTP base URL (http→ws, https→wss)
  Uri _wsUri(String path) {
    final httpUri = Uri.parse('$_base$path');
    final scheme = httpUri.scheme == 'https' ? 'wss' : 'ws';
    return httpUri.replace(scheme: scheme);
  }

  /// Throw typed exception from wire error_type string (used by WebSocket path)
  Never _throwWireErrorFromType(String? errorType, String message) {
    switch (errorType) {
      // Session §9 errors
      case 'SessionNotFoundError':
        throw SessionNotFoundError(message);
      case 'SessionEnded':
        throw SessionEnded(message);
      case 'SessionForbidden':
        throw SessionForbidden(message);
      case 'Unauthenticated':
        throw Unauthenticated(message);

      // Voice-specific errors
      case 'UnsupportedAudioFormat':
        throw UnsupportedAudioFormat(message);
      case 'EmptyRecording':
        throw EmptyRecording(message);
      case 'UnintelligibleQuery':
        throw UnintelligibleQuery(message);
      case 'QueryTooLong':
        throw QueryTooLong(message);
      case 'RecordingTooLarge':
        throw RecordingTooLarge(message);
      case 'VoiceUnavailable':
        throw VoiceUnavailable(message);

      default:
        throw TransportError(message);
    }
  }

  @override
  Future<Uint8List> fetchAudioChunk(String sessionId, String chunkId) async {
    // Fetch pre-generated audio chunk via authenticated GET request
    final uri = _uri(
      '/api/sessions/${Uri.encodeComponent(sessionId)}/voice-audio/${Uri.encodeComponent(chunkId)}',
    );

    http.Response response;
    try {
      response = await _client
          .get(uri, headers: _headers())
          .timeout(const Duration(seconds: 10));
    } on TimeoutException {
      throw const TransportError('audio chunk fetch timeout');
    } on http.ClientException catch (e) {
      throw TransportError('network failure: ${e.message}');
    }

    // Check for wire errors (§9 + voice errors)
    _throwWireError(response);

    // Return raw audio bytes
    return response.bodyBytes;
  }
}
