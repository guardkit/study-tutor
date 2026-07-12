/// AudioPlayback — sequential TTS chunk playback (S-A2 voice fix §5.2).
///
/// `AudioAnswerPart` chunks are fetched via the existing `fetchAudioChunk`
/// adapter and handed here to be played back-to-back, in `seq` order, with a
/// stop control. The port is a tiny interface so the session screen can inject
/// a mock in widget tests (just_audio needs platform channels and cannot run
/// hermetically).
library;

import 'dart:io';
import 'dart:typed_data';

import 'package:just_audio/just_audio.dart';

/// Plays already-fetched audio chunks sequentially, with a stop control.
abstract interface class AudioPlayback {
  /// Play [chunks] back-to-back in order. Completes when the last chunk
  /// finishes or [stop] is called.
  Future<void> playSequential(List<Uint8List> chunks);

  /// Stop any in-progress playback immediately.
  Future<void> stop();

  /// Release underlying resources.
  Future<void> dispose();
}

/// Real [AudioPlayback] backed by `just_audio` (already a declared dependency).
/// Each chunk is written to a temp file and played to completion before the
/// next begins, so the answer is heard as one continuous utterance.
class JustAudioPlayback implements AudioPlayback {
  JustAudioPlayback({AudioPlayer? player}) : _player = player ?? AudioPlayer();

  final AudioPlayer _player;
  bool _stopped = false;

  @override
  Future<void> playSequential(List<Uint8List> chunks) async {
    _stopped = false;
    for (final bytes in chunks) {
      if (_stopped) break;
      final file = await _writeTemp(bytes);
      try {
        await _player.setFilePath(file.path);
        // `play()` completes when playback reaches the end (or is stopped).
        await _player.play();
      } finally {
        if (await file.exists()) {
          await file.delete();
        }
      }
    }
  }

  @override
  Future<void> stop() async {
    _stopped = true;
    await _player.stop();
  }

  @override
  Future<void> dispose() async {
    _stopped = true;
    await _player.dispose();
  }

  Future<File> _writeTemp(Uint8List bytes) async {
    final name =
        'tts_${DateTime.now().microsecondsSinceEpoch}_${bytes.length}.audio';
    final file = File('${Directory.systemTemp.path}/$name');
    await file.writeAsBytes(bytes, flush: true);
    return file;
  }
}
