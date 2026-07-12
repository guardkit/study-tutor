import 'package:flutter/material.dart';

import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/voice_api.dart';
import 'app_scope.dart';
import 'sign_in_screen.dart';
import 'theme/app_theme.dart';

/// App shell: three screens behind Navigator 1.0 pushes. The composition root
/// (main.dart) injects the ports; they are exposed to the tree via [AppScope]
/// (spec §2) while constructor injection stays available for widget tests.
/// Theming is the "warm academic" system (spec §1) — light+dark `fromSeed`
/// schemes following the platform (`ThemeMode.system`).
class StudyTutorApp extends StatelessWidget {
  const StudyTutorApp({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.voiceApi,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final VoiceApi voiceApi;

  @override
  Widget build(BuildContext context) {
    return AppScope(
      identity: identity,
      sessionApi: sessionApi,
      voiceApi: voiceApi,
      child: MaterialApp(
        title: 'Study Tutor',
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        themeMode: ThemeMode.system,
        home: SignInScreen(
          identity: identity,
          sessionApi: sessionApi,
          voiceApi: voiceApi,
        ),
      ),
    );
  }
}
