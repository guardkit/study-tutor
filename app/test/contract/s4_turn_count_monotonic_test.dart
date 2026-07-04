// Contract §4 — turn_count is monotonic (scope §4 test 4): the
// session_version analogue increments per turn, never decreases, and is
// preserved across resume.
import 'package:flutter_test/flutter_test.dart';

import 'contract_harness.dart';

void main() {
  late ContractHarness h;

  setUp(() async {
    h = ContractHarness();
    await h.identity.signIn();
  });

  test('§4 turn_count starts at 0 and increments once per turn', () async {
    final started = await h.api.startSession(subject: 'maths');
    final id = started.sessionId;

    expect((await h.api.sessionStatus(id)).turnCount, 0);

    await h.api.turn(id, 'one');
    expect((await h.api.sessionStatus(id)).turnCount, 1);

    await h.api.turn(id, 'two');
    expect((await h.api.sessionStatus(id)).turnCount, 2);
  });

  test('§4 turn_count is preserved across resume and keeps climbing',
      () async {
    final started = await h.api.startSession(subject: 'maths');
    final id = started.sessionId;
    await h.api.turn(id, 'one');
    await h.api.turn(id, 'two');

    final resumed = await h.api.resumeSession(id);
    expect(resumed.turns, hasLength(4), reason: '2 turns = 4 entries');
    expect((await h.api.sessionStatus(id)).turnCount, 2,
        reason: 'resume must not reset the count');

    await h.api.turn(id, 'three');
    expect((await h.api.sessionStatus(id)).turnCount, 3);
  });

  test('§4 turn_count never decreases over a whole session history', () async {
    final started = await h.api.startSession(subject: 'maths');
    final id = started.sessionId;

    var previous = (await h.api.sessionStatus(id)).turnCount;
    for (var i = 0; i < 5; i++) {
      await h.api.turn(id, 'message $i');
      final current = (await h.api.sessionStatus(id)).turnCount;
      expect(current, greaterThan(previous));
      previous = current;
    }
  });
}
