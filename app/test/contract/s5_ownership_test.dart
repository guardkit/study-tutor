// Contract §5 — ownership (scope §4 test 6): every verb taking a
// `session_id` rejects a caller whose `student_id` isn't the owner with
// SessionForbidden. Constructed with the second principal (scope §2.2).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';

import 'contract_harness.dart';

void main() {
  late ContractHarness h;
  late String lilymaysSessionId;

  setUp(() async {
    h = ContractHarness();
    // Seed a session owned by Lilymay…
    await h.identity.signIn();
    final started = await h.api.startSession(subject: 'maths');
    lilymaysSessionId = started.sessionId;
    await h.api.turn(lilymaysSessionId, 'hello');
    // …then become the second student.
    await h.identity.signInAs(FakeIdentityProvider.secondStudent);
  });

  test('§5 resume_session on someone else\'s session → SessionForbidden',
      () async {
    await expectLater(h.api.resumeSession(lilymaysSessionId),
        throwsA(isA<SessionForbidden>()));
  });

  test('§5 turn on someone else\'s session → SessionForbidden', () async {
    await expectLater(h.api.turn(lilymaysSessionId, 'let me in'),
        throwsA(isA<SessionForbidden>()));
  });

  test('§5 session_status on someone else\'s session → SessionForbidden',
      () async {
    await expectLater(h.api.sessionStatus(lilymaysSessionId),
        throwsA(isA<SessionForbidden>()));
  });

  test('§5 end_session on someone else\'s session → SessionForbidden',
      () async {
    await expectLater(h.api.endSession(lilymaysSessionId),
        throwsA(isA<SessionForbidden>()));
  });

  test('§3 list_sessions is partitioned by student — the other student\'s '
      'sessions are invisible, not forbidden', () async {
    expect(await h.api.listSessions(), isEmpty);
  });

  test('§5 resume_if_active never matches another student\'s session',
      () async {
    final started =
        await h.api.startSession(subject: 'maths', resumeIfActive: true);
    expect(started.sessionId, isNot(lilymaysSessionId));
    expect(started.resumed, isFalse);
  });
}
