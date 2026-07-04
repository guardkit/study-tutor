// Contract §5 — ownership (scope §4 test 6): every verb taking a
// `session_id` rejects a caller whose `student_id` isn't the owner with
// SessionForbidden. Constructed with the second principal (scope §2.2 —
// live, the second entry in the dev token table).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';

import 'contract_backend.dart';
import 'fake_contract_backend.dart';

void main() => runOwnershipTests(FakeContractBackend.new);

void runOwnershipTests(ContractBackend Function() newBackend) {
  late ContractBackend b;
  late String lilymaysSessionId;

  setUp(() async {
    b = newBackend();
    await b.reset();
    // Seed a session owned by the default student…
    await b.signIn();
    final started = await b.api.startSession(subject: 'maths');
    lilymaysSessionId = started.sessionId;
    await b.api.turn(lilymaysSessionId, 'hello');
    // …then become the second student.
    await b.signInSecondStudent();
  });

  test('§5 resume_session on someone else\'s session → SessionForbidden',
      () async {
    await expectLater(b.api.resumeSession(lilymaysSessionId),
        throwsA(isA<SessionForbidden>()));
  });

  test('§5 turn on someone else\'s session → SessionForbidden', () async {
    await expectLater(b.api.turn(lilymaysSessionId, 'let me in'),
        throwsA(isA<SessionForbidden>()));
  });

  test('§5 session_status on someone else\'s session → SessionForbidden',
      () async {
    await expectLater(b.api.sessionStatus(lilymaysSessionId),
        throwsA(isA<SessionForbidden>()));
  });

  test('§5 end_session on someone else\'s session → SessionForbidden',
      () async {
    await expectLater(b.api.endSession(lilymaysSessionId),
        throwsA(isA<SessionForbidden>()));
  });

  test('§3 list_sessions is partitioned by student — the other student\'s '
      'sessions are invisible, not forbidden', () async {
    expect(await b.api.listSessions(), isEmpty);
  });

  test('§5 resume_if_active never matches another student\'s session',
      () async {
    final started =
        await b.api.startSession(subject: 'maths', resumeIfActive: true);
    expect(started.sessionId, isNot(lilymaysSessionId));
    expect(started.resumed, isFalse);
  });
}
