// Contract §4 — per-turn durability analogue (scope §4 test 3): each
// (user, tutor) pair is committed to the store as the turn completes, so a
// second client object over the SAME store (same student — the §3
// cross-device pickup rule) resumes mid-session and sees every completed
// turn. In-memory, "durable" = visible through the shared store, not only
// via the client that wrote it.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_harness.dart';

void main() {
  test('§4 a second device resumes mid-session and sees every completed turn',
      () async {
    final h = ContractHarness();
    await h.identity.signIn();

    // Device A starts and speaks — the session is never ended.
    final started = await h.api.startSession(subject: 'maths');
    final id = started.sessionId;
    await h.api.turn(id, 'one');
    await h.api.turn(id, 'two');

    // Device B: a different client object over the same store.
    final deviceB = h.secondClient();
    final resumed = await deviceB.resumeSession(id);

    expect(resumed.status, SessionStatus.active);
    expect(resumed.turns, hasLength(4),
        reason: 'both completed (user, tutor) pairs are already durable');
    expect(resumed.turns.map((t) => t.content).toList()..removeWhere(
        (c) => c != 'one' && c != 'two'), ['one', 'two']);
  });

  test('§4 turns made on the second device are visible back on the first',
      () async {
    final h = ContractHarness();
    await h.identity.signIn();

    final started = await h.api.startSession(subject: 'maths');
    final id = started.sessionId;
    await h.api.turn(id, 'from device A');

    final deviceB = h.secondClient();
    await deviceB.turn(id, 'from device B');

    // Device A sees the store state, not its own cache: §4 session_version
    // (turn_count) lets it detect the session advanced elsewhere.
    final statusOnA = await h.api.sessionStatus(id);
    expect(statusOnA.turnCount, 2);

    final transcriptOnA = (await h.api.resumeSession(id)).turns;
    expect(transcriptOnA, hasLength(4));
    expect(transcriptOnA[2].content, 'from device B');
  });
}
