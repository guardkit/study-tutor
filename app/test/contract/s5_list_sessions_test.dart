// Contract §5 — list_sessions (scope §4 test 9): reflects the status filter
// and shows turn_count / last_activity after activity.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_harness.dart';

void main() {
  late ContractHarness h;

  setUp(() async {
    h = ContractHarness();
    await h.identity.signIn();
  });

  test('§5 rows carry the full shape: session_id, subject, topic, status, '
      'started_at, last_activity, turn_count', () async {
    final started =
        await h.api.startSession(subject: 'maths', topic: 'fractions');
    await h.api.turn(started.sessionId, 'hello');

    final rows = await h.api.listSessions();
    expect(rows, hasLength(1));

    final row = rows.single;
    expect(row.sessionId, started.sessionId);
    expect(row.subject, 'maths');
    expect(row.topic, 'fractions');
    expect(row.status, SessionStatus.active);
    expect(row.turnCount, 1);
    expect(row.lastActivity.isAfter(row.startedAt), isTrue,
        reason: 'the turn moved last_activity past started_at');
  });

  test('§5 status filter separates active from ended', () async {
    final a = await h.api.startSession(subject: 'maths');
    final b = await h.api.startSession(subject: 'science');
    await h.api.endSession(b.sessionId);

    final active = await h.api.listSessions(status: SessionStatus.active);
    expect(active.map((r) => r.sessionId), [a.sessionId]);

    final ended = await h.api.listSessions(status: SessionStatus.ended);
    expect(ended.map((r) => r.sessionId), [b.sessionId]);

    final all = await h.api.listSessions();
    expect(all, hasLength(2));
  });

  test('§5 turn_count and last_activity reflect activity as it happens',
      () async {
    final started = await h.api.startSession(subject: 'maths');

    final before = (await h.api.listSessions()).single;
    expect(before.turnCount, 0);

    await h.api.turn(started.sessionId, 'one');
    await h.api.turn(started.sessionId, 'two');

    final after = (await h.api.listSessions()).single;
    expect(after.turnCount, 2);
    expect(after.lastActivity.isAfter(before.lastActivity), isTrue);
  });

  test('§5 limit caps the row count', () async {
    await h.api.startSession(subject: 'maths');
    await h.api.startSession(subject: 'science');
    await h.api.startSession(subject: 'history');

    expect(await h.api.listSessions(limit: 2), hasLength(2));
    expect(await h.api.listSessions(limit: 10), hasLength(3));
  });
}
