import 'package:flutter/material.dart';

import 'session_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Home')),
      body: Center(
        child: FilledButton(
          onPressed: () {
            // Placeholder navigation only — wave-6 wires startSession.
            Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => const SessionScreen()),
            );
          },
          child: const Text('Start new session'),
        ),
      ),
    );
  }
}
