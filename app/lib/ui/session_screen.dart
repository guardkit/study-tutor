import 'dart:async';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../adapters/audio_playback.dart';
import '../adapters/voice_recorder.dart';
import '../domain/errors.dart';
import '../domain/session.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/voice_api.dart';
import 'error_handling.dart';
import 'formatting.dart';
import 'gamification/celebration_sheet.dart';
import 'progress_store.dart';
import 'theme/motion.dart';
import 'transcript_view.dart';

class SessionScreen extends StatefulWidget {
  const SessionScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.sessionId,
    required this.voiceApi,
    this.subject,
    this.initialTurns = const [],
    this.voiceRecorder,
    this.player,
    this.clock,
    this.progressStore,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final String sessionId;
  final VoiceApi voiceApi;

  /// The app-wide student-model store (spec §6.2). Refreshed after a settled
  /// end so the Home header/Progress screen reflect the new totals. Null in
  /// widget tests that inject the screen without a store.
  final ProgressStore? progressStore;

  /// The session subject/topic — title-cased for the AppBar (spec §3). Null in
  /// widget tests that inject the screen directly, falling back to 'Session'.
  final String? subject;

  final VoiceRecorder? voiceRecorder;

  /// Sequential TTS playback for spoken answers (spec §5.2). Null in the test
  /// environment (just_audio needs platform channels) — playback is skipped.
  final AudioPlayback? player;

  /// Pre-loaded transcript — empty for a new session; resume paths pass the
  /// ordered turns they fetched.
  final List<TurnEntry> initialTurns;

  /// Injectable clock for the recording-elapsed label (tests drive it with a
  /// fake clock). Defaults to [DateTime.now].
  final DateTime Function()? clock;

  @override
  State<SessionScreen> createState() => _SessionScreenState();
}

/// The optimistic user bubble shown the instant a turn is sent, before the
/// reply arrives (spec §3/§4 — kills the 15–30 s frozen wall). For text turns
/// it carries the typed message; for voice turns the transcript isn't known
/// yet so it renders a neutral placeholder.
class _Optimistic {
  const _Optimistic({this.text, required this.isVoice});
  final String? text;
  final bool isVoice;
}

class _SessionScreenState extends State<SessionScreen>
    with SingleTickerProviderStateMixin {
  late final List<TurnEntry> _turns = List.of(widget.initialTurns);
  final _input = TextEditingController();
  final _scroll = ScrollController();
  late final VoiceRecorder? _recorder = widget.voiceRecorder;

  bool _sending = false;
  bool _ended = false;
  bool _recording = false;
  bool _voiceUnavailable = false;
  bool _playing = false;

  /// The in-flight optimistic user bubble (null when none pending).
  _Optimistic? _optimistic;

  /// Whether to show the tutor "typing" indicator while awaiting a reply.
  bool _awaiting = false;

  /// Dismissible banner state (spec §3: themed MaterialBanner replaces the
  /// hardcoded amber/red containers).
  String? _bannerMessage;
  bool _bannerIsError = false;

  DateTime? _recordingStartTime;
  Timer? _elapsedTicker;
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: AppMotion.flamePulse,
  );

  @override
  void initState() {
    super.initState();
    // Resume paths arrive with a full transcript: open at the latest exchange,
    // not the oldest message.
    if (_turns.isNotEmpty) _scrollToBottom(animate: false);
  }

  @override
  void dispose() {
    _elapsedTicker?.cancel();
    _pulse.dispose();
    _recorder?.dispose();
    widget.player?.dispose();
    _scroll.dispose();
    _input.dispose();
    super.dispose();
  }

  /// The ListView stays anchored to its offset when items append, so new turns
  /// fall below the fold. Scroll after the frame in which they are laid out —
  /// [animate] `easeOutCubic` for sends, instant on first open.
  void _scrollToBottom({bool animate = true}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scroll.hasClients) return;
      final target = _scroll.position.maxScrollExtent;
      if (animate) {
        _scroll
            .animateTo(
              target,
              duration: AppMotion.standard,
              curve: AppMotion.standardCurve,
            )
            .then((_) {
          // The estimated extent can grow as off-screen items lay in during
          // the animation; snap to the true bottom on completion so the newest
          // exchange is fully in view.
          if (mounted && _scroll.hasClients) {
            _scroll.jumpTo(_scroll.position.maxScrollExtent);
          }
        });
      } else {
        _scroll.jumpTo(target);
      }
    });
  }

  void _showBanner(String message, {bool isError = true}) {
    setState(() {
      _bannerMessage = message;
      _bannerIsError = isError;
    });
  }

  Future<void> _endSession() async {
    try {
      final result = await widget.sessionApi.endSession(widget.sessionId);
      if (!mounted) return;
      // §4: ended is terminal — the screen goes read-only immediately. Stop any
      // in-progress recording so its 60 s hard-stop timer can't fire post-end.
      _recorder?.cancel();
      setState(() => _ended = true);

      // §6.2: a non-null settlement block celebrates, then returns to Home and
      // refreshes progress. A null block is the plain end path — NO celebration
      // chrome, ever. The block is nullable: absent means absent.
      final gamification = result.gamification;
      if (gamification != null) {
        await showCelebrationSheet(context, gamification);
        if (!mounted) return;
        widget.progressStore
            ?.refresh(streakExtended: gamification.streakExtended);
        // Return to Home (only when there is somewhere to pop to — a widget
        // test may inject this screen as the root route).
        if (Navigator.of(context).canPop()) Navigator.of(context).pop();
      }
    } on SessionEnded {
      if (!mounted) return;
      setState(() => _ended = true);
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(context, widget.identity, widget.sessionApi, widget.voiceApi);
    } on TransportError {
      // The end never reached the backend: not ended, nothing lost — the End
      // affordance stays and tapping it again is the retry.
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

    // Optimistic: show the user bubble + typing indicator immediately.
    setState(() {
      _sending = true;
      _optimistic = _Optimistic(text: text, isVoice: false);
      _awaiting = true;
      _input.clear();
    });
    _scrollToBottom();

    try {
      final result = await widget.sessionApi.turn(widget.sessionId, text);
      if (!mounted) return;
      setState(() {
        final now = DateTime.now();
        _turns
          ..add(TurnEntry(role: TurnRole.user, content: text, ts: now))
          ..add(TurnEntry(role: TurnRole.tutor, content: result.tutorResponse, ts: now));
        _optimistic = null;
        _awaiting = false;
      });
      _scrollToBottom();
    } on SessionEnded {
      // Ended under us (e.g. another device): roll the optimistic bubble back,
      // keep the unsent text in the (now disabled) field.
      if (!mounted) return;
      setState(() {
        _ended = true;
        _optimistic = null;
        _awaiting = false;
        _input.text = text;
      });
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(context, widget.identity, widget.sessionApi, widget.voiceApi);
    } on TransportError {
      // The turn may never have reached the backend: roll back the optimistic
      // bubble and restore the unsent text so the retry affordance (send again)
      // resends the exact message — unchanged connection-problem behaviour.
      if (!mounted) return;
      setState(() {
        _optimistic = null;
        _awaiting = false;
        _input.text = text;
      });
      await showConnectionProblem(context);
    } on SessionApiException {
      // SessionForbidden / SessionNotFoundError: shared surface, back home.
      // Restore the unsent text (the turn never landed) — same as the other
      // non-success paths.
      if (!mounted) return;
      setState(() {
        _optimistic = null;
        _awaiting = false;
        _input.text = text;
      });
      await showCantOpenSession(context);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _toggleMic() async {
    final recorder = _recorder;
    // A null recorder means voice capture is unavailable, so the mic button is
    // disabled to match (see [_micButton]) and recording is never attempted.
    if (recorder == null || _sending || _ended || _voiceUnavailable) return;

    if (!_recording) {
      // Start recording.
      try {
        await recorder.start(onMaxDuration: _onAutoStopped);
        if (!mounted) return;
        _startRecordingUi();
      } catch (_) {
        // Microphone permission denied or unavailable — mic stays enabled so
        // the user can retry (spec §4: no permanently dead mic).
        if (!mounted) return;
        _showBanner(
          "This app needs microphone access to record your questions",
        );
      }
      return;
    }

    // Stop recording and send.
    Uint8List? audio;
    try {
      audio = await recorder.stop();
    } on RecordingTooLarge {
      if (!mounted) return;
      _stopRecordingUi();
      _showBanner(
        "That recording is too large — keep your questions under a minute",
      );
      return;
    }

    if (!mounted) return;

    if (audio == null || audio.isEmpty) {
      _stopRecordingUi();
      _showBanner("That recording was too short — try again");
      return;
    }

    _stopRecordingUi();
    setState(() {
      _sending = true;
      _optimistic = const _Optimistic(isVoice: true);
      _awaiting = true;
    });
    _scrollToBottom();
    await _sendVoiceTurn(audio);
  }

  /// The 60-second hard-stop fired (design §6.1/§6.3): send the captured audio
  /// on the user's behalf and re-sync the recording UI, instead of dropping the
  /// recording. Errors from the auto-stop (e.g. an over-cap recording) surface
  /// as a banner rather than an uncaught async exception.
  void _onAutoStopped(Uint8List? audio, Object? error) {
    if (!mounted) return;
    _stopRecordingUi();
    // The hard-stop timer fires independently of screen state, so re-apply the
    // manual-send guards (_toggleMic): never send on an ended session, over an
    // in-flight send, or once voice has been marked unavailable.
    if (_ended || _sending || _voiceUnavailable) return;
    if (error is RecordingTooLarge) {
      _showBanner(
        "That recording is too large — keep your questions under a minute",
      );
      return;
    }
    if (audio == null || audio.isEmpty) {
      _showBanner("That recording was too short — try again");
      return;
    }
    setState(() {
      _sending = true;
      _optimistic = const _Optimistic(isVoice: true);
      _awaiting = true;
    });
    _scrollToBottom();
    unawaited(_sendVoiceTurn(audio));
  }

  DateTime _now() => (widget.clock ?? DateTime.now)();

  void _startRecordingUi() {
    setState(() {
      _recording = true;
      _recordingStartTime = _now();
      _bannerMessage = null;
    });
    _pulse.repeat(reverse: true);
    _elapsedTicker?.cancel();
    _elapsedTicker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  void _stopRecordingUi() {
    _elapsedTicker?.cancel();
    _elapsedTicker = null;
    _pulse.stop();
    _pulse.value = 0;
    setState(() {
      _recording = false;
      _recordingStartTime = null;
    });
  }

  Future<void> _sendVoiceTurn(Uint8List audio) async {
    try {
      final result = await widget.voiceApi.voiceTurn(
        widget.sessionId,
        audio,
        contentType: 'audio/m4a',
      );
      if (!mounted) return;

      // Answer text = text parts joined in order (as today).
      final answerText = result.answerParts
          .whereType<TextAnswerPart>()
          .map((part) => part.text)
          .join(' ');

      setState(() {
        final now = DateTime.now();
        _turns
          ..add(TurnEntry(role: TurnRole.user, content: result.transcript, ts: now))
          ..add(TurnEntry(role: TurnRole.tutor, content: answerText, ts: now));
        _optimistic = null;
        _awaiting = false;
      });
      _scrollToBottom();

      // TTS: fetch + play the spoken answer sequentially (spec §5.2).
      unawaited(_playAnswer(result));
    } on VoiceUnavailable {
      if (!mounted) return;
      _clearPending();
      setState(() => _voiceUnavailable = true);
      _showBanner(
        "Spoken answers aren't available right now — text still works",
        isError: false,
      );
    } on UnsupportedAudioFormat {
      _voiceError("That audio format isn't supported — try recording again");
    } on EmptyRecording {
      _voiceError(
        "That recording was too short — please speak your question clearly",
      );
    } on UnintelligibleQuery {
      _voiceError(
        "I couldn't understand that — could you try again more clearly?",
      );
    } on QueryTooLong {
      _voiceError(
        "That question is too long — try breaking it into smaller parts",
      );
    } on RecordingTooLarge {
      _voiceError(
        "That recording is too large — keep your questions under a minute",
      );
    } on SessionEnded {
      if (!mounted) return;
      _clearPending();
      setState(() => _ended = true);
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(context, widget.identity, widget.sessionApi, widget.voiceApi);
    } on TransportError {
      if (!mounted) return;
      _clearPending();
      await showConnectionProblem(context);
    } on SessionApiException {
      if (!mounted) return;
      _clearPending();
      await showCantOpenSession(context);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  void _voiceError(String message) {
    if (!mounted) return;
    _clearPending();
    _showBanner(message);
  }

  void _clearPending() {
    setState(() {
      _optimistic = null;
      _awaiting = false;
    });
  }

  Future<void> _playAnswer(VoiceTurnResult result) async {
    final player = widget.player;
    if (player == null) return;
    final parts = result.answerParts.whereType<AudioAnswerPart>().toList()
      ..sort((a, b) => a.seq.compareTo(b.seq));
    if (parts.isEmpty) return;
    try {
      final chunks = <Uint8List>[];
      for (final part in parts) {
        chunks.add(
          await widget.voiceApi.fetchAudioChunk(widget.sessionId, part.chunkId),
        );
      }
      if (!mounted) return;
      setState(() => _playing = true);
      await player.playSequential(chunks);
    } catch (_) {
      // Playback failure must not break the turn — the text is already shown.
    } finally {
      if (mounted) setState(() => _playing = false);
    }
  }

  Future<void> _stopPlayback() async {
    await widget.player?.stop();
    if (mounted) setState(() => _playing = false);
  }

  double _bubbleMaxWidth(BuildContext context) {
    // Spec §4: 76% of screen width, capped at 560 (replaces the 320 hardcode).
    return math.min(560.0, MediaQuery.of(context).size.width * 0.76);
  }

  Widget _optimisticBubble(BuildContext context, _Optimistic pending) {
    final colors = Theme.of(context).colorScheme;
    return Align(
      alignment: Alignment.centerRight,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: BoxConstraints(maxWidth: _bubbleMaxWidth(context)),
        decoration: BoxDecoration(
          color: colors.primaryContainer,
          borderRadius: BorderRadius.circular(12),
        ),
        child: pending.isVoice
            ? Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.mic, size: 16, color: colors.onPrimaryContainer),
                  const SizedBox(width: 6),
                  const Text('Recording sent…'),
                ],
              )
            : Text(pending.text ?? ''),
      ),
    );
  }

  Widget _typingIndicator(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Semantics(
      label: 'Tutor is typing',
      liveRegion: true,
      child: Align(
      key: const Key('typing-indicator'),
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: colors.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (var i = 0; i < 3; i++)
              Padding(
                padding: EdgeInsets.only(left: i == 0 ? 0 : 4),
                child: CircleAvatar(
                  radius: 3,
                  backgroundColor: colors.onSurfaceVariant,
                ),
              ),
          ],
        ),
      ),
      ),
    );
  }

  String _formatElapsed() {
    if (_recordingStartTime == null) return '0s';
    return '${_now().difference(_recordingStartTime!).inSeconds}s';
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(titleCaseSubject(widget.subject)),
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
            child: TranscriptView(
              turns: _turns,
              controller: _scroll,
              // The optimistic user bubble + typing indicator are the live
              // session's pending items, appended after the confirmed turns.
              trailing: [
                if (_optimistic != null) _optimisticBubble(context, _optimistic!),
                if (_awaiting) _typingIndicator(context),
              ],
              emptyState: const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'Ask your first question below — type it or tap the '
                    'mic to speak.',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ),
          ),
          if (_bannerMessage != null)
            MaterialBanner(
              backgroundColor: _bannerIsError
                  ? colors.errorContainer
                  : colors.tertiaryContainer,
              content: Semantics(
                liveRegion: true,
                child: Text(
                  _bannerMessage!,
                  style: TextStyle(
                    color: _bannerIsError
                        ? colors.onErrorContainer
                        : colors.onTertiaryContainer,
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => setState(() => _bannerMessage = null),
                  child: const Text('Dismiss'),
                ),
              ],
            ),
          if (_playing)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Row(
                children: [
                  const Icon(Icons.volume_up, size: 18),
                  const SizedBox(width: 8),
                  const Text('Playing answer…'),
                  const Spacer(),
                  TextButton(
                    onPressed: _stopPlayback,
                    child: const Text('Stop'),
                  ),
                ],
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
                  _micButton(colors),
                  if (_recording)
                    Padding(
                      padding: const EdgeInsets.only(left: 4),
                      child: Semantics(
                        label: 'Recording, ${_formatElapsed()}',
                        container: true,
                        excludeSemantics: true,
                        child: Text(
                          _formatElapsed(),
                          style: TextStyle(
                            color: colors.error,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: _input,
                      // Only the ended state disables the field. Disabling on
                      // `_sending` would dismiss the keyboard on every send; the
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

  /// 56 dp FAB-style mic (spec §3): pulsing red while recording.
  Widget _micButton(ColorScheme colors) {
    final disabled =
        _recorder == null || _sending || _ended || _voiceUnavailable;
    return SizedBox(
      width: 56,
      height: 56,
      child: AnimatedBuilder(
        animation: _pulse,
        builder: (context, child) {
          final background = _recording
              ? Color.lerp(colors.errorContainer, colors.error, _pulse.value)
              : colors.surfaceContainerHighest;
          return DecoratedBox(
            decoration: BoxDecoration(
              color: disabled ? colors.surfaceContainerHigh : background,
              shape: BoxShape.circle,
            ),
            child: child,
          );
        },
        child: IconButton(
          iconSize: 28,
          icon: Icon(
            _recording ? Icons.stop : Icons.mic,
            color: _recording ? colors.onError : null,
            semanticLabel: _voiceUnavailable
                ? 'Voice input unavailable'
                : (_recording ? 'Stop recording' : 'Record a question'),
          ),
          onPressed: disabled ? null : _toggleMic,
        ),
      ),
    );
  }
}
