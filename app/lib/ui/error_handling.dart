import 'package:flutter/material.dart';

import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import 'sign_in_screen.dart';

/// Scope §3 error surfaces, shared by home and session screens. The closed
/// §9 error set maps to exactly three treatments:
/// - Unauthenticated → [routeToSignIn]
/// - SessionEnded → the session screen's ended state (handled in place)
/// - SessionForbidden / SessionNotFoundError → [showCantOpenSession]

/// Clear the whole stack and land on sign-in.
void routeToSignIn(
  BuildContext context,
  IdentityProvider identity,
  SessionApi sessionApi,
) {
  Navigator.of(context).pushAndRemoveUntil(
    MaterialPageRoute<void>(
      builder: (_) =>
          SignInScreen(identity: identity, sessionApi: sessionApi),
    ),
    (route) => false,
  );
}

/// The one shared, non-crashing surface for SessionForbidden and
/// SessionNotFoundError — a dialog (deterministic in tests: no auto-dismiss
/// timer), then back to home.
Future<void> showCantOpenSession(BuildContext context) async {
  await showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Text("Can't open this session"),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(dialogContext).pop(),
          child: const Text('OK'),
        ),
      ],
    ),
  );
  if (context.mounted) {
    Navigator.of(context).popUntil((route) => route.isFirst);
  }
}
