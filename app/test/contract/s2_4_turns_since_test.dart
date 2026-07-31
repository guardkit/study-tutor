// Binding §2.4 (additive addendum) — `turns_since`, the additive delta read.
// It is NOT one of the §5 six verbs: it returns the ordered transcript ROWS at
// 0-based index `>= since` plus `next` = the RAW total row count, and it reads
// ENDED sessions too (allow_ended) so a poll survives the active→ended
// transition — this verb NEVER throws SessionEnded. Runs through the same
// ContractBackend harness as the other contract files (hermetic via the fake;
// live from the p2 wave that wires the real adapter behind ContractBackend).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_backend.dart';
import 'fake_contract_backend.dart';

void main() => runTurnsSinceTests(FakeContractBackend.new);

void runTurnsSinceTests(ContractBackend Function() newBackend) {
  late ContractBackend b;

  setUp(() async {
    b = newBackend();
    await b.reset();
    await b.signIn();
  });

  /// Start an active session and run [turns] turns → `2 * turns` rows.
  Future<String> sessionWithTurns(int turns) async {
    final started = await b.api.startSession(subject: 'maths');
    for (var i = 0; i < turns; i++) {
      await b.api.turn(started.sessionId, 'q$i');
    }
    return started.sessionId;
  }

  test('since=0 returns the full ordered transcript; next = raw row count',
      () async {
    final id = await sessionWithTurns(2); // 4 rows

    final result = await b.api.turnsSince(id, 0);

    expect(result.sessionId, id);
    expect(result.status, SessionStatus.active);
    expect(result.turns, hasLength(4),
        reason: 'since=0 → every row, both (user, tutor) pairs');
    expect(result.next, 4,
        reason: 'next is the RAW total row count, not the //2 pair count');
    expect(result.turns.map((t) => t.role).toList(),
        [TurnRole.user, TurnRole.tutor, TurnRole.user, TurnRole.tutor]);
    expect(result.turns[0].content, 'q0');
    expect(result.turns[2].content, 'q1');
  });

  test('since=total returns empty with next=total (a 200, never an error)',
      () async {
    final id = await sessionWithTurns(2); // 4 rows

    final result = await b.api.turnsSince(id, 4);

    expect(result.turns, isEmpty);
    expect(result.next, 4);
  });

  test('since past the end (> total) still returns empty with next=total',
      () async {
    final id = await sessionWithTurns(1); // 2 rows

    final result = await b.api.turnsSince(id, 99);

    expect(result.turns, isEmpty);
    expect(result.next, 2);
  });

  test('a mid offset returns the tail from that row onward', () async {
    final id = await sessionWithTurns(3); // 6 rows: q0,r0,q1,r1,q2,r2

    final result = await b.api.turnsSince(id, 2);

    expect(result.next, 6, reason: 'next stays the raw total row count');
    expect(result.turns, hasLength(4), reason: 'rows [2:] — the tail');
    expect(result.turns.first.content, 'q1',
        reason: 'row index 2 (0-based) is the second user turn');
    expect(result.turns.map((t) => t.content).toList(),
        containsAllInOrder(['q1', 'q2']));
  });

  test('reads an ENDED session without throwing (allow_ended; survives the '
      'active→ended transition)', () async {
    final started = await b.api.startSession(subject: 'maths');
    final id = started.sessionId;
    await b.api.turn(id, 'hello');
    await b.api.endSession(id);

    final result = await b.api.turnsSince(id, 0);

    expect(result.status, SessionStatus.ended);
    expect(result.turns, hasLength(2),
        reason: 'the single (user, tutor) pair is still readable when ended');
    expect(result.turns.first.content, 'hello');
    expect(result.next, 2);
  });
}
