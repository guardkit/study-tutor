/// VoiceRecorder — the real microphone-capture adapter (S-A2 voice fix §5.1).
///
/// Moved out of `lib/fakes/` (where `stop()` returned a 100-byte placeholder)
/// into the adapter layer where it belongs. `stop()` now returns the REAL
/// recorded file bytes and enforces the declared 10 MB cap (throws
/// [RecordingTooLarge] when exceeded). The record-package + file-read plumbing
/// sits behind the [RecordingBackend] seam so the byte-reading and cap logic
/// are testable without a physical microphone.
library;

import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:record/record.dart' as record;

import '../domain/errors.dart';

/// Audio encoder selection for [VoiceRecorder].
///
/// Maps to the record package's AudioEncoder enum. Kept as a simple enum to
/// avoid coupling call sites to the record package's internal types.
enum AudioEncoder {
  /// AAC-LC (m4a container) — default, best iOS/Android compatibility.
  aacLc,

  /// Opus codec — fallback for platforms where AAC isn't available.
  opus,
}

/// Seam over the microphone-capture plumbing so [VoiceRecorder]'s cap/byte
/// logic can be unit-tested with a fake backend (no real mic). `stop()`
/// returns the recorded file path, exactly as the record package does.
abstract interface class RecordingBackend {
  Future<void> start(AudioEncoder encoder);

  /// Stop capture and return the temp file path (null if nothing was written).
  Future<String?> stop();

  Future<void> cancel();

  Future<void> dispose();
}

/// Default [RecordingBackend] wrapping `record.AudioRecorder`.
class _RecordPackageBackend implements RecordingBackend {
  final record.AudioRecorder _record = record.AudioRecorder();

  @override
  Future<void> start(AudioEncoder encoder) {
    final recordEncoder = encoder == AudioEncoder.aacLc
        ? record.AudioEncoder.aacLc
        : record.AudioEncoder.opus;
    // Empty path lets the record package pick a temp file.
    return _record.start(record.RecordConfig(encoder: recordEncoder), path: '');
  }

  @override
  Future<String?> stop() => _record.stop();

  @override
  Future<void> cancel() => _record.stop().then((_) {});

  @override
  Future<void> dispose() async => _record.dispose();
}

/// Wrapper around the record package with voice-specific constraints.
///
/// Enforces:
/// - 60-second hard stop (client-side limit, design §6.1/§6.3)
/// - 10 MB byte cap — `stop()` throws [RecordingTooLarge] past it (§5.1)
/// - Injectable encoder selection (m4a/AAC default, opus fallback)
///
/// The recorder auto-stops at 60 seconds so a recording can never exceed the
/// duration limit even if the user forgets to tap stop.
class VoiceRecorder {
  VoiceRecorder({
    this.encoder = AudioEncoder.aacLc,
    Duration? maxDuration,
    int? maxSizeBytes,
    RecordingBackend? backend,
    Future<Uint8List> Function(String path)? readBytes,
  })  : maxDuration = maxDuration ?? const Duration(seconds: 60),
        maxSizeBytes = maxSizeBytes ?? (10 * 1024 * 1024),
        _backend = backend ?? _RecordPackageBackend(),
        _readBytes = readBytes ?? _readFileBytes;

  final AudioEncoder encoder;
  final Duration maxDuration;
  final int maxSizeBytes;
  final RecordingBackend _backend;
  final Future<Uint8List> Function(String path) _readBytes;

  bool _isRecording = false;
  Timer? _autoStopTimer;

  /// Whether a recording is currently in progress.
  bool get isRecording => _isRecording;

  static Future<Uint8List> _readFileBytes(String path) =>
      File(path).readAsBytes();

  /// Start recording with the configured encoder. Throws if already recording.
  /// Sets up the 60-second auto-stop.
  Future<void> start() async {
    if (_isRecording) {
      throw StateError('Already recording');
    }
    await _backend.start(encoder);
    _isRecording = true;
    _autoStopTimer = Timer(maxDuration, () {
      if (_isRecording) stop();
    });
  }

  /// Stop recording and return the REAL recorded bytes (§5.1). Returns null if
  /// no recording was in progress or the backend produced no file. Throws
  /// [RecordingTooLarge] if the captured audio exceeds [maxSizeBytes].
  Future<Uint8List?> stop() async {
    if (!_isRecording) return null;

    _autoStopTimer?.cancel();
    _autoStopTimer = null;

    final path = await _backend.stop();
    _isRecording = false;

    if (path == null) return null;

    final bytes = await _readBytes(path);
    if (bytes.length > maxSizeBytes) {
      throw const RecordingTooLarge();
    }
    return bytes;
  }

  /// Cancel the current recording without returning bytes. Safe to call when
  /// not recording.
  void cancel() {
    if (!_isRecording) return;
    _autoStopTimer?.cancel();
    _autoStopTimer = null;
    _isRecording = false;
    _backend.cancel();
  }

  /// Dispose of resources.
  void dispose() {
    cancel();
    _backend.dispose();
  }
}
