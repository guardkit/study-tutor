// Lane 1 step 2 (app leg): the Home subject picker. Visible even with a
// single subject (Rich's call, 2026-08-02); the selection threads into
// startSession and the progress read, with defaultSubject as the fallback
// when no SubjectStore is composed (SUBJECT_DEFAULT.md §4: the default
// becomes the fallback, not a fixed value).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/domain/gamification.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_student_model_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ports/student_model_api.dart';
import 'package:study_tutor_app/ui/app.dart';
import 'package:study_tutor_app/ui/home_screen.dart';
import 'package:study_tutor_app/ui/subject_store.dart';

/// Records every subject fetched, answering like the live backend: the seeded
/// record for English, the zero-state for a subject with nothing banked.
class _RecordingStudentModelApi implements StudentModelApi {
  _RecordingStudentModelApi(this._identity);

  final FakeIdentityProvider _identity;
  final fetched = <String>[];

  @override
  Future<StudentModel> fetch({required String subject}) async {
    if (_identity.currentPrincipal == null) throw const Unauthenticated();
    fetched.add(subject);
    return subject == defaultSubject
        ? FakeStudentModelApi.defaultModel
        : FakeStudentModelApi.zeroState;
  }
}

void main() {
  late FakeIdentityProvider identity;
  late FakeSessionApi sessionApi;
  late FakeVoiceApi voiceApi;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn();
    sessionApi = FakeSessionApi(identity: identity);
    voiceApi = FakeVoiceApi();
  });

  Widget home({SubjectStore? subjectStore}) => MaterialApp(
        home: HomeScreen(
          identity: identity,
          sessionApi: sessionApi,
          voiceApi: voiceApi,
          subjectStore: subjectStore,
        ),
      );

  testWidgets('fallback: no subject store → startSession sends defaultSubject',
      (tester) async {
    await tester.pumpWidget(home());
    await tester.pumpAndSettle();

    expect(find.byType(SegmentedButton<String>), findsNothing,
        reason: 'no composed store — nothing to pick from');

    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    final active = await sessionApi.listSessions(status: SessionStatus.active);
    expect(active.single.subject, defaultSubject,
        reason: 'the seam-test anchor stays the value sent with no selection');

    await tester.pageBack();
    await tester.pumpAndSettle();
  });

  testWidgets('the picker is visible even with a single subject',
      (tester) async {
    await tester.pumpWidget(
        home(subjectStore: SubjectStore(fallback: defaultSubject)));
    await tester.pumpAndSettle();

    final picker = find.byType(SegmentedButton<String>);
    expect(picker, findsOneWidget,
        reason: "Rich's call 2026-08-02: the control shows today, not only "
            'once a second subject lands');
    expect(find.descendant(of: picker, matching: find.text('English')),
        findsOneWidget);
  });

  testWidgets('a picked subject reaches startSession and the session screen',
      (tester) async {
    final store = SubjectStore(
        fallback: defaultSubject, subjects: const ['english', 'french']);
    await tester.pumpWidget(home(subjectStore: store));
    await tester.pumpAndSettle();

    final picker = find.byType(SegmentedButton<String>);
    expect(find.descendant(of: picker, matching: find.text('English')),
        findsOneWidget);
    expect(find.descendant(of: picker, matching: find.text('French')),
        findsOneWidget, reason: 'both offered subjects render as segments');

    await tester.tap(find.text('French'));
    await tester.pump();
    expect(store.selectedSubject, 'french');
    expect(tester.widget<SegmentedButton<String>>(picker).selected, {'french'},
        reason: 'the rendered highlight follows the store, not a hardcoded '
            'default');

    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    final active = await sessionApi.listSessions(status: SessionStatus.active);
    expect(active.single.subject, 'french',
        reason: 'the picked subject is what startSession sends');
    expect(find.widgetWithText(AppBar, 'French'), findsOneWidget,
        reason: 'the pushed session screen is titled by the started subject');

    await tester.pageBack();
    await tester.pumpAndSettle();
  });

  testWidgets(
      'the selection threads through the REAL composition: progress read '
      'and startSession both follow it via the AppScope wiring',
      (tester) async {
    final appIdentity = FakeIdentityProvider();
    final recorder = _RecordingStudentModelApi(appIdentity);
    final shellSessionApi = FakeSessionApi(identity: appIdentity);
    final store = SubjectStore(
        fallback: defaultSubject, subjects: const ['english', 'french']);
    await tester.pumpWidget(StudyTutorApp(
      identity: appIdentity,
      sessionApi: shellSessionApi,
      voiceApi: FakeVoiceApi(),
      studentModelApi: recorder,
      subjectStore: store,
    ));

    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    expect(recorder.fetched, [defaultSubject],
        reason: 'Home loads progress under the fallback subject');

    await tester.tap(find.text('French'));
    await tester.pumpAndSettle();
    expect(recorder.fetched, [defaultSubject, 'french'],
        reason: 'changing the selection refetches under the new subject');

    // Home here resolved its store from the ambient AppScope (no constructor
    // injection) — the shipped composition. Starting now must send the
    // selection, not the fallback.
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    final active =
        await shellSessionApi.listSessions(status: SessionStatus.active);
    expect(active.single.subject, 'french',
        reason: 'the picked subject reaches startSession through the scope '
            'resolution, not only through widget injection');

    await tester.pageBack();
    await tester.pumpAndSettle();
  });
}
