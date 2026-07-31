import 'package:flutter/material.dart';

import '../fakes/fake_student_model_api.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/student_model_api.dart';
import '../ports/voice_api.dart';
import 'app_scope.dart';
import 'home_screen.dart';
import 'progress_store.dart';
import 'sign_in_screen.dart';
import 'theme/app_theme.dart';
import 'theme_controller.dart';

/// App shell: the screens behind Navigator 1.0 pushes. The composition root
/// (main.dart) injects the ports; they are exposed to the tree via [AppScope]
/// (spec §2) while constructor injection stays available for widget tests.
/// Theming is the "warm academic" system (spec §1) — light+dark `fromSeed`
/// schemes following the platform (`ThemeMode.system`).
///
/// S-A3: [studentModelApi] and [progressStore] are optional — a test that
/// pumps `StudyTutorApp` with only the three v1 ports gets a default fake
/// student-model read and a store over it, so pre-S-A3 widget tests compile
/// and run unchanged. [themeController] is optional the same way: absent, the
/// shell creates one defaulting to [ThemeMode.system] (the prior hardcoded
/// behaviour), so pre-Settings tests are unaffected.
class StudyTutorApp extends StatefulWidget {
  const StudyTutorApp({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.voiceApi,
    this.studentModelApi,
    this.progressStore,
    this.themeController,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final VoiceApi voiceApi;
  final StudentModelApi? studentModelApi;
  final ProgressStore? progressStore;
  final ThemeController? themeController;

  @override
  State<StudyTutorApp> createState() => _StudyTutorAppState();
}

class _StudyTutorAppState extends State<StudyTutorApp> {
  late final StudentModelApi _studentModelApi =
      widget.studentModelApi ?? FakeStudentModelApi(identity: widget.identity);
  late final ProgressStore _progressStore = widget.progressStore ??
      ProgressStore(api: _studentModelApi, subject: defaultSubject);
  late final ThemeController _themeController =
      widget.themeController ?? ThemeController();

  @override
  void dispose() {
    // Only dispose objects we created; injected ones are owned by the caller.
    if (widget.progressStore == null) _progressStore.dispose();
    if (widget.themeController == null) _themeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScope(
      identity: widget.identity,
      sessionApi: widget.sessionApi,
      voiceApi: widget.voiceApi,
      studentModelApi: _studentModelApi,
      progressStore: _progressStore,
      themeController: _themeController,
      // The shell rebuilds when the theme mode changes so `MaterialApp`
      // re-reads `themeMode` from the controller (spec §7 Settings surface).
      child: ListenableBuilder(
        listenable: _themeController,
        builder: (context, _) => MaterialApp(
          title: 'Study Tutor',
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          themeMode: _themeController.mode,
          home: SignInScreen(
            identity: widget.identity,
            sessionApi: widget.sessionApi,
            voiceApi: widget.voiceApi,
          ),
        ),
      ),
    );
  }
}
