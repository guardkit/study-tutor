import 'package:flutter/material.dart';

import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import 'sign_in_screen.dart';

/// App shell: three screens behind Navigator 1.0 pushes, ports injected via
/// constructors (composition root is main.dart), Flutter default theme
/// (scope §7: no theming/branding in v1).
class StudyTutorApp extends StatelessWidget {
  const StudyTutorApp({
    super.key,
    required this.identity,
    required this.sessionApi,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Study Tutor',
      home: SignInScreen(identity: identity, sessionApi: sessionApi),
    );
  }
}
