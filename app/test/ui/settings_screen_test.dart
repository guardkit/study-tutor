// Settings / Profile surface (scope §7) widget tests.
//
// Covers the two behaviours named in the stage:
//   - toggling the Appearance selector updates MaterialApp.themeMode (through
//     the app-wide ThemeController, driven end-to-end via StudyTutorApp);
//   - the Profile Sign out action invokes identity.signOut() and routes to the
//     sign-in screen, clearing the back stack (reusing the shared flow).
//
// Screens are driven against the fakes only (no network, no Keycloak).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/app.dart';
import 'package:study_tutor_app/ui/home_screen.dart';
import 'package:study_tutor_app/ui/settings_screen.dart';
import 'package:study_tutor_app/ui/sign_in_screen.dart';
import 'package:study_tutor_app/ui/theme_controller.dart';

void main() {
  late FakeIdentityProvider identity;
  late FakeSessionApi sessionApi;
  late FakeVoiceApi voiceApi;

  setUp(() {
    identity = FakeIdentityProvider();
    sessionApi = FakeSessionApi(identity: identity);
    voiceApi = FakeVoiceApi();
  });

  ThemeMode currentThemeMode(WidgetTester tester) =>
      tester.widget<MaterialApp>(find.byType(MaterialApp)).themeMode!;

  group('Appearance selector', () {
    testWidgets('selecting Dark updates MaterialApp.themeMode', (tester) async {
      await tester.pumpWidget(StudyTutorApp(
        identity: identity,
        sessionApi: sessionApi,
        voiceApi: voiceApi,
      ));
      await tester.pumpAndSettle();

      // Sign in (default principal) → Home.
      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();
      expect(find.byType(HomeScreen), findsOneWidget);

      // Default follows the platform.
      expect(currentThemeMode(tester), ThemeMode.system);

      // Open the overflow → Settings.
      await tester.tap(find.byType(PopupMenuButton<String>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Settings'));
      await tester.pumpAndSettle();
      expect(find.byType(SettingsScreen), findsOneWidget);

      // Pick Dark on the Appearance selector.
      await tester.tap(find.text('Dark'));
      await tester.pumpAndSettle();
      expect(currentThemeMode(tester), ThemeMode.dark);

      // And Light.
      await tester.tap(find.text('Light'));
      await tester.pumpAndSettle();
      expect(currentThemeMode(tester), ThemeMode.light);
    });
  });

  group('Profile sign out', () {
    Widget makeSettings(ThemeController controller) {
      return MaterialApp(
        home: SettingsScreen(
          identity: identity,
          sessionApi: sessionApi,
          voiceApi: voiceApi,
          themeController: controller,
        ),
      );
    }

    testWidgets('shows the signed-in principal display name', (tester) async {
      await identity.signIn();
      await tester.pumpWidget(makeSettings(ThemeController()));
      await tester.pumpAndSettle();

      expect(find.text('Lilymay'), findsOneWidget);
    });

    testWidgets('Sign out invokes identity.signOut() and routes to sign-in',
        (tester) async {
      await identity.signIn();
      expect(identity.currentPrincipal, isNotNull);

      await tester.pumpWidget(makeSettings(ThemeController()));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(OutlinedButton, 'Sign out'));
      await tester.pumpAndSettle();

      // Identity port sign-out ran.
      expect(identity.currentPrincipal, isNull);
      // Routed to sign-in, back stack cleared.
      expect(find.byType(SignInScreen), findsOneWidget);
      expect(find.byType(SettingsScreen), findsNothing);
      final navigator = tester.state<NavigatorState>(find.byType(Navigator));
      expect(navigator.canPop(), isFalse);
    });
  });
}
