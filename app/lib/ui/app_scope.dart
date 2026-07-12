import 'package:flutter/widgets.dart';

import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/voice_api.dart';

/// Root [InheritedWidget] composing the app's ports (spec §2) so screens read
/// them via `AppScope.of(context)` instead of constructor prop-drilling. The
/// composition root (`main.dart`) still constructs the adapters and passes
/// them here; constructor injection on the screens stays available so widget
/// tests can inject fakes directly without an ambient scope.
///
/// `StudentModelApi` joins this triplet in S-A3 — not composed yet.
class AppScope extends InheritedWidget {
  const AppScope({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.voiceApi,
    required super.child,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final VoiceApi voiceApi;

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
      voiceApi != oldWidget.voiceApi;
}
