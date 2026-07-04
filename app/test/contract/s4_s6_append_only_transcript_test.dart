// Contract §4/§6 — turns are append-only (scope §4 test 2):
// transcript order is insertion order; resume_session returns the full
// ordered transcript; tutor replies match the backend's reply expectation
// (the fake pins exact canned strings — scope §2.3 determinism).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_backend.dart';
import 'fake_contract_backend.dart';

void main() => runAppendOnlyTranscriptTests(FakeContractBackend.new);

void runAppendOnlyTranscriptTests(ContractBackend Function() newBackend) {
  late ContractBackend b;

  setUp(() async {
    b = newBackend();
    await b.reset();
    await b.signIn();
  });

  test('§6 transcript order is insertion order; resume returns it in full',
      () async {
    final started = await b.api.startSession(subject: 'maths');
    final id = started.sessionId;

    await b.api.turn(id, 'what is a fraction?');
    await b.api.turn(id, 'a part of a whole?');

    final resumed = await b.api.resumeSession(id);
    expect(resumed.turns, hasLength(4));

    expect(resumed.turns.map((t) => t.role).toList(), [
      TurnRole.user,
      TurnRole.tutor,
      TurnRole.user,
      TurnRole.tutor,
    ]);
    expect(resumed.turns[0].content, 'what is a fraction?');
    expect(resumed.turns[2].content, 'a part of a whole?');

    // §6 append-only: timestamps never go backwards in transcript order
    // (relative ordering — at-or-after holds on every backend).
    for (var i = 1; i < resumed.turns.length; i++) {
      expect(
        resumed.turns[i].ts.isBefore(resumed.turns[i - 1].ts),
        isFalse,
        reason: 'turn $i out of order',
      );
    }
  });

  test('tutor replies match the reply expectation, keyed off turn index '
      '(scope §2.3 — exact canned strings on the fake)', () async {
    final started = await b.api.startSession(subject: 'maths');
    final id = started.sessionId;

    final r0 = await b.api.turn(id, 'first');
    final r1 = await b.api.turn(id, 'second');

    expect(r0.tutorResponse, b.expectedTutorReply(0));
    expect(r1.tutorResponse, b.expectedTutorReply(1));

    // The transcript stores exactly the replies that were returned — a
    // backend-independent round-trip property.
    final resumed = await b.api.resumeSession(id);
    expect(resumed.turns[1].content, r0.tutorResponse);
    expect(resumed.turns[3].content, r1.tutorResponse);
  });

  test('a new turn appends after resume — nothing is rewritten', () async {
    final started = await b.api.startSession(subject: 'maths');
    final id = started.sessionId;
    await b.api.turn(id, 'one');

    final before = (await b.api.resumeSession(id)).turns;
    await b.api.turn(id, 'two');
    final after = (await b.api.resumeSession(id)).turns;

    expect(after.length, before.length + 2);
    expect(after.sublist(0, before.length), before,
        reason: 'existing prefix must be untouched (append-only)');
    expect(after[before.length].content, 'two');
  });
}
