import 'package:flutter/material.dart';

import '../domain/session.dart';
import '../ports/session_api.dart';

class SessionScreen extends StatefulWidget {
  const SessionScreen({
    super.key,
    required this.sessionApi,
    required this.sessionId,
    this.initialTurns = const [],
  });

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

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending) return;

    setState(() => _sending = true);
    final result = await widget.sessionApi.turn(widget.sessionId, text);
    if (!mounted) return;
    setState(() {
      final now = DateTime.now();
      _turns
        ..add(TurnEntry(role: TurnRole.user, content: text, ts: now))
        ..add(TurnEntry(
            role: TurnRole.tutor, content: result.tutorResponse, ts: now));
      _input.clear();
      _sending = false;
    });
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
      appBar: AppBar(title: const Text('Session')),
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
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      enabled: !_sending,
                      onSubmitted: (_) => _send(),
                      decoration: const InputDecoration(
                          hintText: 'Type a message…'),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: _sending ? null : _send,
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
