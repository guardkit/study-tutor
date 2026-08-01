import 'package:flutter/material.dart';

import '../domain/errors.dart';
import '../domain/session.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/voice_api.dart';
import 'error_handling.dart';
import 'formatting.dart';
import 'transcript_view.dart';

/// Session-History screen (spec §3): a read-only list of the student's ENDED
/// sessions. Tapping one loads its ordered transcript via `turns_since` (from
/// row 0) and opens it read-only in a [TranscriptView] — no input bar, nothing
/// to send.
///
/// The two reads it uses (`list_sessions` with the status filter, then
/// `turns_since`) never mutate a session: History never starts, turns, or ends
/// one. `turns_since` reads ended sessions (unlike `resume_session`), so it is
/// the verb that loads a finished transcript.
class HistoryScreen extends StatefulWidget {
  const HistoryScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.voiceApi,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;

  /// Needed only so an [Unauthenticated] mid-list can route back to sign-in
  /// through the shared [routeToSignIn] surface.
  final VoiceApi voiceApi;

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<SessionSummary> _ended = const [];
  bool _loading = true;

  /// In-flight guard for opening a transcript — a double-tap must not push the
  /// transcript route twice.
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final ended =
          await widget.sessionApi.listSessions(status: SessionStatus.ended);
      if (!mounted) return;
      setState(() {
        _ended = ended;
        _loading = false;
      });
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(
          context, widget.identity, widget.sessionApi, widget.voiceApi);
    } on TransportError {
      // Stay put with whatever we had; pull-to-refresh is the retry.
      if (!mounted) return;
      setState(() => _loading = false);
      await showConnectionProblem(context);
    }
  }

  Future<void> _open(SessionSummary summary) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final result = await widget.sessionApi.turnsSince(summary.sessionId, 0);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => _TranscriptScreen(
            subject: summary.subject,
            turns: result.turns,
          ),
        ),
      );
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(
          context, widget.identity, widget.sessionApi, widget.voiceApi);
    } on TransportError {
      if (!mounted) return;
      await showConnectionProblem(context);
    } on SessionApiException {
      // SessionForbidden / SessionNotFoundError — the shared surface.
      if (!mounted) return;
      await showCantOpenSession(context);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Session history')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                children: [
                  if (_ended.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 24),
                      child: Center(
                        child: Text(
                          "No finished sessions yet — when you wrap one up "
                          "it'll show up here.",
                          textAlign: TextAlign.center,
                          style: theme.textTheme.bodyLarge?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant),
                        ),
                      ),
                    )
                  else
                    for (final summary in _ended) _historyCard(theme, summary),
                ],
              ),
      ),
    );
  }

  Widget _historyCard(ThemeData theme, SessionSummary summary) {
    final title = titleCaseSubject(summary.subject);
    final when = relativeTime(summary.lastActivity);
    return Semantics(
      button: true,
      label: '$title session, ${summary.turnCount} turns, last active $when. '
          'Opens the transcript.',
      child: Card(
        child: ListTile(
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          title: Text(title, style: theme.textTheme.titleMedium),
          subtitle: Row(
            children: [
              Text('${summary.turnCount} turns'),
              Text(
                '  ·  $when',
                style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
              ),
            ],
          ),
          trailing: const Icon(Icons.chevron_right),
          onTap: _busy ? null : () => _open(summary),
        ),
      ),
    );
  }
}

/// The read-only transcript page a history tap opens: an app bar titled with the
/// session subject and a [TranscriptView] of the ordered turns. No input bar.
class _TranscriptScreen extends StatelessWidget {
  const _TranscriptScreen({required this.subject, required this.turns});

  final String? subject;
  final List<TurnEntry> turns;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(titleCaseSubject(subject))),
      body: TranscriptView(
        turns: turns,
        padding: const EdgeInsets.symmetric(vertical: 8),
        emptyState: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'No messages in this session.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyLarge
                  ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
          ),
        ),
      ),
    );
  }
}
