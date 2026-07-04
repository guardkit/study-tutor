import 'package:flutter/material.dart';

import '../domain/errors.dart';
import '../domain/session.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import 'error_handling.dart';

class SessionScreen extends StatefulWidget {
  const SessionScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.sessionId,
    this.initialTurns = const [],
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final String sessionId;

  /// Pre-loaded transcript — empty for a new session; resume paths pass the
  /// ordered turns they fetched.
  final List<TurnEntry> initialTurns;

  @override
  State<SessionScreen> createState() => _SessionScreenState();
}

class _SessionScreenState extends State<SessionScreen> {
  late final List<TurnEntry> _turns = List.of(widget.initialTurns);
  final _input = TextEditingController();
  bool _sending = false;
  bool _ended = false;

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
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
      routeToSignIn(context, widget.identity, widget.sessionApi);
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
          ..add(TurnEntry(
              role: TurnRole.tutor, content: result.tutorResponse, ts: now));
        _input.clear();
      });
    } on SessionEnded {
      // Ended under us (e.g. another device): ended state, input disabled
      // (scope §3) — the unsent message is dropped, not appended.
      if (!mounted) return;
      setState(() => _ended = true);
    } on Unauthenticated {
      if (!mounted) return;
      routeToSignIn(context, widget.identity, widget.sessionApi);
    } on SessionApiException {
      // SessionForbidden / SessionNotFoundError: shared surface, back home.
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
          color: isUser ? colors.primaryContainer : colors.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(turn.content),
      ),
    );
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
                    itemCount: _turns.length,
                    itemBuilder: (context, i) => _bubble(context, _turns[i]),
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
                  Expanded(
                    child: TextField(
                      controller: _input,
                      enabled: !_sending && !_ended,
                      onSubmitted: (_) => _send(),
                      decoration: const InputDecoration(
                          hintText: 'Type a message…'),
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
