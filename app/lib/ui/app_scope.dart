import 'package:flutter/widgets.dart';

import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/student_model_api.dart';
import '../ports/voice_api.dart';
import 'progress_store.dart';
import 'subject_store.dart';
import 'theme_controller.dart';

/// Root [InheritedWidget] composing the app's ports (spec §2) so screens read
/// them via `AppScope.of(context)` instead of constructor prop-drilling. The
/// composition root (`main.dart`) still constructs the adapters and passes
/// them here; constructor injection on the screens stays available so widget
/// tests can inject fakes directly without an ambient scope.
///
/// S-A3 adds the `StudentModelApi` port and the app-wide [ProgressStore]
/// (owning the student-model snapshot) to the scope. The Settings surface adds
/// the app-wide [ThemeController] (theme-mode selection) alongside them.
/// Lane 1 step 2 adds the app-wide [SubjectStore] (the selected tutoring
/// subject, `defaultSubject` as fallback).
class AppScope extends InheritedWidget {
  const AppScope({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.voiceApi,
    required this.studentModelApi,
    required this.progressStore,
    required this.subjectStore,
    required this.themeController,
    required super.child,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final VoiceApi voiceApi;
  final StudentModelApi studentModelApi;
  final ProgressStore progressStore;
  final SubjectStore subjectStore;
  final ThemeController themeController;

  /// The nearest enclosing scope. Throws if none is present — screens that
  /// opt into scope reading must live under an [AppScope].
  static AppScope of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'No AppScope found in context');
    return scope!;
  }

  /// The nearest enclosing scope, or null when a screen was constructed with
  /// injected ports outside any scope (widget tests).
  static AppScope? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<AppScope>();

  @override
  bool updateShouldNotify(AppScope oldWidget) =>
      identity != oldWidget.identity ||
      sessionApi != oldWidget.sessionApi ||
      voiceApi != oldWidget.voiceApi ||
      studentModelApi != oldWidget.studentModelApi ||
      progressStore != oldWidget.progressStore ||
      subjectStore != oldWidget.subjectStore ||
      themeController != oldWidget.themeController;
}
