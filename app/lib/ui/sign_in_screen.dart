import 'package:flutter/material.dart';

import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import 'home_screen.dart';

class SignInScreen extends StatelessWidget {
  const SignInScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;

  Future<void> _signIn(BuildContext context) async {
    await identity.signIn();
    if (!context.mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) =>
            HomeScreen(identity: identity, sessionApi: sessionApi),
      ),
    );
  }

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
              onPressed: () => _signIn(context),
              child: const Text('Sign in'),
            ),
          ],
        ),
      ),
    );
  }
}
