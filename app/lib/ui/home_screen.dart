import 'package:flutter/material.dart';

import '../domain/errors.dart';
import '../domain/session.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import 'error_handling.dart';
import 'session_screen.dart';

/// Fixed subject for v1 — the build plan allows it; a subject picker is out
/// of scope (scope §7).
const defaultSubject = 'maths';

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<SessionSummary> _active = const [];

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

  Future<void> _refresh() async {
    try {
      final active =
          await widget.sessionApi.listSessions(status: SessionStatus.active);
      if (!mounted) return;
      setState(() => _active = active);
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(context, widget.identity, widget.sessionApi);
    } on TransportError {
      // Stay put with whatever list we already had — "try again" is the
      // pull-to-refresh on this list once the connection returns.
      if (!mounted) return;
      await showConnectionProblem(context);
    }
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
        sessionId: started.sessionId,
        initialTurns: started.turns ?? const [],
      ));
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(context, widget.identity, widget.sessionApi);
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
        sessionId: resumed.sessionId,
        initialTurns: resumed.turns,
      ));
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(context, widget.identity, widget.sessionApi);
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Home')),
      // Pull-to-refresh is the retry gesture for a failed list call — without
      // it a TransportError on the initial refresh dead-ends on a stale
      // "No active sessions" until some other navigation re-lists.
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            for (final summary in _active)
              Card(
                child: ListTile(
                  title: Text(summary.subject ?? 'Session'),
                  subtitle: Text('${summary.turnCount} turns'),
                  trailing: FilledButton.tonal(
                    onPressed: _busy ? null : () => _resume(summary),
                    child: const Text('Resume'),
                  ),
                ),
              ),
            if (_active.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: Text('No active sessions')),
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
}
