import 'package:flutter/material.dart';

import '../domain/principal.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/voice_api.dart';
import 'home_screen.dart';

/// SignIn (spec §3): app name in the display face + a one-line purpose + the
/// existing sign-in affordance. When the composed identity provider is a
/// [PrincipalChooser] with more than one principal (the fake has two), a small
/// chooser lets a dev pick who to sign in as. Post-Keycloak this screen is
/// replaced — kept intentionally minimal.
class SignInScreen extends StatelessWidget {
  const SignInScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.voiceApi,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final VoiceApi voiceApi;

  Future<void> _signIn(BuildContext context) async {
    await identity.signIn();
    if (!context.mounted) return;
    _toHome(context);
  }

  Future<void> _signInAs(BuildContext context, Principal principal) async {
    final chooser = identity as PrincipalChooser;
    await chooser.signInAs(principal);
    if (!context.mounted) return;
    _toHome(context);
  }

  void _toHome(BuildContext context) {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => HomeScreen(
          identity: identity,
          sessionApi: sessionApi,
          voiceApi: voiceApi,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final chooser = identity is PrincipalChooser
        ? identity as PrincipalChooser
        : null;
    final choices = chooser?.availablePrincipals ?? const <Principal>[];
    final showChoices = choices.length > 1;

    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // App name in the display face (headlineMedium carries it).
              Text(
                'Study Tutor',
                style: theme.textTheme.headlineMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'Your AI study partner for English — one question at a time.',
                style: theme.textTheme.bodyLarge
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: () => _signIn(context),
                child: const Text('Sign in'),
              ),
              if (showChoices) ...[
                const SizedBox(height: 16),
                Text(
                  'Or sign in as',
                  style: theme.textTheme.labelLarge
                      ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                ),
                const SizedBox(height: 4),
                Wrap(
                  alignment: WrapAlignment.center,
                  spacing: 8,
                  children: [
                    for (final principal in choices)
                      OutlinedButton(
                        onPressed: () => _signInAs(context, principal),
                        child: Text(principal.displayName),
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
