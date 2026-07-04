// Contract §9 — unknown session + session_status semantics (scope §4
// test 8): unknown `session_id` → SessionNotFoundError; `session_status` is
// the one verb that still answers on an ended session; `resumable` is true
// while active and false once ended.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_harness.dart';

void main() {
  late ContractHarness h;

  setUp(() async {
    h = ContractHarness();
    await h.identity.signIn();
  });

  test('§9 unknown session_id → SessionNotFoundError on every session_id verb',
      () async {
    final notFound = throwsA(isA<SessionNotFoundError>());
    await expectLater(h.api.resumeSession('s-999'), notFound);
    await expectLater(h.api.turn('s-999', 'hello'), notFound);
    await expectLater(h.api.sessionStatus('s-999'), notFound);
    await expectLater(h.api.endSession('s-999'), notFound);
  });

  test('§5 session_status returns the full shape while active, '
      'resumable: true', () async {
    final started = await h.api.startSession(subject: 'maths', topic: 'fractions');
    await h.api.turn(started.sessionId, 'hello');

    final status = await h.api.sessionStatus(started.sessionId);

    expect(status.sessionId, started.sessionId);
    expect(status.studentId, 'lilymay');
    expect(status.status, SessionStatus.active);
    expect(status.turnCount, 1);
    expect(status.resumable, isTrue, reason: '§4: active is resumable');
    expect(status.lastActivity.isBefore(status.startedAt), isFalse);
  });

  test('§9 session_status alone still answers on an ended session, '
      'resumable: false', () async {
    final started = await h.api.startSession(subject: 'maths');
    await h.api.turn(started.sessionId, 'hello');
    await h.api.endSession(started.sessionId);

    // The other session_id verbs are terminal-locked (§4, proven in
    // s4_lifecycle_test) — session_status answers.
    final status = await h.api.sessionStatus(started.sessionId);

    expect(status.status, SessionStatus.ended);
    expect(status.resumable, isFalse, reason: '§4: ended is terminal');
    expect(status.turnCount, 1,
        reason: 'history is preserved, not erased, by ending');
  });

  test('§4 resumable flips exactly with the active → ended transition',
      () async {
    final started = await h.api.startSession(subject: 'maths');

    expect((await h.api.sessionStatus(started.sessionId)).resumable, isTrue);
    await h.api.endSession(started.sessionId);
    expect((await h.api.sessionStatus(started.sessionId)).resumable, isFalse);
  });
}
