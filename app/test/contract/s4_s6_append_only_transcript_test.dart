// Contract §4/§6 — turns are append-only (scope §4 test 2):
// transcript order is insertion order; resume_session returns the full
// ordered transcript; tutor replies are canned and deterministic.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';

import 'contract_harness.dart';

void main() {
  late ContractHarness h;

  setUp(() async {
    h = ContractHarness();
    await h.identity.signIn();
  });

  test('§6 transcript order is insertion order; resume returns it in full',
      () async {
    final started = await h.api.startSession(subject: 'maths');
    final id = started.sessionId;

    await h.api.turn(id, 'what is a fraction?');
    await h.api.turn(id, 'a part of a whole?');

    final resumed = await h.api.resumeSession(id);
    expect(resumed.turns, hasLength(4));

    expect(resumed.turns.map((t) => t.role).toList(), [
      TurnRole.user,
      TurnRole.tutor,
      TurnRole.user,
      TurnRole.tutor,
    ]);
    expect(resumed.turns[0].content, 'what is a fraction?');
    expect(resumed.turns[2].content, 'a part of a whole?');

    // §6 append-only: timestamps never go backwards in transcript order.
    for (var i = 1; i < resumed.turns.length; i++) {
      expect(
        resumed.turns[i].ts.isBefore(resumed.turns[i - 1].ts),
        isFalse,
        reason: 'turn $i out of order',
      );
    }
  });

  test('tutor replies are deterministic, keyed off turn index (scope §2.3)',
      () async {
    final started = await h.api.startSession(subject: 'maths');
    final id = started.sessionId;

    final r0 = await h.api.turn(id, 'first');
    final r1 = await h.api.turn(id, 'second');

    expect(r0.tutorResponse, FakeSessionApi.cannedReplies[0]);
    expect(r1.tutorResponse, FakeSessionApi.cannedReplies[1]);

    final resumed = await h.api.resumeSession(id);
    expect(resumed.turns[1].content, FakeSessionApi.cannedReplies[0]);
    expect(resumed.turns[3].content, FakeSessionApi.cannedReplies[1]);
  });

  test('a new turn appends after resume — nothing is rewritten', () async {
    final started = await h.api.startSession(subject: 'maths');
    final id = started.sessionId;
    await h.api.turn(id, 'one');

    final before = (await h.api.resumeSession(id)).turns;
    await h.api.turn(id, 'two');
    final after = (await h.api.resumeSession(id)).turns;

    expect(after.length, before.length + 2);
    expect(after.sublist(0, before.length), before,
        reason: 'existing prefix must be untouched (append-only)');
    expect(after[before.length].content, 'two');
  });
}
