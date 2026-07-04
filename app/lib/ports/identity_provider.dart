/// The `IdentityProvider` port — auth as a port (scope §2.2).
///
/// v1 has one adapter (FakeIdentityProvider); Keycloak arrives later as a
/// second adapter behind this same interface. `signOut` completes the port
/// but gets no v1 UI affordance.
library;

import '../domain/principal.dart';

abstract interface class IdentityProvider {
  /// The signed-in principal, or null when signed out. May hold a stale
  /// (invalidated) token — the backend port is the validity authority (§3).
  Principal? get currentPrincipal;

  Future<Principal> signIn();

  Future<void> signOut();
}
