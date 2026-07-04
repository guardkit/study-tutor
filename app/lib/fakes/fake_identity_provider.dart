/// Fake identity adapter (scope §2.2): two principals, an invalidate-token
/// switch, and the token → student_id derivation the fake backend consults.
///
/// Contract §3: `student_id` is derived from the validated token by the
/// backend, never asserted by the client. In the fake world this class plays
/// both roles — the client-side identity port AND the fake auth server's
/// introspection endpoint ([studentIdForToken]) that FakeSessionApi trusts,
/// mirroring how the real backend trusts Keycloak rather than the app.
library;

import '../domain/principal.dart';
import '../ports/identity_provider.dart';

class FakeIdentityProvider implements IdentityProvider {
  /// Default student — the contract §3 interim single-user mode.
  static const lilymay = Principal(token: 'token-lilymay', displayName: 'Lilymay');

  /// Second principal so ownership violations are constructible (scope §2.2).
  static const secondStudent = Principal(token: 'token-alex', displayName: 'Alex');

  /// The fake auth server's token table (token → student_id).
  static const _studentIdByToken = <String, String>{
    'token-lilymay': 'lilymay',
    'token-alex': 'alex',
  };

  Principal? _current;
  final Set<String> _invalidatedTokens = {};

  @override
  Principal? get currentPrincipal => _current;

  /// Signs in the default student (Lilymay). Re-authenticating restores a
  /// previously invalidated token — as with a real IdP, signing in again
  /// yields a valid credential (here the constant token regains validity),
  /// so the Unauthenticated → sign-in → retry loop can actually recover.
  @override
  Future<Principal> signIn() async {
    _invalidatedTokens.remove(lilymay.token);
    _current = lilymay;
    return lilymay;
  }

  @override
  Future<void> signOut() async {
    _current = null;
  }

  /// Test hook: sign in as a specific principal (e.g. [secondStudent] for
  /// ownership tests). Not on the port — the v1 UI only ever [signIn]s.
  Future<Principal> signInAs(Principal principal) async {
    _invalidatedTokens.remove(principal.token);
    _current = principal;
    return principal;
  }

  /// Test hook: the invalidate-token switch (scope §2.2). The client-side
  /// principal stays set — the app still *thinks* it is signed in — but the
  /// backend's next introspection rejects the token, which is exactly the
  /// stale-token shape that makes `Unauthenticated` constructible.
  void invalidateCurrentToken() {
    final token = _current?.token;
    if (token != null) {
      _invalidatedTokens.add(token);
    }
  }

  /// Fake auth-server introspection (§3 derivation): the `student_id` for a
  /// token, or null when the token is unknown or invalidated — the caller
  /// maps null to `Unauthenticated`.
  String? studentIdForToken(String? token) {
    if (token == null || _invalidatedTokens.contains(token)) {
      return null;
    }
    return _studentIdByToken[token];
  }
}
