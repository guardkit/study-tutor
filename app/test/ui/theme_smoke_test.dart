// S-A1 design system: Home renders under both ThemeMode.light and
// ThemeMode.dark without error, and the BandColors extension resolves in
// context for each mode. Behaviour is unchanged — this is a re-skin smoke.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/home_screen.dart';
import 'package:study_tutor_app/ui/theme/app_theme.dart';
import 'package:study_tutor_app/ui/theme/band_colors.dart';

void main() {
  Future<BandColors> pumpHome(WidgetTester tester, ThemeMode mode) async {
    final identity = FakeIdentityProvider();
    await identity.signIn();
    late BandColors resolved;
    await tester.pumpWidget(MaterialApp(
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: mode,
      home: Builder(builder: (context) {
        resolved = BandColors.of(context);
        return HomeScreen(
          identity: identity,
          sessionApi: FakeSessionApi(identity: identity),
          voiceApi: FakeVoiceApi(),
        );
      }),
    ));
    await tester.pumpAndSettle();
    return resolved;
  }

  testWidgets('Home renders under ThemeMode.light', (tester) async {
    final bands = await pumpHome(tester, ThemeMode.light);
    expect(find.text('Hi, Lilymay'), findsOneWidget);
    expect(bands.mastered, BandColors.light.mastered);
  });

  testWidgets('Home renders under ThemeMode.dark', (tester) async {
    final bands = await pumpHome(tester, ThemeMode.dark);
    expect(find.text('Hi, Lilymay'), findsOneWidget);
    expect(bands.mastered, BandColors.dark.mastered);
  });
}
