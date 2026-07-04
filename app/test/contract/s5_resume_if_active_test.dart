// Contract §5 — start_session(resume_if_active) is keyed on
// (student, subject) (scope §4 test 5): it returns the existing active
// session with its turns instead of creating a new one; a different subject,
// or omitting the flag, creates a new session.
import 'package:flutter_test/flutter_test.dart';

import 'contract_harness.dart';

void main() {
  late ContractHarness h;

  setUp(() async {
    h = ContractHarness();
    await h.identity.signIn();
  });

  test('§5 resume_if_active returns the existing active (student, subject) '
      'session with resumed: true and its turns', () async {
    final first = await h.api.startSession(subject: 'maths');
    await h.api.turn(first.sessionId, 'one');
    await h.api.turn(first.sessionId, 'two');

    final again =
        await h.api.startSession(subject: 'maths', resumeIfActive: true);

    expect(again.sessionId, first.sessionId);
    expect(again.resumed, isTrue);
    expect(again.turns, isNotNull);
    expect(again.turns, hasLength(4));
    expect(again.turns!.first.content, 'one');
  });

  test('§5 a different subject creates a new session', () async {
    final maths = await h.api.startSession(subject: 'maths');

    final science =
        await h.api.startSession(subject: 'science', resumeIfActive: true);

    expect(science.sessionId, isNot(maths.sessionId));
    expect(science.resumed, isFalse);
  });

  test('§5 omitting the flag always creates a new session', () async {
    final first = await h.api.startSession(subject: 'maths');
    final second = await h.api.startSession(subject: 'maths');

    expect(second.sessionId, isNot(first.sessionId));
    expect(second.resumed, isFalse);
  });

  test('§5 duplicate active (student, subject) sessions: the most recently '
      'active one wins (contract wording is singular — see QUESTIONS.md)',
      () async {
    final older = await h.api.startSession(subject: 'maths');
    final newer = await h.api.startSession(subject: 'maths');
    // Advance the *newer* session so it is unambiguously the most recently
    // active — the "resume where you left off" pick.
    await h.api.turn(newer.sessionId, 'latest activity here');

    final resumed =
        await h.api.startSession(subject: 'maths', resumeIfActive: true);

    expect(resumed.sessionId, newer.sessionId);
    expect(resumed.sessionId, isNot(older.sessionId));
    expect(resumed.resumed, isTrue);
  });

  test('§5 an ended session never matches — resume_if_active only matches '
      'active sessions', () async {
    final first = await h.api.startSession(subject: 'maths');
    await h.api.endSession(first.sessionId);

    final again =
        await h.api.startSession(subject: 'maths', resumeIfActive: true);

    expect(again.sessionId, isNot(first.sessionId));
    expect(again.resumed, isFalse);
  });
}
