import 'package:flutter/material.dart';

import '../adapters/audio_playback.dart';
import '../adapters/voice_recorder.dart';
import '../domain/errors.dart';
import '../domain/session.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/voice_api.dart';
import 'app_scope.dart';
import 'error_handling.dart';
import 'formatting.dart';
import 'gamification/progress_header_card.dart';
import 'gamification/progress_screen.dart';
import 'history_screen.dart';
import 'live_session_screen.dart';
import 'progress_store.dart';
import 'session_screen.dart';

/// Default subject for v1 — English (AQA 8700/8702), matching the tutor's
/// fine-tune, the Scholar persona, and query_student_model's default. A subject
/// picker is out of scope for v1 (scope §7); when it lands this becomes the
/// fallback rather than a fixed value. The robot's ask_tutor sends this same
/// default, so (student, subject) session pickup matches across phone and robot
/// (recon D6/D8). Previously 'maths' — a stale placeholder with no content
/// behind it; reconciled to the English tutor 2026-07-07 (ASSUM-001).
const defaultSubject = 'english';

/// Warm, specific empty state (spec §1 register) — no fabricated streak data
/// (gamification lands in S-A3), no bare string.
const homeEmptyState =
    "No sessions yet — start one below and it'll show up here.";

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.voiceApi,
    this.progressStore,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final VoiceApi voiceApi;

  /// The app-wide student-model store (spec §2). Optional: resolved from the
  /// ambient [AppScope] when absent so widget tests can inject it directly.
  final ProgressStore? progressStore;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<SessionSummary> _active = const [];
  ProgressStore? _store;

  /// In-flight guard for Start/Resume (same reason as the session screen's
  /// `_sending`): a double-tap must not start two sessions or push two
  /// screens. Held for the whole open-session lifetime — `_open` only
  /// returns when the pushed route pops.
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Resolve the store once (constructor injection wins; else the AppScope),
    // then kick the first load. Safe here — InheritedWidget lookups are allowed
    // in didChangeDependencies, unlike initState.
    _store ??= widget.progressStore ?? AppScope.maybeOf(context)?.progressStore;
    final store = _store;
    if (store != null && !store.hasLoaded) store.load();
  }

  void _openProgress(ProgressStore store) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => ProgressScreen(store: store)),
    );
  }

  /// Open the read-only Session-History screen (spec §3). Reuses Home's already
  /// injected ports; nothing new needs composing in main.dart.
  void _openHistory() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => HistoryScreen(
          identity: widget.identity,
          sessionApi: widget.sessionApi,
          voiceApi: widget.voiceApi,
        ),
      ),
    );
  }

  Future<void> _refresh() async {
    try {
      final active =
          await widget.sessionApi.listSessions(status: SessionStatus.active);
      if (!mounted) return;
      setState(() => _active = active);
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(context, widget.identity, widget.sessionApi, widget.voiceApi);
    } on TransportError {
      // Stay put with whatever list we already had — "try again" is the
      // pull-to-refresh on this list once the connection returns.
      if (!mounted) return;
      await showConnectionProblem(context);
    }
  }

  /// Open the read-only LIVE mirror of an active session (the one the Reachy
  /// robot may be driving). A pure read — it never touches the session — so no
  /// re-list is needed on return and no `_busy` guard is held.
  void _watchLive(SessionSummary summary) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => LiveSessionScreen(
          identity: widget.identity,
          sessionApi: widget.sessionApi,
          voiceApi: widget.voiceApi,
          sessionId: summary.sessionId,
          subject: summary.subject,
        ),
      ),
    );
  }

  /// Push the session screen, then re-list on return — an ended session must
  /// drop off the resume list, an advanced one must show its new turn count.
  Future<void> _open(SessionScreen screen) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => screen),
    );
    if (mounted) await _refresh();
  }

  Future<void> _startNewSession() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final started =
          await widget.sessionApi.startSession(subject: defaultSubject);
      if (!mounted) return;
      await _open(SessionScreen(
        identity: widget.identity,
        sessionApi: widget.sessionApi,
        voiceApi: widget.voiceApi,
        sessionId: started.sessionId,
        subject: defaultSubject,
        initialTurns: started.turns ?? const [],
        voiceRecorder: VoiceRecorder(),
        player: JustAudioPlayback(),
        progressStore: _store,
        streamVoice: true,
      ));
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(context, widget.identity, widget.sessionApi, widget.voiceApi);
    } on TransportError {
      // Nothing was started — stay home; the button works again once
      // `_busy` resets in `finally`.
      if (!mounted) return;
      await showConnectionProblem(context);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _resume(SessionSummary summary) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final resumed =
          await widget.sessionApi.resumeSession(summary.sessionId);
      if (!mounted) return;
      await _open(SessionScreen(
        identity: widget.identity,
        sessionApi: widget.sessionApi,
        voiceApi: widget.voiceApi,
        sessionId: resumed.sessionId,
        subject: summary.subject,
        initialTurns: resumed.turns,
        voiceRecorder: VoiceRecorder(),
        player: JustAudioPlayback(),
        progressStore: _store,
        streamVoice: true,
      ));
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(context, widget.identity, widget.sessionApi, widget.voiceApi);
    } on TransportError {
      // Before the SessionApiException catch-all: a dead network is not
      // "can't open this session". The row stays (it may be perfectly
      // resumable) and there is no re-list — the server is unreachable.
      if (!mounted) return;
      await showConnectionProblem(context);
    } on SessionApiException {
      // SessionForbidden / SessionNotFoundError (and, defensively, a session
      // that ended elsewhere): shared surface, then re-list — the stale row
      // must drop off (scope §3).
      if (!mounted) return;
      await showCantOpenSession(context);
      if (mounted) await _refresh();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _signOut() async {
    await widget.identity.signOut();
    if (!mounted) return;
    routeToSignIn(context, widget.identity, widget.sessionApi, widget.voiceApi);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final displayName = widget.identity.currentPrincipal?.displayName;
    final greeting = displayName == null ? 'Hi there' : 'Hi, $displayName';

    return Scaffold(
      appBar: AppBar(
        title: Text(greeting),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'sign_out') _signOut();
              if (value == 'history') _openHistory();
            },
            itemBuilder: (context) => const [
              PopupMenuItem<String>(
                value: 'history',
                child: Text('Session history'),
              ),
              PopupMenuItem<String>(
                value: 'sign_out',
                child: Text('Sign out'),
              ),
            ],
          ),
        ],
      ),
      // Pull-to-refresh is the retry gesture for a failed list call — without
      // it a TransportError on the initial refresh dead-ends on a stale empty
      // state until some other navigation re-lists.
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            if (_store != null) _progressHeader(_store!),
            for (final summary in _active) _sessionCard(theme, summary),
            if (_active.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Center(
                  child: Text(
                    homeEmptyState,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyLarge
                        ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                  ),
                ),
              ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: _busy ? null : _startNewSession,
              child: const Text('Start new session'),
            ),
          ],
        ),
      ),
    );
  }

  /// The Progress header card (spec §6.1) — always shown, never hidden; it
  /// rebuilds off the store and renders a warm zero-state when there is no
  /// banked data yet.
  Widget _progressHeader(ProgressStore store) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: ListenableBuilder(
        listenable: store,
        builder: (context, _) => ProgressHeaderCard(
          model: store.model,
          aliveToday: store.streakAliveToday,
          onTap: () => _openProgress(store),
        ),
      ),
    );
  }

  Widget _sessionCard(ThemeData theme, SessionSummary summary) {
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        title: Text(
          titleCaseSubject(summary.subject),
          style: theme.textTheme.titleMedium,
        ),
        subtitle: Row(
          children: [
            Text('${summary.turnCount} turns'),
            Text(
              '  ·  ${relativeTime(summary.lastActivity)}',
              style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              tooltip: 'Watch live',
              icon: const Icon(Icons.sensors, semanticLabel: 'Watch live'),
              onPressed: () => _watchLive(summary),
            ),
            const SizedBox(width: 4),
            FilledButton.tonal(
              onPressed: _busy ? null : () => _resume(summary),
              child: const Text('Resume'),
            ),
          ],
        ),
      ),
    );
  }
}
