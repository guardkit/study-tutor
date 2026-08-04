// Server-queue item 3, option (b) — ruled by Rich 2026-08-04: a start with
// `resume_if_active: false` against an active (student, subject) session
// ENDS it and creates fresh, never duplicating an active. This pins the
// FAKE (the contract's reference implementation); PROMOTE this into the
// shared contract body (test/contract/s5_resume_if_active_test.dart) once
// the spark's server-side normalisation deploys, so the live suite asserts
// the same — the fake-fidelity note in known-issues tracks that promotion.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';

void main() {
  late FakeIdentityProvider identity;
  late FakeSessionApi api;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn();
    api = FakeSessionApi(identity: identity);
  });

  test('resume_if_active:false against an active match ends it and creates '
      'fresh — never a second active (student, subject) session', () async {
    final first = await api.startSession(subject: 'english', topic: 'macbeth');

    final second = await api.startSession(subject: 'english');

    expect(second.resumed, isFalse);
    expect(second.sessionId, isNot(first.sessionId));

    final active = await api.listSessions(status: SessionStatus.active);
    expect(active, hasLength(1),
        reason: 'one-active by construction — the invariant D8 cross-device '
            'pickup relies on');
    expect(active.single.sessionId, second.sessionId);

    final all = await api.listSessions();
    final old = all.firstWhere((s) => s.sessionId == first.sessionId);
    expect(old.status, SessionStatus.ended,
        reason: 'the previous active was ENDED, not orphaned');
  });

  test('a different subject is untouched by a fresh start', () async {
    final english =
        await api.startSession(subject: 'english', topic: 'macbeth');

    await api.startSession(subject: 'french');

    final active = await api.listSessions(status: SessionStatus.active);
    expect(active, hasLength(2),
        reason: 'the one-active invariant is per (student, subject)');
    expect(
      active.map((s) => s.sessionId),
      contains(english.sessionId),
    );
  });
}
