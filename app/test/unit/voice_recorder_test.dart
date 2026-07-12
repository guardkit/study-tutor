// S-A2 §5.1: the real VoiceRecorder (moved to lib/adapters) returns the REAL
// recorded file bytes from stop() — not the old 100-byte placeholder — and
// enforces the 10 MB cap. The record-package + file-read plumbing is behind
// the RecordingBackend seam, so these run hermetically with a fake backend
// pointing at a real temp file.
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/adapters/voice_recorder.dart';
import 'package:study_tutor_app/domain/errors.dart';

/// A [RecordingBackend] whose `stop()` returns a fixed, caller-supplied path —
/// the seam that lets us point the recorder at a real file we wrote ourselves.
class FakeRecordingBackend implements RecordingBackend {
  FakeRecordingBackend(this.path);
  final String? path;
  bool started = false;

  @override
  Future<void> start(AudioEncoder encoder) async => started = true;

  @override
  Future<String?> stop() async => path;

  @override
  Future<void> cancel() async {}

  @override
  Future<void> dispose() async {}
}

void main() {
  late Directory tempDir;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('voice_recorder_test');
  });

  tearDown(() async {
    if (await tempDir.exists()) await tempDir.delete(recursive: true);
  });

  test('stop() returns the REAL recorded bytes, not a placeholder', () async {
    // Write a real file with known, non-placeholder contents.
    final bytes = Uint8List.fromList(List<int>.generate(2048, (i) => i % 256));
    final file = File('${tempDir.path}/recording.m4a');
    await file.writeAsBytes(bytes);

    final recorder = VoiceRecorder(backend: FakeRecordingBackend(file.path));
    await recorder.start();
    final result = await recorder.stop();

    expect(result, isNotNull);
    expect(result!.length, bytes.length,
        reason: 'the actual file length, not the old 100-byte placeholder');
    expect(result, equals(bytes),
        reason: 'byte-for-byte the recorded file contents');
  });

  test('stop() enforces the size cap → RecordingTooLarge', () async {
    final bytes = Uint8List.fromList(List<int>.filled(128, 1));
    final file = File('${tempDir.path}/too_big.m4a');
    await file.writeAsBytes(bytes);

    final recorder = VoiceRecorder(
      maxSizeBytes: 64, // captured file (128 B) exceeds the cap
      backend: FakeRecordingBackend(file.path),
    );
    await recorder.start();

    expect(recorder.stop, throwsA(isA<RecordingTooLarge>()));
  });

  test('a file at exactly the cap is allowed', () async {
    final bytes = Uint8List.fromList(List<int>.filled(64, 9));
    final file = File('${tempDir.path}/at_cap.m4a');
    await file.writeAsBytes(bytes);

    final recorder = VoiceRecorder(
      maxSizeBytes: 64,
      backend: FakeRecordingBackend(file.path),
    );
    await recorder.start();
    final result = await recorder.stop();

    expect(result, isNotNull);
    expect(result!.length, 64);
  });

  test('stop() before start() returns null', () async {
    final recorder = VoiceRecorder(backend: FakeRecordingBackend(null));
    expect(await recorder.stop(), isNull);
  });

  test('backend that produced no file → stop() returns null', () async {
    final recorder = VoiceRecorder(backend: FakeRecordingBackend(null));
    await recorder.start();
    expect(await recorder.stop(), isNull);
  });

  test('default constants unchanged (60 s / 10 MB / aacLc)', () {
    final recorder = VoiceRecorder(backend: FakeRecordingBackend(null));
    expect(recorder.maxDuration, const Duration(seconds: 60));
    expect(recorder.maxSizeBytes, 10 * 1024 * 1024);
    expect(recorder.encoder, AudioEncoder.aacLc);
  });
}
