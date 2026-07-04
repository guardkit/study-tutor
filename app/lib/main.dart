import 'package:flutter/material.dart';

import 'fakes/fake_identity_provider.dart';
import 'fakes/fake_session_api.dart';
import 'ui/app.dart';

// Composition root: the fakes are constructed HERE and only here (scope §2).
// Swapping in the real HTTP/WS + Keycloak adapters later is a change to this
// file, not to the screens.
void main() {
  final identity = FakeIdentityProvider();
  final sessionApi = FakeSessionApi(identity: identity);
  runApp(StudyTutorApp(identity: identity, sessionApi: sessionApi));
}
