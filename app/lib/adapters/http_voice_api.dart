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
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

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

  /// Per-request deadline for voice turns (aligned to contract budget):
  /// voice processing (STT + LLM + TTS) has higher latency than text turns,
  /// budget is 30s (design §6.3). Constructor override exists for tests only.
  static const _defaultVoiceTurnBudget = Duration(seconds: 30);

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
      '/api/sessions/${Uri.encodeComponent(sessionId)}/voice_turn',
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

    // Map response to VoiceTurnResult
    try {
      final map = json as Map<String, dynamic>;
      final transcript = map['transcript'] as String;
      final answerPartsJson = map['answer_parts'] as List<dynamic>;

      final answerParts = answerPartsJson.map((part) {
        final partMap = part as Map<String, dynamic>;
        final seq = partMap['seq'] as int;

        if (partMap.containsKey('text')) {
          return TextAnswerPart(seq: seq, text: partMap['text'] as String);
        } else if (partMap.containsKey('chunk_id')) {
          return AudioAnswerPart(
            seq: seq,
            chunkId: partMap['chunk_id'] as String,
          );
        } else {
          throw const TransportError('answer part missing text or chunk_id');
        }
      }).toList();

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
  }) {
    // Streaming variant not implemented in TASK-VC-003 (MVP HTTP turn only)
    throw UnimplementedError('voiceTurnStream lands in TASK-VC-006');
  }

  @override
  Future<Uint8List> fetchAudioChunk(String sessionId, String chunkId) {
    // Audio chunk fetching not implemented in TASK-VC-003 (MVP HTTP turn only)
    throw UnimplementedError('fetchAudioChunk lands in TASK-VC-006');
  }
}
