// Contract §9 — unknown session + session_status semantics (scope §4
// test 8): unknown `session_id` → SessionNotFoundError; `session_status` is
// the one verb that still answers on an ended session; `resumable` is true
// while active and false once ended.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_backend.dart';
import 'fake_contract_backend.dart';

void main() => runUnknownSessionAndStatusTests(FakeContractBackend.new);

void runUnknownSessionAndStatusTests(ContractBackend Function() newBackend) {
  late ContractBackend b;

  setUp(() async {
    b = newBackend();
    await b.reset();
    await b.signIn();
  });

  test('§9 unknown session_id → SessionNotFoundError on every session_id verb',
      () async {
    final notFound = throwsA(isA<SessionNotFoundError>());
    await expectLater(b.api.resumeSession('s-999'), notFound);
    await expectLater(b.api.turn('s-999', 'hello'), notFound);
    await expectLater(b.api.sessionStatus('s-999'), notFound);
    await expectLater(b.api.endSession('s-999'), notFound);
  });

  test('§5 session_status returns the full shape while active, '
      'resumable: true', () async {
    final started =
        await b.api.startSession(subject: 'maths', topic: 'fractions');
    await b.api.turn(started.sessionId, 'hello');

    final status = await b.api.sessionStatus(started.sessionId);

    expect(status.sessionId, started.sessionId);
    expect(status.studentId, b.defaultStudentId);
    expect(status.status, SessionStatus.active);
    expect(status.turnCount, 1);
    expect(status.resumable, isTrue, reason: '§4: active is resumable');
    expect(status.lastActivity.isBefore(status.startedAt), isFalse,
        reason: 'relative ordering: activity never precedes the start');
  });

  test('§9 session_status alone still answers on an ended session, '
      'resumable: false', () async {
    final started = await b.api.startSession(subject: 'maths');
    await b.api.turn(started.sessionId, 'hello');
    await b.api.endSession(started.sessionId);

    // The other session_id verbs are terminal-locked (§4, proven in
    // s4_lifecycle_test) — session_status answers.
    final status = await b.api.sessionStatus(started.sessionId);

    expect(status.status, SessionStatus.ended);
    expect(status.resumable, isFalse, reason: '§4: ended is terminal');
    expect(status.turnCount, 1,
        reason: 'history is preserved, not erased, by ending');
  });

  test('§4 resumable flips exactly with the active → ended transition',
      () async {
    final started = await b.api.startSession(subject: 'maths');

    expect((await b.api.sessionStatus(started.sessionId)).resumable, isTrue);
    await b.api.endSession(started.sessionId);
    expect((await b.api.sessionStatus(started.sessionId)).resumable, isFalse);
  });
}
