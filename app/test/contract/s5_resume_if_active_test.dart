// Contract §5 — start_session(resume_if_active) is keyed on
// (student, subject) (scope §4 test 5): it returns the existing active
// session with its turns instead of creating a new one; a different subject,
// or omitting the flag, creates a new session.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';

import 'contract_backend.dart';
import 'fake_contract_backend.dart';

void main() => runResumeIfActiveTests(FakeContractBackend.new);

void runResumeIfActiveTests(ContractBackend Function() newBackend) {
  late ContractBackend b;

  setUp(() async {
    b = newBackend();
    await b.reset();
    await b.signIn();
  });

  test('§5 resume_if_active returns the existing active (student, subject) '
      'session with resumed: true and its turns', () async {
    final first = await b.api.startSession(subject: 'maths');
    await b.api.turn(first.sessionId, 'one');
    await b.api.turn(first.sessionId, 'two');

    final again =
        await b.api.startSession(subject: 'maths', resumeIfActive: true);

    expect(again.sessionId, first.sessionId);
    expect(again.resumed, isTrue);
    expect(again.turns, isNotNull);
    expect(again.turns, hasLength(4));
    expect(again.turns!.first.content, 'one');
  });

  test('§5 a different subject creates a new session', () async {
    final maths = await b.api.startSession(subject: 'maths');

    final science =
        await b.api.startSession(subject: 'science', resumeIfActive: true);

    expect(science.sessionId, isNot(maths.sessionId));
    expect(science.resumed, isFalse);
  });

  test('§5 omitting the flag always creates a new session', () async {
    final first = await b.api.startSession(subject: 'maths');
    final second = await b.api.startSession(subject: 'maths');

    expect(second.sessionId, isNot(first.sessionId));
    expect(second.resumed, isFalse);
  });

  test('§5 (ruled 2026-08-04) a fresh start ENDS the active (student, '
      'subject) match — end-then-create, never a second active', () async {
    // Rich's option (b) ruling on the double-active seam: the fake
    // implements it (bb5a4fa) and the server deployed it same day
    // (19a0211, with a partial-unique-index backstop). One-active per
    // (student, subject) is what D8 cross-device pickup relies on.
    final first =
        await b.api.startSession(subject: 'maths', topic: 'fractions');

    final second = await b.api.startSession(subject: 'maths');

    expect(second.resumed, isFalse);
    expect(second.sessionId, isNot(first.sessionId));

    final active = await b.api.listSessions(status: SessionStatus.active);
    expect(active, hasLength(1),
        reason: 'the previous active was ENDED by the fresh start — '
            'one-active by construction, never a silent duplicate');
    expect(active.single.sessionId, second.sessionId);
  });

  test('§5 duplicate active (student, subject) sessions: the most recently '
      'active one wins (contract wording is singular — see QUESTIONS.md)',
      () async {
    // Since the 2026-08-04 (b) ruling, a start can no longer MINT a
    // duplicate active — the second start below ends the first
    // (end-then-create), so this now exercises resume picking the one
    // true active. The most-recent-wins rule stays pinned for any
    // duplicate that predates the ruling (or arrives via a path the
    // partial index doesn't guard) — the QUESTIONS.md wording question
    // is moot-by-construction for new data.
    final older = await b.api.startSession(subject: 'maths');
    final newer = await b.api.startSession(subject: 'maths');
    // Advance the *newer* session so it is unambiguously the most recently
    // active — the "resume where you left off" pick.
    await b.api.turn(newer.sessionId, 'latest activity here');

    final resumed =
        await b.api.startSession(subject: 'maths', resumeIfActive: true);

    expect(resumed.sessionId, newer.sessionId);
    expect(resumed.sessionId, isNot(older.sessionId));
    expect(resumed.resumed, isTrue);
  });

  test('§5 an ended session never matches — resume_if_active only matches '
      'active sessions', () async {
    final first = await b.api.startSession(subject: 'maths');
    await b.api.endSession(first.sessionId);

    final again =
        await b.api.startSession(subject: 'maths', resumeIfActive: true);

    expect(again.sessionId, isNot(first.sessionId));
    expect(again.resumed, isFalse);
  });
}
