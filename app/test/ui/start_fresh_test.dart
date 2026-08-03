// Lilymay's 2026-08-03 "switched to Macbeth" defect — Rich's product ruling
// (full app fix): a start while a session is active for the SAME subject must
// never silently resume it. The card discloses the planner-pinned topic
// ("Continue: <topic>"), and the start-fresh sheet captures the learner's own
// topic (chips from her known topics + free text) before end+start with the
// override. Both verbs already exist; no contract change.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_student_model_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/home_screen.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/ports/session_api.dart';
import 'package:study_tutor_app/ui/progress_store.dart';
import 'package:study_tutor_app/ui/session_screen.dart';
import 'package:study_tutor_app/ui/subject_store.dart';

/// Fake whose NEXT startSession dies on the wire — the review's
/// end-lands-start-throws partial-failure window.
class StartFlakySessionApi extends FakeSessionApi {
  StartFlakySessionApi({required super.identity});

  bool failNextStart = false;

  @override
  Future<StartSessionResult> startSession({
    String? subject,
    String? topic,
    bool resumeIfActive = false,
  }) {
    if (failNextStart) {
      failNextStart = false;
      throw const TransportError();
    }
    return super.startSession(
      subject: subject,
      topic: topic,
      resumeIfActive: resumeIfActive,
    );
  }
}

void main() {
  late FakeIdentityProvider identity;
  late FakeSessionApi sessionApi;
  late FakeVoiceApi voiceApi;
  late ProgressStore store;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn();
    sessionApi = FakeSessionApi(identity: identity);
    voiceApi = FakeVoiceApi();
    store = ProgressStore(
      api: FakeStudentModelApi(identity: identity),
      subject: 'english',
    );
  });

  Widget home() => MaterialApp(
        home: HomeScreen(
          identity: identity,
          sessionApi: sessionApi,
          voiceApi: voiceApi,
          progressStore: store,
        ),
      );

  Future<void> seedActive({String topic = 'macbeth'}) async {
    await sessionApi.startSession(subject: 'english', topic: topic);
  }

  Future<List<SessionSummary>> actives() =>
      sessionApi.listSessions(status: SessionStatus.active);

  testWidgets('the session card discloses the planner-pinned topic',
      (tester) async {
    await seedActive(topic: 'macbeth');
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();

    expect(find.text('Continue: Macbeth'), findsOneWidget,
        reason: 'never a silent resume — the card says what the session '
            'is ABOUT, not just its subject');
  });

  testWidgets('start with an active same-subject session opens the sheet '
      'instead of silently resuming', (tester) async {
    await seedActive();
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    expect(find.text('You already have a session going'), findsOneWidget);
    expect(find.byType(SessionScreen), findsNothing,
        reason: 'no session was opened before the learner chose');
    expect(await actives(), hasLength(1),
        reason: 'nothing was started or ended before the choice');
  });

  testWidgets('sheet Continue resumes the active session', (tester) async {
    final started =
        await sessionApi.startSession(subject: 'english', topic: 'macbeth');
    await sessionApi.turn(started.sessionId, 'first question');

    await tester.pumpWidget(home());
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'Continue: Macbeth'));
    await tester.pumpAndSettle();

    expect(find.byType(SessionScreen), findsOneWidget);
    expect(find.text('first question'), findsOneWidget,
        reason: 'Continue is a RESUME — the transcript is intact');
    expect(await actives(), hasLength(1));

    await tester.pageBack();
    await tester.pumpAndSettle();
  });

  testWidgets('a chip names the topic; start-fresh ends the old session and '
      'starts with the override', (tester) async {
    await seedActive(topic: 'macbeth');
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    // Chips come from her own topic_confidence keys.
    await tester.tap(find.widgetWithText(ActionChip, 'Poetry'));
    await tester.pumpAndSettle();
    await tester.tap(
      find.widgetWithText(FilledButton, 'End it and start fresh on Poetry'),
    );
    await tester.pumpAndSettle();

    expect(find.byType(SessionScreen), findsOneWidget);
    final active = await actives();
    expect(active.single.topic, 'poetry',
        reason: "the learner's topic override reaches start_session");

    await tester.pageBack();
    await tester.pumpAndSettle();
  });

  testWidgets('start-fresh yields a genuinely NEW session id', (tester) async {
    final seeded =
        await sessionApi.startSession(subject: 'english', topic: 'macbeth');
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    await tester
        .tap(find.widgetWithText(FilledButton, 'End it and start fresh'));
    await tester.pumpAndSettle();

    final active = await actives();
    expect(active.single.sessionId, isNot(seeded.sessionId),
        reason: 'the old id was captured — not a guessed literal');

    await tester.pageBack();
    await tester.pumpAndSettle();
  });

  testWidgets('free text names a topic she has never studied', (tester) async {
    await seedActive(topic: 'macbeth');
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    await tester.enterText(
        find.widgetWithText(TextField, 'Topic'), 'an inspector calls');
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('start fresh on An Inspector Calls'));
    await tester.pumpAndSettle();

    final active = await actives();
    expect(active.single.topic, 'an inspector calls',
        reason: 'exactly the defect scenario: her intended text wins');

    await tester.pageBack();
    await tester.pumpAndSettle();
  });

  testWidgets('start-fresh with no topic lets the planner pick',
      (tester) async {
    await seedActive(topic: 'macbeth');
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    await tester
        .tap(find.widgetWithText(FilledButton, 'End it and start fresh'));
    await tester.pumpAndSettle();

    final active = await actives();
    expect(active.single.topic, isNull,
        reason: 'no override — the planner picks, but EXPLICITLY fresh');

    await tester.pageBack();
    await tester.pumpAndSettle();
  });

  testWidgets('the gate uses SERVER truth: a session started elsewhere '
      'after Home last refreshed still raises the sheet', (tester) async {
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();
    // The robot / another device starts a session AFTER Home's refresh —
    // the in-memory list is now stale (the review's silent-bypass finding).
    await seedActive(topic: 'macbeth');

    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    expect(find.text('You already have a session going'), findsOneWidget,
        reason: 'gating on the cached list would have silently one-tapped '
            'into a second session');
    expect(await actives(), hasLength(1));
  });

  testWidgets('an active session for a DIFFERENT subject does not raise '
      'the sheet — one-tap start on the picker-selected subject',
      (tester) async {
    await seedActive(topic: 'macbeth'); // english
    final subjects = SubjectStore(
      fallback: defaultSubject,
      subjects: const ['english', 'french'],
    );
    await tester.pumpWidget(MaterialApp(
      home: HomeScreen(
        identity: identity,
        sessionApi: sessionApi,
        voiceApi: voiceApi,
        progressStore: store,
        subjectStore: subjects,
      ),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.text('French'));
    await tester.pump();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    expect(find.text('You already have a session going'), findsNothing,
        reason: 'the english session does not collide with a french start');
    expect(find.byType(SessionScreen), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();
  });

  testWidgets('dismissing the sheet changes nothing — no start, no end',
      (tester) async {
    final seeded =
        await sessionApi.startSession(subject: 'english', topic: 'macbeth');
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    // Tap the barrier above the sheet.
    await tester.tapAt(const Offset(20, 60));
    await tester.pumpAndSettle();

    expect(find.byType(SessionScreen), findsNothing);
    final active = await actives();
    expect(active.single.sessionId, seeded.sessionId,
        reason: 'her session is untouched — dismissal is a free action');
  });

  testWidgets('end lands but the start dies on the wire: the dead session '
      'is never re-offered as Continue', (tester) async {
    final flaky = StartFlakySessionApi(identity: identity);
    await flaky.startSession(subject: 'english', topic: 'macbeth');
    await tester.pumpWidget(MaterialApp(
      home: HomeScreen(
        identity: identity,
        sessionApi: flaky,
        voiceApi: voiceApi,
        progressStore: store,
      ),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    flaky.failNextStart = true;
    await tester
        .tap(find.widgetWithText(FilledButton, 'End it and start fresh'));
    await tester.pumpAndSettle();

    // Connection dialog surfaced; dismiss it.
    await tester.tap(find.widgetWithText(TextButton, 'OK'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Continue: Macbeth'), findsNothing,
        reason: 'the ended session must not linger as a "Continue" card '
            '(review: end-landed/start-failed stale disclosure)');
    expect(await flaky.listSessions(status: SessionStatus.active), isEmpty);
  });

  testWidgets('the active session having ended elsewhere does not discard '
      "the learner's typed topic — fresh start proceeds", (tester) async {
    final seeded =
        await sessionApi.startSession(subject: 'english', topic: 'macbeth');
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    // Another device ends it while the sheet is open.
    await sessionApi.endSession(seeded.sessionId);

    await tester.enterText(
        find.widgetWithText(TextField, 'Topic'), 'an inspector calls');
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('start fresh on An Inspector Calls'));
    await tester.pumpAndSettle();

    final active = await actives();
    expect(active.single.topic, 'an inspector calls',
        reason: 'her intent survives the already-ended race');
    expect(find.byType(SessionScreen), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();
  });

  testWidgets('no active session → one-tap start, no sheet', (tester) async {
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    expect(find.text('You already have a session going'), findsNothing);
    expect(find.byType(SessionScreen), findsOneWidget,
        reason: 'the warm one-tap start is preserved when nothing collides');

    await tester.pageBack();
    await tester.pumpAndSettle();
  });
}
