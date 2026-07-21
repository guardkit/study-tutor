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

import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart' as record;

import '../domain/errors.dart';

/// Raised by [VoiceRecorder.start] when the microphone permission is not
/// granted. Client-side only (never arrives over the wire), so it is not part
/// of the §9 [SessionApiException] hierarchy.
class MicrophonePermissionDenied implements Exception {
  const MicrophonePermissionDenied();

  @override
  String toString() => 'MicrophonePermissionDenied';
}

/// Delivered when the 60-second hard-stop fires: [audio] carries the captured
/// bytes (null/empty when the capture produced nothing), or [error] is set when
/// reading/capping the recording failed (e.g. [RecordingTooLarge]). Lets the UI
/// send the auto-stopped audio and re-sync its recording state instead of
/// silently dropping the recording.
typedef VoiceAutoStop = void Function(Uint8List? audio, Object? error);

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
  /// Whether microphone capture is permitted, requesting the runtime permission
  /// if it has not been decided yet. record ^5.x requires this before [start].
  Future<bool> hasPermission();

  Future<void> start(AudioEncoder encoder);

  /// Stop capture and return the temp file path (null if nothing was written).
  Future<String?> stop();

  Future<void> cancel();

  Future<void> dispose();
}

/// Default [RecordingBackend] wrapping `record.AudioRecorder`.
class _RecordPackageBackend implements RecordingBackend {
  final record.AudioRecorder _record = record.AudioRecorder();

  /// The file path the current recording is being written to. record ^5.x
  /// requires a concrete path (an empty string fails native recorder init).
  String? _currentPath;

  @override
  Future<bool> hasPermission() => _record.hasPermission();

  @override
  Future<void> start(AudioEncoder encoder) async {
    final recordEncoder = encoder == AudioEncoder.aacLc
        ? record.AudioEncoder.aacLc
        : record.AudioEncoder.opus;
    final extension = encoder == AudioEncoder.aacLc ? 'm4a' : 'opus';
    final dir = await getTemporaryDirectory();
    _currentPath =
        '${dir.path}/voice_${DateTime.now().microsecondsSinceEpoch}.$extension';
    await _record.start(
      record.RecordConfig(encoder: recordEncoder),
      path: _currentPath!,
    );
  }

  @override
  Future<String?> stop() async => (await _record.stop()) ?? _currentPath;

  // Dedicated cancel() stops AND removes the temp file (no leak on cancel).
  @override
  Future<void> cancel() => _record.cancel();

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

  /// Start recording with the configured encoder. Throws [StateError] if already
  /// recording, or [MicrophonePermissionDenied] if the mic permission is not
  /// granted (the request prompt is shown as part of the check). Arms the
  /// 60-second hard-stop; when it fires, [onMaxDuration] receives the captured
  /// audio (or an error) so the caller can send it and re-sync its UI rather
  /// than losing the recording.
  Future<void> start({VoiceAutoStop? onMaxDuration}) async {
    if (_isRecording) {
      throw StateError('Already recording');
    }
    if (!await _backend.hasPermission()) {
      throw const MicrophonePermissionDenied();
    }
    await _backend.start(encoder);
    _isRecording = true;
    _autoStopTimer = Timer(maxDuration, () {
      // Fully guarded: never let the captured audio drop silently or an
      // over-cap/read throw escape as an uncaught async error.
      unawaited(_handleAutoStop(onMaxDuration));
    });
  }

  Future<void> _handleAutoStop(VoiceAutoStop? onMaxDuration) async {
    if (!_isRecording) return;
    try {
      final bytes = await stop();
      onMaxDuration?.call(bytes, null);
    } catch (error) {
      onMaxDuration?.call(null, error);
    }
  }

  /// Stop recording and return the REAL recorded bytes (§5.1). Returns null when
  /// no recording was in progress or the capture produced nothing usable (no
  /// file, an empty/absent path, an unreadable file, or zero bytes — all common
  /// on real hardware for an instant double-tap or a mic glitch). Throws
  /// [RecordingTooLarge] if the captured audio exceeds [maxSizeBytes].
  Future<Uint8List?> stop() async {
    if (!_isRecording) return null;
    // Claim the stop synchronously, BEFORE any await, so a second concurrent
    // stop() (e.g. a manual tap racing the 60 s auto-stop) no-ops instead of
    // reading and sending the same recording twice.
    _isRecording = false;

    _autoStopTimer?.cancel();
    _autoStopTimer = null;

    final path = await _backend.stop();

    if (path == null || path.isEmpty) return null;

    Uint8List bytes;
    try {
      bytes = await _readBytes(path);
    } on FileSystemException {
      // The capture never produced a usable file — treat as an empty recording
      // rather than crashing the mic tap.
      return null;
    }
    // Best-effort cleanup: the temp capture file is no longer needed once read
    // into memory (the bytes are what we upload). Swallow any delete error.
    unawaited(File(path).delete().then((_) {}, onError: (_) {}));
    if (bytes.isEmpty) return null;
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
