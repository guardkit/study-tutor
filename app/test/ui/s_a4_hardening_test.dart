// S-A4 hardening tests: accessibility semantics labels on every new gamification
// / voice component, and text-scale (1.3×) resilience — the Home header card and
// the session-end celebration sheet must lay out without overflow at large text
// scales. Semantics tests assert the composed screen-reader phrasing; text-scale
// tests assert no RenderFlex overflow exception is thrown.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/gamification.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_student_model_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/gamification/celebration_sheet.dart';
import 'package:study_tutor_app/ui/gamification/progress_header_card.dart';
import 'package:study_tutor_app/ui/gamification/progress_screen.dart';
import 'package:study_tutor_app/ui/gamification/streak_badge.dart';
import 'package:study_tutor_app/ui/progress_store.dart';
import 'package:study_tutor_app/ui/session_screen.dart';
import 'package:study_tutor_app/ui/theme/app_theme.dart';

const _fullBlock = SessionGamification(
  xpAwarded: 120,
  totalXp: 170,
  levelNumber: 2,
  levelName: 'Novice',
  levelUp: true,
  achievementsUnlocked: [
    UnlockedAchievement(id: 'first_steps', name: 'First Steps', xp: 50),
  ],
  streakDays: 3,
  streakExtended: true,
);

Widget _wrap(Widget child, {ThemeMode mode = ThemeMode.light}) => MaterialApp(
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: mode,
      home: Scaffold(body: child),
    );

/// A MaterialApp whose entire route stack (including modal bottom sheets, which
/// live in the app overlay) renders at [scale]× text.
Widget _scaledApp(Widget home, double scale) => MaterialApp(
      theme: AppTheme.light(),
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context)
            .copyWith(textScaler: TextScaler.linear(scale)),
        child: child!,
      ),
      home: home,
    );

Widget _sheetHost(SessionGamification block) => Builder(
      builder: (context) => Scaffold(
        body: Center(
          child: FilledButton(
            onPressed: () => showCelebrationSheet(context, block),
            child: const Text('open'),
          ),
        ),
      ),
    );

Future<ProgressStore> _loadedStore() async {
  final identity = FakeIdentityProvider();
  await identity.signIn();
  final store = ProgressStore(
    api: FakeStudentModelApi(identity: identity),
    subject: 'english',
  );
  await store.load();
  return store;
}

void main() {
  group('a11y semantics — gamification surfaces', () {
    testWidgets('StreakBadge exposes warm, non-shaming streak labels',
        (tester) async {
      final handle = tester.ensureSemantics();

      await tester.pumpWidget(
        _wrap(const StreakBadge(streakDays: 6, aliveToday: false)),
      );
      expect(find.bySemanticsLabel('6 day streak, ends tonight'),
          findsOneWidget);

      await tester.pumpWidget(
        _wrap(const StreakBadge(streakDays: 0, aliveToday: false)),
      );
      expect(find.bySemanticsLabel('No streak yet'), findsOneWidget);

      handle.dispose();
    });

    testWidgets('ProgressHeaderCard reads as one button with a composite label',
        (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(_wrap(ProgressHeaderCard(
        model: FakeStudentModelApi.defaultModel,
        aliveToday: false,
        onTap: () {},
      )));

      expect(
        find.bySemanticsLabel('Your progress. Level 5, Learner. '
            '240 XP this week. 6 day streak, ends tonight.'),
        findsOneWidget,
      );
      handle.dispose();
    });

    testWidgets('ProgressHeaderCard zero-state has a warm semantic label',
        (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(_wrap(ProgressHeaderCard(
        model: FakeStudentModelApi.zeroState,
        aliveToday: false,
        onTap: () {},
      )));

      expect(
        find.bySemanticsLabel('Your progress. Finish your first session to '
            'earn XP and start a streak.'),
        findsOneWidget,
      );
      handle.dispose();
    });

    testWidgets('Progress screen cells expose mastery / near / recent labels',
        (tester) async {
      // A tall surface so every ListView section lays into the tree (and thus
      // the semantics tree) without scrolling.
      final view =
          TestWidgetsFlutterBinding.instance.platformDispatcher.implicitView!;
      view.physicalSize = const Size(800, 2000);
      view.devicePixelRatio = 1.0;
      addTearDown(() {
        view.resetPhysicalSize();
        view.resetDevicePixelRatio();
      });

      final handle = tester.ensureSemantics();
      final store = await _loadedStore();
      await tester.pumpWidget(_wrap(ProgressScreen(store: store)));
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel('Macbeth: Secure, feeling confident'),
          findsOneWidget);
      expect(
        find.bySemanticsLabel('Almost there: Morning Star. '
            'One more early-morning session (4/5).'),
        findsOneWidget,
      );
      expect(find.bySemanticsLabel(RegExp(r'Three Day Run,.*plus 100 XP')),
          findsOneWidget);
      handle.dispose();
    });

    testWidgets('Celebration sheet elements carry semantics labels',
        (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(_wrap(_sheetHost(_fullBlock)));
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel('120 XP earned this session'),
          findsOneWidget);
      expect(find.bySemanticsLabel('3 day streak, kept alive'), findsOneWidget);
      expect(
        find.bySemanticsLabel('Level up! You reached Level 2, Novice'),
        findsOneWidget,
      );
      expect(
        find.bySemanticsLabel('Achievement unlocked: First Steps, plus 50 XP'),
        findsOneWidget,
      );
      handle.dispose();
    });
  });

  group('a11y semantics — session voice states', () {
    Future<(FakeSessionApi, String)> startedSession() async {
      final identity = FakeIdentityProvider();
      await identity.signIn();
      final api = FakeSessionApi(identity: identity);
      final started = await api.startSession(subject: 'english');
      return (api, started.sessionId);
    }

    testWidgets('idle mic exposes "Record a question"', (tester) async {
      final handle = tester.ensureSemantics();
      final (api, sessionId) = await startedSession();
      final identity = FakeIdentityProvider();
      await identity.signIn();

      await tester.pumpWidget(_wrap(SessionScreen(
        identity: identity,
        sessionApi: api,
        voiceApi: FakeVoiceApi(),
        sessionId: sessionId,
        voiceRecorder: FakeVoiceRecorder(),
      )));

      expect(find.bySemanticsLabel('Record a question'), findsOneWidget);
      handle.dispose();
    });

    testWidgets('mic flips to "Stop recording" + a recording label once armed',
        (tester) async {
      final handle = tester.ensureSemantics();
      final (api, sessionId) = await startedSession();
      final identity = FakeIdentityProvider();
      await identity.signIn();

      await tester.pumpWidget(_wrap(SessionScreen(
        identity: identity,
        sessionApi: api,
        voiceApi: FakeVoiceApi(),
        sessionId: sessionId,
        voiceRecorder: FakeVoiceRecorder(),
      )));

      await tester.tap(find.bySemanticsLabel('Record a question'));
      await tester.pump(); // let recorder.start() resolve + UI arm
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.bySemanticsLabel('Stop recording'), findsOneWidget);
      expect(find.bySemanticsLabel(RegExp(r'Recording, \d+s')), findsOneWidget);

      // Dispose the screen so its recording ticker/pulse don't leak past the
      // test (they cancel on unmount).
      await tester.pumpWidget(const SizedBox());
      handle.dispose();
    });
  });

  group('text-scale 1.3× resilience', () {
    testWidgets('ProgressHeaderCard lays out at 1.3× without overflow',
        (tester) async {
      final view =
          TestWidgetsFlutterBinding.instance.platformDispatcher.implicitView!;
      view.physicalSize = const Size(360, 640);
      view.devicePixelRatio = 1.0;
      addTearDown(() {
        view.resetPhysicalSize();
        view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(_scaledApp(
        Scaffold(
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              ProgressHeaderCard(
                model: FakeStudentModelApi.defaultModel,
                aliveToday: false,
                onTap: () {},
              ),
            ],
          ),
        ),
        1.3,
      ));
      await tester.pump();

      expect(tester.takeException(), isNull);
      expect(find.byType(ProgressHeaderCard), findsOneWidget);
    });

    testWidgets('Celebration sheet (full block) scrolls, no overflow at 1.3×',
        (tester) async {
      final view =
          TestWidgetsFlutterBinding.instance.platformDispatcher.implicitView!;
      view.physicalSize = const Size(360, 640);
      view.devicePixelRatio = 1.0;
      addTearDown(() {
        view.resetPhysicalSize();
        view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(_scaledApp(_sheetHost(_fullBlock), 1.3));
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      // Content rendered; the dismiss button exists even if below the fold.
      expect(find.byKey(const Key('celebration-xp')), findsOneWidget);
      expect(find.text('Nice work'), findsOneWidget);
    });
  });
}
