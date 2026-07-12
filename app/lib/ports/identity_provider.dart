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

/// Optional capability: a dev/test identity source that can enumerate and
/// select among several principals (the fake has two). This is deliberately a
/// *separate* interface — it does NOT change the [IdentityProvider] shape.
/// Real IdPs (Keycloak) won't implement it, so the SignIn chooser only appears
/// when the composed provider offers it (spec §3: "shows displayName choices
/// if multiple principals exist").
abstract interface class PrincipalChooser {
  /// The principals a dev can sign in as.
  List<Principal> get availablePrincipals;

  /// Sign in as a specific [principal] (must be one of [availablePrincipals]).
  Future<Principal> signInAs(Principal principal);
}
