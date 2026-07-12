// S-A3 §6.1 / §6.3: the Home progress header card (populated + warm zero-state)
// and the Progress screen (level, streak, band-coloured mastery grid resolving
// the BandColors tokens in light and dark, near-unlocks, recent achievements).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_student_model_api.dart';
import 'package:study_tutor_app/ui/gamification/progress_header_card.dart';
import 'package:study_tutor_app/ui/gamification/progress_screen.dart';
import 'package:study_tutor_app/ui/progress_store.dart';
import 'package:study_tutor_app/ui/theme/app_theme.dart';
import 'package:study_tutor_app/ui/theme/band_colors.dart';

void main() {
  Widget wrap(Widget child, {ThemeMode mode = ThemeMode.light}) => MaterialApp(
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        themeMode: mode,
        home: Scaffold(body: child),
      );

  group('ProgressHeaderCard (§6.1)', () {
    testWidgets('populated: level, this-week XP, streak, progress bar',
        (tester) async {
      await tester.pumpWidget(wrap(ProgressHeaderCard(
        model: FakeStudentModelApi.defaultModel,
        aliveToday: false,
        onTap: () {},
      )));

      expect(find.textContaining('Learner'), findsOneWidget);
      expect(find.text('240 XP this week'), findsOneWidget);
      expect(find.byType(LinearProgressIndicator), findsOneWidget);
      // Yesterday-anchored (not alive today) shows the warm nudge, not shaming.
      expect(find.text('ends tonight'), findsOneWidget);
    });

    testWidgets('data_available:false → warm zero-state, never hidden',
        (tester) async {
      var tapped = false;
      await tester.pumpWidget(wrap(ProgressHeaderCard(
        model: FakeStudentModelApi.zeroState,
        aliveToday: false,
        onTap: () => tapped = true,
      )));

      expect(find.textContaining('Finish your first session'), findsOneWidget);
      expect(find.byType(LinearProgressIndicator), findsNothing);

      await tester.tap(find.byType(ProgressHeaderCard));
      expect(tapped, isTrue);
    });

    testWidgets('null snapshot (still loading) also renders the zero-state',
        (tester) async {
      await tester.pumpWidget(wrap(ProgressHeaderCard(
        model: null,
        aliveToday: false,
        onTap: () {},
      )));
      expect(find.textContaining('Finish your first session'), findsOneWidget);
    });
  });

  group('ProgressScreen (§6.3)', () {
    // A tall surface so every section (down to Recent achievements) lays into
    // the element tree without scrolling — the ListView only builds what its
    // viewport reaches.
    setUp(() {
      final view = TestWidgetsFlutterBinding.instance.platformDispatcher
          .implicitView!;
      view.physicalSize = const Size(800, 2000);
      view.devicePixelRatio = 1.0;
    });
    tearDown(() {
      final view = TestWidgetsFlutterBinding.instance.platformDispatcher
          .implicitView!;
      view.resetPhysicalSize();
      view.resetDevicePixelRatio();
    });

    Future<ProgressStore> loadedStore() async {
      final identity = FakeIdentityProvider();
      await identity.signIn();
      final store = ProgressStore(
        api: FakeStudentModelApi(identity: identity),
        subject: 'english',
      );
      await store.load();
      return store;
    }

    testWidgets('band-coloured mastery grid uses the design §6.1 labels',
        (tester) async {
      final store = await loadedStore();
      await tester.pumpWidget(wrap(ProgressScreen(store: store)));
      await tester.pumpAndSettle();

      // macbeth 0.7 → Secure; poetry 0.55 → Developing; jekyll 0.35 → Struggling.
      expect(find.text('Secure'), findsOneWidget);
      expect(find.text('Developing'), findsOneWidget);
      expect(find.text('Struggling'), findsOneWidget);
      expect(find.textContaining('Learner'), findsWidgets);
      expect(find.text('Almost there'), findsOneWidget);
      expect(find.text('Morning Star'), findsOneWidget);
      expect(find.text('Three Day Run'), findsOneWidget);
    });

    testWidgets('the mastery grid resolves BandColors in dark mode too',
        (tester) async {
      final store = await loadedStore();
      late BandColors resolved;
      await tester.pumpWidget(wrap(
        Builder(builder: (context) {
          resolved = BandColors.of(context);
          return ProgressScreen(store: store);
        }),
        mode: ThemeMode.dark,
      ));
      await tester.pumpAndSettle();

      expect(resolved.secure, BandColors.dark.secure);
      expect(find.text('Secure'), findsOneWidget);
    });

    testWidgets('"how bands work" info sheet opens', (tester) async {
      final store = await loadedStore();
      await tester.pumpWidget(wrap(ProgressScreen(store: store)));
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.info_outline));
      await tester.pumpAndSettle();

      expect(find.text('How bands work'), findsOneWidget);
      expect(find.text('needs more work'), findsOneWidget); // design §6.1 phrasing
    });
  });
}
