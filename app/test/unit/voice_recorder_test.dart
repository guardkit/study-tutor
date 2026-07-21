// S-A2 §5.1: the real VoiceRecorder (moved to lib/adapters) returns the REAL
// recorded file bytes from stop() — not the old 100-byte placeholder — and
// enforces the 10 MB cap. The record-package + file-read plumbing is behind
// the RecordingBackend seam, so these run hermetically with a fake backend
// pointing at a real temp file.
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/adapters/voice_recorder.dart';
import 'package:study_tutor_app/domain/errors.dart';

/// A [RecordingBackend] whose `stop()` returns a fixed, caller-supplied path —
/// the seam that lets us point the recorder at a real file we wrote ourselves.
class FakeRecordingBackend implements RecordingBackend {
  FakeRecordingBackend(this.path);
  final String? path;
  bool started = false;

  /// Mic-permission answer; default granted so the happy-path tests proceed.
  bool permission = true;

  @override
  Future<bool> hasPermission() async => permission;

  @override
  Future<void> start(AudioEncoder encoder) async => started = true;

  @override
  Future<String?> stop() async => path;

  @override
  Future<void> cancel() async {}

  @override
  Future<void> dispose() async {}
}

/// A backend whose `stop()` parks on a caller-controlled future — lets a test
/// hold the first stop() mid-await and race a second stop() against it.
class DelayedStopBackend implements RecordingBackend {
  DelayedStopBackend(this.gate);
  final Future<String?> gate;
  int stopCalls = 0;

  @override
  Future<bool> hasPermission() async => true;

  @override
  Future<void> start(AudioEncoder encoder) async {}

  @override
  Future<String?> stop() {
    stopCalls++;
    return gate;
  }

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

  test('start() throws MicrophonePermissionDenied when permission not granted',
      () async {
    final recorder =
        VoiceRecorder(backend: FakeRecordingBackend(null)..permission = false);
    await expectLater(
      recorder.start(),
      throwsA(isA<MicrophonePermissionDenied>()),
    );
    expect(recorder.isRecording, isFalse);
  });

  test('empty backend path → stop() returns null, no crash', () async {
    // record can yield '' for a capture that produced nothing (the empty-path
    // bug): stop() must treat it as an empty recording, not File('').readAsBytes.
    final recorder = VoiceRecorder(backend: FakeRecordingBackend(''));
    await recorder.start();
    expect(await recorder.stop(), isNull);
  });

  test('missing/unreadable file → stop() returns null, no crash', () async {
    final recorder = VoiceRecorder(
      backend: FakeRecordingBackend('${tempDir.path}/never_created.m4a'),
    );
    await recorder.start();
    expect(await recorder.stop(), isNull);
  });

  test('zero-byte recording → stop() returns null', () async {
    final file = File('${tempDir.path}/empty.m4a');
    await file.writeAsBytes(Uint8List(0));
    final recorder = VoiceRecorder(backend: FakeRecordingBackend(file.path));
    await recorder.start();
    expect(await recorder.stop(), isNull);
  });

  test('60 s auto-stop delivers the captured audio to onMaxDuration', () {
    fakeAsync((async) {
      final bytes = Uint8List.fromList(List<int>.filled(32, 5));
      Uint8List? delivered;
      Object? error;
      final recorder = VoiceRecorder(
        backend: FakeRecordingBackend('/fake/path.m4a'),
        readBytes: (_) async => bytes,
      );
      recorder.start(onMaxDuration: (audio, err) {
        delivered = audio;
        error = err;
      });
      async.flushMicrotasks();
      expect(recorder.isRecording, isTrue);

      async.elapse(const Duration(seconds: 60));
      async.flushMicrotasks();

      expect(delivered, equals(bytes),
          reason: 'auto-stopped audio is sent, not silently dropped');
      expect(error, isNull);
      expect(recorder.isRecording, isFalse);
    });
  });

  test('a second stop() racing the first no-ops (no double read/send)', () async {
    // The auto-stop and a manual tap can both call stop(); the second must not
    // re-read and re-send the same recording.
    final gate = Completer<String?>();
    final backend = DelayedStopBackend(gate.future);
    var reads = 0;
    final recorder = VoiceRecorder(
      backend: backend,
      readBytes: (_) async {
        reads++;
        return Uint8List.fromList([1, 2, 3]);
      },
    );
    await recorder.start();

    final first = recorder.stop(); // parks on the gate
    final second = await recorder.stop(); // must no-op immediately

    expect(second, isNull, reason: 'the racing stop() returns null, no re-send');
    expect(backend.stopCalls, 1, reason: 'backend.stop() issued once');

    gate.complete('/tmp/take.m4a');
    final firstResult = await first;
    expect(firstResult, isNotNull);
    expect(reads, 1, reason: 'the recording is read exactly once');
  });

  test('60 s auto-stop over cap → error delivered, never an uncaught throw', () {
    fakeAsync((async) {
      final big = Uint8List.fromList(List<int>.filled(128, 1));
      Object? error;
      final recorder = VoiceRecorder(
        maxSizeBytes: 64,
        backend: FakeRecordingBackend('/fake/path.m4a'),
        readBytes: (_) async => big,
      );
      recorder.start(onMaxDuration: (audio, err) => error = err);
      async.flushMicrotasks();

      async.elapse(const Duration(seconds: 60));
      async.flushMicrotasks();

      expect(error, isA<RecordingTooLarge>());
      expect(recorder.isRecording, isFalse);
    });
  });
}
