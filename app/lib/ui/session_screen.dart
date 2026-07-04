import 'package:flutter/material.dart';

class SessionScreen extends StatelessWidget {
  const SessionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Session')),
      body: Column(
        children: [
          const Expanded(
            child: Center(child: Text('No messages yet')),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  const Expanded(
                    child: TextField(
                      decoration:
                          InputDecoration(hintText: 'Type a message…'),
                    ),
                  ),
                  // Placeholder — wave-6 wires turn().
                  IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: null,
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
