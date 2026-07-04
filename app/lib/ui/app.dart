import 'package:flutter/material.dart';

import 'sign_in_screen.dart';

/// Walking-skeleton app shell: three screens behind Navigator 1.0 pushes,
/// Flutter default theme (scope §7: no theming/branding in v1).
class StudyTutorApp extends StatelessWidget {
  const StudyTutorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      title: 'Study Tutor',
      home: SignInScreen(),
    );
  }
}
