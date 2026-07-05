// Contract §3/§9 — auth required (scope §4 test 7): every verb without a
// valid token → Unauthenticated. Covers both no-principal (signed out) and
// invalidated-token (stale principal) shapes.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';

import 'contract_backend.dart';
import 'fake_contract_backend.dart';

void main() => runAuthenticationTests(FakeContractBackend.new);

void runAuthenticationTests(ContractBackend Function() newBackend) {
  late ContractBackend b;

  setUp(() async {
    b = newBackend();
    await b.reset();
    // Deliberately NOT signed in — the signed-out shape is half the point.
  });

  test('§3/§9 all six verbs while signed out → Unauthenticated', () async {
    final unauthenticated = throwsA(isA<Unauthenticated>());

    await expectLater(b.api.startSession(subject: 'maths'), unauthenticated);
    await expectLater(b.api.listSessions(), unauthenticated);
    await expectLater(b.api.resumeSession('s-1'), unauthenticated);
    await expectLater(b.api.turn('s-1', 'hello'), unauthenticated);
    await expectLater(b.api.sessionStatus('s-1'), unauthenticated);
    await expectLater(b.api.endSession('s-1'), unauthenticated);
  });

  test('§3/§9 all six verbs with an invalidated token → Unauthenticated, '
      'even though the client still holds a principal', () async {
    await b.signIn();
    final started = await b.api.startSession(subject: 'maths');
    final id = started.sessionId;

    b.invalidateCurrentToken();
    expect(b.hasLocalPrincipal, isTrue,
        reason: 'stale token: the app still thinks it is signed in');

    final unauthenticated = throwsA(isA<Unauthenticated>());
    await expectLater(b.api.startSession(subject: 'maths'), unauthenticated);
    await expectLater(b.api.listSessions(), unauthenticated);
    await expectLater(b.api.resumeSession(id), unauthenticated);
    await expectLater(b.api.turn(id, 'hello'), unauthenticated);
    await expectLater(b.api.sessionStatus(id), unauthenticated);
    await expectLater(b.api.endSession(id), unauthenticated);
  });

  test('§3 auth is checked before session lookup — invalid token + unknown '
      'id → Unauthenticated, not SessionNotFoundError', () async {
    await expectLater(
        b.api.sessionStatus('no-such-id'), throwsA(isA<Unauthenticated>()));
  });
}
