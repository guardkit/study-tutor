import 'package:flutter/material.dart';

import 'home_screen.dart';

class SignInScreen extends StatelessWidget {
  const SignInScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Study Tutor',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () {
                // Placeholder navigation only — wave-6 wires IdentityProvider.
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute<void>(builder: (_) => const HomeScreen()),
                );
              },
              child: const Text('Sign in'),
            ),
          ],
        ),
      ),
    );
  }
}
