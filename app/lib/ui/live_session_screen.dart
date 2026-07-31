import 'dart:async';

import 'package:flutter/material.dart';

import '../domain/errors.dart';
import '../domain/session.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/voice_api.dart';
import 'error_handling.dart';
import 'formatting.dart';
import 'theme/motion.dart';
import 'transcript_view.dart';

/// A read-only LIVE mirror of the session the Reachy robot is driving.
///
/// The robot's `ask_tutor` uses `start(resume_if_active: true, subject: english)`,
/// so its turns land on the student's ONE active `(student, english)` session
/// (contract §5). The phone — the SAME student — can WATCH that session without
/// touching it: this screen [turnsSince]s (from row 0) to load the current
/// transcript, then POLLS [turnsSince] on [pollInterval] for DELTAS — each poll
/// asks for the rows at index `>= knownRows`, appends just the returned tail to
/// the same [TranscriptView], and advances `knownRows` to the response's `next`
/// (the raw total row count). Update cost is O(new rows), never O(whole
/// conversation): there is no status probe and no full re-fetch. Purely a READ —
/// it never starts, turns, or ends a session, and adds no contract shapes.
///
/// `turns_since` (binding §2.4 addendum) is the ended-tolerant transcript read:
/// unlike `resume_session` (active-only, §4 terminal), it reads ENDED sessions
/// too, so the poll survives the active→ended transition without a SessionEnded.
/// The ended transition is read straight off the poll response's `status`.
///
/// The active→ended transition is graceful: polling stops, the last transcript
/// is kept, and a "session ended" note is shown. The poll timer is cancelled on
/// [dispose] and on the transition, so nothing leaks.
class LiveSessionScreen extends StatefulWidget {
  const LiveSessionScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.voiceApi,
    required this.sessionId,
    this.subject,
    this.pollInterval = const Duration(seconds: 3),
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;

  /// Needed only so an [Unauthenticated] mid-poll can route back to sign-in
  /// through the shared [routeToSignIn] surface.
  final VoiceApi voiceApi;

  final String sessionId;

  /// The session subject — title-cased for the AppBar (spec §3). Null in widget
  /// tests that inject the screen directly, falling back to 'Session'.
  final String? subject;

  /// Injectable so widget tests drive polling on a fake clock instead of real
  /// wall-clock timers (the hermetic gate never sleeps). Defaults to ~3s.
  final Duration pollInterval;

  @override
  State<LiveSessionScreen> createState() => _LiveSessionScreenState();
}

class _LiveSessionScreenState extends State<LiveSessionScreen> {
  final List<TurnEntry> _turns = <TurnEntry>[];
  final _scroll = ScrollController();

  /// The number of transcript ROWS we have already appended — the `since` we
  /// hand to the next [turnsSince] poll. Advanced to the response's `next` (the
  /// raw total row count) after each successful delta so the poll only ever
  /// fetches rows we have not yet rendered.
  int _knownRows = 0;

  bool _loading = true;
  bool _ended = false;

  /// Re-entrancy guard: a poll's async work may outlive its interval, so a
  /// later tick must not start a second overlapping poll.
  bool _polling = false;

  Timer? _timer;

  @override
  void initState() {
    super.initState();
    unawaited(_initialLoad());
  }

  @override
  void dispose() {
    _stopPolling();
    _scroll.dispose();
    super.dispose();
  }

  /// Load the current transcript once, then — if the session is still active —
  /// begin polling. An already-ended session is shown read-only with no timer.
  Future<void> _initialLoad() async {
    try {
      final result = await widget.sessionApi.turnsSince(widget.sessionId, 0);
      if (!mounted) return;
      setState(() {
        _turns.addAll(result.turns);
        _knownRows = result.next;
        _ended = result.status == SessionStatus.ended;
        _loading = false;
      });
      _scrollToBottom(animate: false);
      if (!_ended) _startPolling();
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(
          context, widget.identity, widget.sessionApi, widget.voiceApi);
    } on TransportError {
      // Couldn't reach the backend for the first read — surface it and stay on
      // an empty mirror; there is nothing to poll yet.
      if (!mounted) return;
      setState(() => _loading = false);
      await showConnectionProblem(context);
    } on SessionApiException {
      // SessionForbidden / SessionNotFoundError — the shared "can't open"
      // surface (turns_since never throws SessionEnded: it reads ended too).
      if (!mounted) return;
      setState(() => _loading = false);
      await showCantOpenSession(context);
    }
  }

  void _startPolling() {
    _timer?.cancel();
    _timer = Timer.periodic(widget.pollInterval, (_) => unawaited(_poll()));
  }

  void _stopPolling() {
    _timer?.cancel();
    _timer = null;
  }

  /// One poll cycle: a DELTA read of the rows at index `>= _knownRows`. Any
  /// returned tail is appended into the SAME [TranscriptView] and `_knownRows`
  /// advances to `next`; the active→ended transition is read straight off the
  /// response `status` (turns_since reads ended too, binding §2.4), so a final
  /// turn that lands as the session ends arrives in the same delta and is
  /// appended before we stop — no last turn is missed.
  Future<void> _poll() async {
    if (_polling || !mounted) return;
    _polling = true;
    try {
      final result =
          await widget.sessionApi.turnsSince(widget.sessionId, _knownRows);
      if (!mounted) return;
      final hasNew = result.turns.isNotEmpty;
      final ended = result.status == SessionStatus.ended;
      if (ended) _stopPolling();
      if (hasNew || ended) {
        setState(() {
          _turns.addAll(result.turns);
          _knownRows = result.next;
          if (ended) _ended = true;
        });
      }
      if (hasNew) _scrollToBottom();
    } on Unauthenticated {
      _stopPolling();
      if (!mounted) return;
      routeToSignIn(
          context, widget.identity, widget.sessionApi, widget.voiceApi);
    } on TransportError {
      // Transient: a dropped delta poll is not fatal to a live mirror. `_knownRows`
      // is left un-advanced (only a success moves it), so the next tick re-asks
      // from the same offset and catches up. Keep the last transcript on screen
      // and keep polling — no dialog: a watcher must not be nagged on a flaky beat.
    } on SessionApiException {
      // SessionForbidden / SessionNotFoundError — stop and surface once.
      _stopPolling();
      if (!mounted) return;
      await showCantOpenSession(context);
    } finally {
      _polling = false;
    }
  }

  /// Keep the newest exchange in view as turns append (mirrors the session
  /// screen): scroll after the frame that lays the new items out.
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
          if (mounted && _scroll.hasClients) {
            _scroll.jumpTo(_scroll.position.maxScrollExtent);
          }
        });
      } else {
        _scroll.jumpTo(target);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Flexible(child: Text(titleCaseSubject(widget.subject))),
            const SizedBox(width: 8),
            if (!_ended) _liveBadge(theme),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Expanded(
                  child: TranscriptView(
                    turns: _turns,
                    controller: _scroll,
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    emptyState: Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(
                          _ended
                              ? 'No messages in this session.'
                              : "Waiting for the first question — this updates "
                                  "live as the session goes.",
                          textAlign: TextAlign.center,
                          style: theme.textTheme.bodyLarge?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant),
                        ),
                      ),
                    ),
                  ),
                ),
                if (_ended) _endedNote(theme),
              ],
            ),
    );
  }

  /// A small pulsing-free LIVE chip (informational — Semantics-labelled per
  /// S-A4). The dot uses the [ColorScheme.error] role, not a raw colour.
  Widget _liveBadge(ThemeData theme) {
    final colors = theme.colorScheme;
    return Semantics(
      label: 'Live — this session is updating automatically',
      container: true,
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: colors.errorContainer,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: colors.error,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              'LIVE',
              style: theme.textTheme.labelSmall?.copyWith(
                color: colors.onErrorContainer,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// The graceful-end footer (spec: keep the last transcript, note the end).
  Widget _endedNote(ThemeData theme) {
    final colors = theme.colorScheme;
    return Semantics(
      label: 'This session has ended.',
      container: true,
      excludeSemantics: true,
      child: Container(
        width: double.infinity,
        color: colors.surfaceContainerHighest,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.check_circle_outline,
                size: 18, color: colors.onSurfaceVariant),
            const SizedBox(width: 8),
            Text(
              'Session ended',
              style: theme.textTheme.bodyMedium
                  ?.copyWith(color: colors.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }
}
