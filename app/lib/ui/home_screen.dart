import 'package:flutter/material.dart';

import '../domain/session.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
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

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    final active =
        await widget.sessionApi.listSessions(status: SessionStatus.active);
    if (!mounted) return;
    setState(() => _active = active);
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
    final started =
        await widget.sessionApi.startSession(subject: defaultSubject);
    if (!mounted) return;
    await _open(SessionScreen(
      sessionApi: widget.sessionApi,
      sessionId: started.sessionId,
      initialTurns: started.turns ?? const [],
    ));
  }

  Future<void> _resume(SessionSummary summary) async {
    final resumed =
        await widget.sessionApi.resumeSession(summary.sessionId);
    if (!mounted) return;
    await _open(SessionScreen(
      sessionApi: widget.sessionApi,
      sessionId: resumed.sessionId,
      initialTurns: resumed.turns,
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Home')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (final summary in _active)
            Card(
              child: ListTile(
                title: Text(summary.subject ?? 'Session'),
                subtitle: Text('${summary.turnCount} turns'),
                trailing: FilledButton.tonal(
                  onPressed: () => _resume(summary),
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
            onPressed: _startNewSession,
            child: const Text('Start new session'),
          ),
        ],
      ),
    );
  }
}
