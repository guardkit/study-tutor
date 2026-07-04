// Contract §4 — per-turn durability analogue (scope §4 test 3): each
// (user, tutor) pair is committed as the turn completes, so a second client
// over the SAME backend (same student — the §3 cross-device pickup rule)
// resumes mid-session and sees every completed turn. Against the fake,
// "durable" = visible through the shared store, not only via the client
// that wrote it; live, it is real per-turn durability.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_backend.dart';
import 'fake_contract_backend.dart';

void main() => runDurabilitySecondClientTests(FakeContractBackend.new);

void runDurabilitySecondClientTests(ContractBackend Function() newBackend) {
  late ContractBackend b;

  setUp(() async {
    b = newBackend();
    await b.reset();
    await b.signIn();
  });

  test('§4 a second device resumes mid-session and sees every completed turn',
      () async {
    // Device A starts and speaks — the session is never ended.
    final started = await b.api.startSession(subject: 'maths');
    final id = started.sessionId;
    await b.api.turn(id, 'one');
    await b.api.turn(id, 'two');

    // Device B: a different client object over the same backend.
    final deviceB = b.secondClient();
    final resumed = await deviceB.resumeSession(id);

    expect(resumed.status, SessionStatus.active);
    expect(resumed.turns, hasLength(4),
        reason: 'both completed (user, tutor) pairs are already durable');
    expect(
        resumed.turns.map((t) => t.content).toList()
          ..removeWhere((c) => c != 'one' && c != 'two'),
        ['one', 'two']);
  });

  test('§4 turns made on the second device are visible back on the first',
      () async {
    final started = await b.api.startSession(subject: 'maths');
    final id = started.sessionId;
    await b.api.turn(id, 'from device A');

    final deviceB = b.secondClient();
    await deviceB.turn(id, 'from device B');

    // Device A sees the backend state, not its own cache: §4 session_version
    // (turn_count) lets it detect the session advanced elsewhere.
    final statusOnA = await b.api.sessionStatus(id);
    expect(statusOnA.turnCount, 2);

    final transcriptOnA = (await b.api.resumeSession(id)).turns;
    expect(transcriptOnA, hasLength(4));
    expect(transcriptOnA[2].content, 'from device B');
  });
}
