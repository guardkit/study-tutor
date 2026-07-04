// Contract §5 — list_sessions (scope §4 test 9): reflects the status filter
// and shows turn_count / last_activity after activity.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_backend.dart';
import 'fake_contract_backend.dart';

void main() => runListSessionsTests(FakeContractBackend.new);

void runListSessionsTests(ContractBackend Function() newBackend) {
  late ContractBackend b;

  setUp(() async {
    b = newBackend();
    await b.reset();
    await b.signIn();
  });

  test('§5 rows carry the full shape: session_id, subject, topic, status, '
      'started_at, last_activity, turn_count', () async {
    final started =
        await b.api.startSession(subject: 'maths', topic: 'fractions');
    await b.api.turn(started.sessionId, 'hello');

    final rows = await b.api.listSessions();
    expect(rows, hasLength(1));

    final row = rows.single;
    expect(row.sessionId, started.sessionId);
    expect(row.subject, 'maths');
    expect(row.topic, 'fractions');
    expect(row.status, SessionStatus.active);
    expect(row.turnCount, 1);
    expect(row.lastActivity, b.advancedFrom(row.startedAt),
        reason: 'the turn moved last_activity past started_at');
  });

  test('§5 status filter separates active from ended', () async {
    final maths = await b.api.startSession(subject: 'maths');
    final science = await b.api.startSession(subject: 'science');
    await b.api.endSession(science.sessionId);

    final active = await b.api.listSessions(status: SessionStatus.active);
    expect(active.map((r) => r.sessionId), [maths.sessionId]);

    final ended = await b.api.listSessions(status: SessionStatus.ended);
    expect(ended.map((r) => r.sessionId), [science.sessionId]);

    final all = await b.api.listSessions();
    expect(all, hasLength(2));
  });

  test('§5 turn_count and last_activity reflect activity as it happens',
      () async {
    final started = await b.api.startSession(subject: 'maths');

    final before = (await b.api.listSessions()).single;
    expect(before.turnCount, 0);

    await b.api.turn(started.sessionId, 'one');
    await b.api.turn(started.sessionId, 'two');

    final after = (await b.api.listSessions()).single;
    expect(after.turnCount, 2);
    expect(after.lastActivity, b.advancedFrom(before.lastActivity));
  });

  test('§5 limit caps the row count', () async {
    await b.api.startSession(subject: 'maths');
    await b.api.startSession(subject: 'science');
    await b.api.startSession(subject: 'history');

    expect(await b.api.listSessions(limit: 2), hasLength(2));
    expect(await b.api.listSessions(limit: 10), hasLength(3));
  });
}
