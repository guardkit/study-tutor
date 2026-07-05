import 'package:flutter/material.dart';

import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import 'sign_in_screen.dart';

/// Error surfaces shared by home and session screens. The closed error set
/// (§9 wire set + the client-local TransportError) maps to exactly four
/// treatments:
/// - Unauthenticated → [routeToSignIn]
/// - SessionEnded → the session screen's ended state (handled in place)
/// - SessionForbidden / SessionNotFoundError → [showCantOpenSession]
/// - TransportError → [showConnectionProblem] (phase-2 scope §3.2)

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

/// The fourth treatment (phase-2 scope §3.2): TransportError — the backend
/// was unreachable, timed out, or answered garbage. A dialog for the same
/// reason as [showCantOpenSession] (no auto-dismiss timer to flake tests),
/// but it navigates NOWHERE: the caller's screen and state — including any
/// unsent input — survive, so "try again" is just repeating the action.
Future<void> showConnectionProblem(BuildContext context) async {
  await showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Text('Connection problem'),
      content: const Text(
          "Couldn't reach the tutor. Check your connection and try again."),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(dialogContext).pop(),
          child: const Text('OK'),
        ),
      ],
    ),
  );
}
