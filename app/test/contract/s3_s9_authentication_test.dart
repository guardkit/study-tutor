// Contract §3/§9 — auth required (scope §4 test 7): every verb without a
// valid token → Unauthenticated. Covers both no-principal (signed out) and
// invalidated-token (stale principal) shapes.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';

import 'contract_harness.dart';

void main() {
  test('§3/§9 all six verbs while signed out → Unauthenticated', () async {
    final h = ContractHarness();
    final unauthenticated = throwsA(isA<Unauthenticated>());

    await expectLater(h.api.startSession(subject: 'maths'), unauthenticated);
    await expectLater(h.api.listSessions(), unauthenticated);
    await expectLater(h.api.resumeSession('s-1'), unauthenticated);
    await expectLater(h.api.turn('s-1', 'hello'), unauthenticated);
    await expectLater(h.api.sessionStatus('s-1'), unauthenticated);
    await expectLater(h.api.endSession('s-1'), unauthenticated);
  });

  test('§3/§9 all six verbs with an invalidated token → Unauthenticated, '
      'even though the client still holds a principal', () async {
    final h = ContractHarness();
    await h.identity.signIn();
    final started = await h.api.startSession(subject: 'maths');
    final id = started.sessionId;

    h.identity.invalidateCurrentToken();
    expect(h.identity.currentPrincipal, isNotNull,
        reason: 'stale token: the app still thinks it is signed in');

    final unauthenticated = throwsA(isA<Unauthenticated>());
    await expectLater(h.api.startSession(subject: 'maths'), unauthenticated);
    await expectLater(h.api.listSessions(), unauthenticated);
    await expectLater(h.api.resumeSession(id), unauthenticated);
    await expectLater(h.api.turn(id, 'hello'), unauthenticated);
    await expectLater(h.api.sessionStatus(id), unauthenticated);
    await expectLater(h.api.endSession(id), unauthenticated);
  });

  test('§3 auth is checked before session lookup — invalid token + unknown '
      'id → Unauthenticated, not SessionNotFoundError', () async {
    final h = ContractHarness();
    await expectLater(
        h.api.sessionStatus('no-such-id'), throwsA(isA<Unauthenticated>()));
  });
}
