import 'package:flutter/material.dart';

import '../adapters/keycloak_identity_provider.dart';
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
///
/// TASK-KCA3-004: Now a StatefulWidget with loading/failure/cancel states
/// driven by the adapter's SIGNIN_OUTCOME (SignInCancelled vs SignInFailed).
class SignInScreen extends StatefulWidget {
  const SignInScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.voiceApi,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final VoiceApi voiceApi;

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

enum _SignInState { idle, loading, cancelled, failed }

class _SignInScreenState extends State<SignInScreen> {
  _SignInState _state = _SignInState.idle;
  String? _errorMessage;

  Future<void> _signIn() async {
    // Double-tap guard: ignore if already loading
    if (_state == _SignInState.loading) return;

    setState(() {
      _state = _SignInState.loading;
      _errorMessage = null;
    });

    try {
      await widget.identity.signIn();
      if (!mounted) return;
      _toHome();
    } on SignInCancelled catch (e) {
      // User cancelled sign-in (browser dismissed)
      if (!mounted) return;
      setState(() {
        _state = _SignInState.cancelled;
        _errorMessage = e.message;
      });
    } on SignInFailed catch (e) {
      // Sign-in failed (discovery/IdP/transport error)
      if (!mounted) return;
      setState(() {
        _state = _SignInState.failed;
        _errorMessage = e.message;
      });
    }
  }

  Future<void> _signInAs(Principal principal) async {
    // Double-tap guard: ignore if already loading
    if (_state == _SignInState.loading) return;

    setState(() {
      _state = _SignInState.loading;
      _errorMessage = null;
    });

    try {
      final chooser = widget.identity as PrincipalChooser;
      await chooser.signInAs(principal);
      if (!mounted) return;
      _toHome();
    } on SignInCancelled catch (e) {
      if (!mounted) return;
      setState(() {
        _state = _SignInState.cancelled;
        _errorMessage = e.message;
      });
    } on SignInFailed catch (e) {
      if (!mounted) return;
      setState(() {
        _state = _SignInState.failed;
        _errorMessage = e.message;
      });
    }
  }

  void _toHome() {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => HomeScreen(
          identity: widget.identity,
          sessionApi: widget.sessionApi,
          voiceApi: widget.voiceApi,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final chooser = widget.identity is PrincipalChooser
        ? widget.identity as PrincipalChooser
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

              // Cancelled state
              if (_state == _SignInState.cancelled) ...[
                Text(
                  'Sign-in was cancelled',
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _signIn,
                  child: const Text('Sign in'),
                ),
              ]
              // Failed state with Try again
              else if (_state == _SignInState.failed) ...[
                Icon(
                  Icons.error_outline,
                  size: 48,
                  color: theme.colorScheme.error,
                ),
                const SizedBox(height: 16),
                Text(
                  _errorMessage ?? 'Sign-in failed',
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: theme.colorScheme.error,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _signIn,
                  child: const Text('Try again'),
                ),
              ]
              // Idle or loading state
              else ...[
                // Loading indicator shown above button during loading
                if (_state == _SignInState.loading) ...[
                  const CircularProgressIndicator(),
                  const SizedBox(height: 16),
                ],
                FilledButton(
                  onPressed: _signIn,
                  child: const Text('Sign in'),
                ),
                if (showChoices && _state == _SignInState.idle) ...[
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
                          onPressed: () => _signInAs(principal),
                          child: Text(principal.displayName),
                        ),
                    ],
                  ),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }
}
