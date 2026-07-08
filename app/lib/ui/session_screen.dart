import 'dart:typed_data';
import 'package:flutter/material.dart';

import '../domain/errors.dart';
import '../domain/session.dart';
import '../fakes/fake_voice_api.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/voice_api.dart';
import 'error_handling.dart';

class SessionScreen extends StatefulWidget {
  const SessionScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.sessionId,
    required this.voiceApi,
    this.initialTurns = const [],
    this.voiceRecorder,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final String sessionId;
  final VoiceApi voiceApi;
  final VoiceRecorder? voiceRecorder;

  /// Pre-loaded transcript — empty for a new session; resume paths pass the
  /// ordered turns they fetched.
  final List<TurnEntry> initialTurns;

  @override
  State<SessionScreen> createState() => _SessionScreenState();
}

class _SessionScreenState extends State<SessionScreen> {
  late final List<TurnEntry> _turns = List.of(widget.initialTurns);
  final _input = TextEditingController();
  final _scroll = ScrollController();
  late final VoiceRecorder? _recorder = widget.voiceRecorder;

  bool _sending = false;
  bool _ended = false;
  bool _recording = false;
  bool _voiceUnavailable = false;
  String? _voiceErrorMessage;
  DateTime? _recordingStartTime;

  @override
  void initState() {
    super.initState();
    // Resume paths arrive with a full transcript: open at the latest
    // exchange, not the oldest message.
    if (_turns.isNotEmpty) _showLatest();
  }

  @override
  void dispose() {
    _recorder?.dispose();
    _scroll.dispose();
    _input.dispose();
    super.dispose();
  }

  /// ListView stays anchored to its current offset when items are appended,
  /// so newly added turns end up below the fold once the transcript exceeds
  /// the viewport. Jump after the frame in which the new items are laid out.
  void _showLatest() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scroll.hasClients) return;
      _scroll.jumpTo(_scroll.position.maxScrollExtent);
    });
  }

  Future<void> _endSession() async {
    try {
      await widget.sessionApi.endSession(widget.sessionId);
      if (!mounted) return;
      // §4: ended is terminal — the screen goes read-only, no way back.
      setState(() => _ended = true);
    } on SessionEnded {
      // Already ended elsewhere — same terminal state (scope §3).
      if (!mounted) return;
      setState(() => _ended = true);
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(
        context,
        widget.identity,
        widget.sessionApi,
        widget.voiceApi,
      );
    } on TransportError {
      // The end never reached the backend: not ended, nothing lost — the
      // End affordance stays and tapping it again is the retry.
      if (!mounted) return;
      await showConnectionProblem(context);
    } on SessionApiException {
      if (!mounted) return;
      await showCantOpenSession(context);
    }
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending || _ended) return;

    setState(() => _sending = true);
    try {
      final result = await widget.sessionApi.turn(widget.sessionId, text);
      if (!mounted) return;
      setState(() {
        final now = DateTime.now();
        _turns
          ..add(TurnEntry(role: TurnRole.user, content: text, ts: now))
          ..add(
            TurnEntry(
              role: TurnRole.tutor,
              content: result.tutorResponse,
              ts: now,
            ),
          );
        _input.clear();
      });
      _showLatest();
    } on SessionEnded {
      // Ended under us (e.g. another device): ended state, input disabled
      // (scope §3) — the unsent message is dropped, not appended.
      if (!mounted) return;
      setState(() => _ended = true);
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(
        context,
        widget.identity,
        widget.sessionApi,
        widget.voiceApi,
      );
    } on TransportError {
      // The turn may never have reached the backend. Nothing is appended and
      // `_input` is NOT cleared (that only happens on success) — the unsent
      // message survives in the field, so "try again" is tapping send again.
      if (!mounted) return;
      await showConnectionProblem(context);
    } on SessionApiException {
      // SessionForbidden / SessionNotFoundError: shared surface, back home.
      if (!mounted) return;
      await showCantOpenSession(context);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _toggleMic() async {
    if (_sending || _ended || _voiceUnavailable) return;

    if (!_recording) {
      // Start recording
      if (_recorder == null) {
        // Test environment: simulate immediate recording
        if (!mounted) return;
        setState(() {
          _recording = true;
          _recordingStartTime = DateTime.now();
          _voiceErrorMessage = null;
        });
        return;
      }

      try {
        await _recorder.start();
        if (!mounted) return;
        setState(() {
          _recording = true;
          _recordingStartTime = DateTime.now();
          _voiceErrorMessage = null;
        });
      } catch (e) {
        // Microphone permission denied or unavailable
        if (!mounted) return;
        setState(() {
          _voiceErrorMessage =
              "This app needs microphone access to record your questions";
        });
      }
    } else {
      // Stop recording and send
      Uint8List? audio;
      if (_recorder == null) {
        // Test environment: use dummy audio
        audio = Uint8List(100);
      } else {
        audio = await _recorder.stop();
      }

      if (!mounted) return;

      if (audio == null || audio.isEmpty) {
        setState(() {
          _recording = false;
          _recordingStartTime = null;
        });
        return;
      }

      setState(() {
        _recording = false;
        _recordingStartTime = null;
        _sending = true;
      });

      await _sendVoiceTurn(audio);
    }
  }

  Future<void> _sendVoiceTurn(Uint8List audio) async {
    try {
      final result = await widget.voiceApi.voiceTurn(
        widget.sessionId,
        audio,
        contentType: 'audio/m4a',
      );

      if (!mounted) return;

      // Extract answer text from answer parts (text parts only, in order)
      final answerText = result.answerParts
          .whereType<TextAnswerPart>()
          .map((part) => part.text)
          .join(' ');

      setState(() {
        final now = DateTime.now();
        // Transcript appears first (exactly like typed turn)
        _turns.add(
          TurnEntry(role: TurnRole.user, content: result.transcript, ts: now),
        );
        // Then the tutor's spoken answer
        _turns.add(
          TurnEntry(role: TurnRole.tutor, content: answerText, ts: now),
        );
      });
      _showLatest();
    } on VoiceUnavailable {
      // Voice backend unavailable — amber degradation, mic disabled
      if (!mounted) return;
      setState(() {
        _voiceUnavailable = true;
        _voiceErrorMessage =
            "Spoken answers aren't available right now — text still works";
      });
    } on UnsupportedAudioFormat {
      if (!mounted) return;
      setState(() {
        _voiceErrorMessage =
            "That audio format isn't supported — try recording again";
      });
    } on EmptyRecording {
      if (!mounted) return;
      setState(() {
        _voiceErrorMessage =
            "That recording was too short — please speak your question clearly";
      });
    } on UnintelligibleQuery {
      if (!mounted) return;
      setState(() {
        _voiceErrorMessage =
            "I couldn't understand that — could you try again more clearly?";
      });
    } on QueryTooLong {
      if (!mounted) return;
      setState(() {
        _voiceErrorMessage =
            "That question is too long — try breaking it into smaller parts";
      });
    } on RecordingTooLarge {
      if (!mounted) return;
      setState(() {
        _voiceErrorMessage =
            "That recording is too large — keep your questions under a minute";
      });
    } on SessionEnded {
      if (!mounted) return;
      setState(() => _ended = true);
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(
        context,
        widget.identity,
        widget.sessionApi,
        widget.voiceApi,
      );
    } on TransportError {
      // Recording preserved — "try again" is tapping mic again
      if (!mounted) return;
      await showConnectionProblem(context);
    } on SessionApiException {
      if (!mounted) return;
      await showCantOpenSession(context);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Widget _bubble(BuildContext context, TurnEntry turn) {
    final isUser = turn.role == TurnRole.user;
    final colors = Theme.of(context).colorScheme;
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: const BoxConstraints(maxWidth: 320),
        decoration: BoxDecoration(
          color: isUser
              ? colors.primaryContainer
              : colors.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(turn.content),
      ),
    );
  }

  String _formatElapsed() {
    if (_recordingStartTime == null) return '';
    final elapsed = DateTime.now().difference(_recordingStartTime!);
    final seconds = elapsed.inSeconds;
    return '${seconds}s';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Session'),
        actions: [
          if (!_ended)
            TextButton(
              onPressed: _endSession,
              child: const Text('End session'),
            ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: _turns.isEmpty
                ? const Center(child: Text('No messages yet'))
                : ListView.builder(
                    controller: _scroll,
                    itemCount: _turns.length,
                    itemBuilder: (context, i) => _bubble(context, _turns[i]),
                  ),
          ),
          if (_voiceUnavailable && _voiceErrorMessage != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              color: Colors.amber.shade100,
              child: Text(
                _voiceErrorMessage!,
                style: TextStyle(color: Colors.amber.shade900),
              ),
            ),
          if (!_voiceUnavailable && _voiceErrorMessage != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              color: Colors.red.shade100,
              child: Text(
                _voiceErrorMessage!,
                style: TextStyle(color: Colors.red.shade900),
              ),
            ),
          if (_ended)
            const Padding(
              padding: EdgeInsets.all(8),
              child: Text('Session ended'),
            ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  IconButton(
                    icon: Icon(
                      _recording ? Icons.stop : Icons.mic,
                      color: _recording ? Colors.red : null,
                    ),
                    onPressed: (_sending || _ended || _voiceUnavailable)
                        ? null
                        : _toggleMic,
                  ),
                  if (_recording)
                    Padding(
                      padding: const EdgeInsets.only(left: 4),
                      child: Text(
                        _formatElapsed(),
                        style: const TextStyle(
                          color: Colors.red,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: _input,
                      // Only the ended state disables the field. Disabling on
                      // `_sending` would unfocus it and dismiss the keyboard
                      // on every send once the port has real latency; the
                      // `_send` guard + disabled send button already prevent
                      // double-send.
                      enabled: !_ended,
                      onSubmitted: (_) => _send(),
                      decoration: const InputDecoration(
                        hintText: 'Type a message…',
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: (_sending || _ended) ? null : _send,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
