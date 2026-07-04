// Contract §4 — lifecycle & terminality (scope §4 test 1):
// start → active; end → ended; ended is terminal — turn/resume/end on an
// ended session → SessionEnded.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_harness.dart';

void main() {
  late ContractHarness h;

  setUp(() async {
    h = ContractHarness();
    await h.identity.signIn();
  });

  test('§4 start_session creates a new active session (resumed: false)',
      () async {
    final started = await h.api.startSession(subject: 'maths');
    expect(started.resumed, isFalse);
    expect(started.studentId, 'lilymay');

    // §4: active is resumable — resume answers with status active.
    final resumed = await h.api.resumeSession(started.sessionId);
    expect(resumed.status, SessionStatus.active);
    expect(resumed.turns, isEmpty);
  });

  test('§4 end_session → ended', () async {
    final started = await h.api.startSession(subject: 'maths');
    final ended = await h.api.endSession(started.sessionId);
    expect(ended.sessionId, started.sessionId);
    expect(ended.status, SessionStatus.ended);
  });

  group('§4 ended is terminal', () {
    late String endedId;

    setUp(() async {
      final started = await h.api.startSession(subject: 'maths');
      endedId = started.sessionId;
      await h.api.turn(endedId, 'hello');
      await h.api.endSession(endedId);
    });

    test('turn on ended → SessionEnded', () async {
      await expectLater(
          h.api.turn(endedId, 'again?'), throwsA(isA<SessionEnded>()));
    });

    test('resume_session on ended → SessionEnded', () async {
      await expectLater(
          h.api.resumeSession(endedId), throwsA(isA<SessionEnded>()));
    });

    test('end_session on ended → SessionEnded (no re-end, no re-open)',
        () async {
      await expectLater(
          h.api.endSession(endedId), throwsA(isA<SessionEnded>()));
    });
  });
}
