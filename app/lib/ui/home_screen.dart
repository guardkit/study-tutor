import 'package:flutter/material.dart';

import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import 'session_screen.dart';

/// Fixed subject for v1 — the build plan allows it; a subject picker is out
/// of scope (scope §7).
const defaultSubject = 'maths';

class HomeScreen extends StatelessWidget {
  const HomeScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;

  Future<void> _startNewSession(BuildContext context) async {
    final started = await sessionApi.startSession(subject: defaultSubject);
    if (!context.mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SessionScreen(
          sessionApi: sessionApi,
          sessionId: started.sessionId,
          initialTurns: started.turns ?? const [],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Home')),
      body: Center(
        child: FilledButton(
          onPressed: () => _startNewSession(context),
          child: const Text('Start new session'),
        ),
      ),
    );
  }
}
