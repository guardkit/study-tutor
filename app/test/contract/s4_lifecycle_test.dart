// Contract §4 — lifecycle & terminality (scope §4 test 1):
// start → active; end → ended; ended is terminal — turn/resume/end on an
// ended session → SessionEnded.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_backend.dart';
import 'fake_contract_backend.dart';

void main() => runLifecycleTests(FakeContractBackend.new);

void runLifecycleTests(ContractBackend Function() newBackend) {
  late ContractBackend b;

  setUp(() async {
    b = newBackend();
    await b.reset();
    await b.signIn();
  });

  test('§4 start_session creates a new active session (resumed: false)',
      () async {
    final started = await b.api.startSession(subject: 'maths');
    expect(started.resumed, isFalse);
    expect(started.studentId, b.defaultStudentId);

    // §4: active is resumable — resume answers with status active.
    final resumed = await b.api.resumeSession(started.sessionId);
    expect(resumed.status, SessionStatus.active);
    expect(resumed.turns, isEmpty);
  });

  test('§4 end_session → ended', () async {
    final started = await b.api.startSession(subject: 'maths');
    final ended = await b.api.endSession(started.sessionId);
    expect(ended.sessionId, started.sessionId);
    expect(ended.status, SessionStatus.ended);
  });

  group('§4 ended is terminal', () {
    late String endedId;

    setUp(() async {
      final started = await b.api.startSession(subject: 'maths');
      endedId = started.sessionId;
      await b.api.turn(endedId, 'hello');
      await b.api.endSession(endedId);
    });

    test('turn on ended → SessionEnded', () async {
      await expectLater(
          b.api.turn(endedId, 'again?'), throwsA(isA<SessionEnded>()));
    });

    test('resume_session on ended → SessionEnded (ended is terminal; §4)',
        () async {
      await expectLater(
          b.api.resumeSession(endedId), throwsA(isA<SessionEnded>()));
    });

    test('end_session on ended → SessionEnded (no re-end, no re-open)',
        () async {
      await expectLater(
          b.api.endSession(endedId), throwsA(isA<SessionEnded>()));
    });
  });
}
