import 'package:flutter/material.dart';

/// App-level theme-mode controller (Settings surface, scope §7). A small
/// [ChangeNotifier] holding the selected [ThemeMode] so `StudyTutorApp` reads
/// `MaterialApp.themeMode` from it instead of a hardcoded constant, and the
/// Appearance selector on the Settings screen writes to it.
///
/// v1 keeps the choice in-memory only — no storage dependency (path_provider /
/// secure-storage are not enlisted for this): the mode resets to [defaultMode]
/// on a cold start. No provider/riverpod/bloc; the app shell rebuilds off this
/// via `ListenableBuilder` exactly like [ProgressStore].
class ThemeController extends ChangeNotifier {
  ThemeController({ThemeMode initialMode = defaultMode}) : _mode = initialMode;

  /// The default before any user choice — follow the platform (spec §1).
  static const ThemeMode defaultMode = ThemeMode.system;

  ThemeMode _mode;

  /// The current app-wide theme mode.
  ThemeMode get mode => _mode;

  /// Set the app-wide theme mode. A no-op (no notification) when unchanged, so
  /// re-selecting the active option doesn't churn a rebuild.
  void setMode(ThemeMode mode) {
    if (mode == _mode) return;
    _mode = mode;
    notifyListeners();
  }
}
