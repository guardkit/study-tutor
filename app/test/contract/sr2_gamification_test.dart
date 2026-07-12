// Contract §5 Rev 2 + binding §2.2.1 (S-R2 gamification) through the
// ContractBackend seam. Invariants (non-null-when-present, non-negative,
// monotonic total, data_available gating) hold for BOTH backends; the fake
// additionally pins exact values (determinism is what makes the contract tests
// exact — scope §2.3). The live suite runs the same body with `exact:false`
// and asserts invariants only.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/domain/gamification.dart';

import 'contract_backend.dart';
import 'fake_contract_backend.dart';

void main() => runGamificationTests(FakeContractBackend.new, exact: true);

void runGamificationTests(
  ContractBackend Function() newBackend, {
  required bool exact,
}) {
  late ContractBackend b;

  setUp(() async {
    b = newBackend();
    await b.reset();
    await b.signIn();
  });

  Future<SessionGamification?> endAfterTurns(int turns) async {
    final started = await b.api.startSession(subject: 'english');
    for (var i = 0; i < turns; i++) {
      await b.api.turn(started.sessionId, 'q$i');
    }
    final ended = await b.api.endSession(started.sessionId);
    return ended.gamification;
  }

  void assertBlockInvariants(SessionGamification g) {
    expect(g.xpAwarded, greaterThanOrEqualTo(0));
    expect(g.totalXp, greaterThanOrEqualTo(0));
    expect(g.streakDays, greaterThanOrEqualTo(0));
    expect(g.levelNumber, inInclusiveRange(1, 15));
    for (final a in g.achievementsUnlocked) {
      expect(a.xp, greaterThanOrEqualTo(0));
    }
  }

  test('end_session settlement block is non-negative and banked', () async {
    final g = await endAfterTurns(3);
    // Live: the block may be absent (unsettled) — invariants only apply when
    // present. Fake: always present.
    if (g == null) {
      expect(exact, isFalse,
          reason: 'the fake always settles a block');
      return;
    }
    assertBlockInvariants(g);

    if (exact) {
      expect(g.xpAwarded, 120);
      expect(g.totalXp, 170);
      expect(g.levelNumber, 2);
      expect(g.levelName, 'Novice');
      expect(g.levelUp, isTrue);
      expect(g.achievementsUnlocked.single.id, 'first_steps');
      expect(g.achievementsUnlocked.single.xp, 50);
      expect(g.streakDays, 1);
      expect(g.streakExtended, isTrue);
    }
  });

  test('total_xp is monotonic across successive settlements', () async {
    final first = await endAfterTurns(3);
    final second = await endAfterTurns(1);
    if (first == null || second == null) {
      expect(exact, isFalse);
      return;
    }
    expect(second.totalXp, greaterThanOrEqualTo(first.totalXp));

    if (exact) {
      expect(first.totalXp, 170);
      expect(second.xpAwarded, 60);
      expect(second.totalXp, 230);
      expect(second.levelUp, isFalse);
      expect(second.achievementsUnlocked, isEmpty);
      expect(second.streakDays, 2);
    }
  });

  test('student-model read is data-gated and non-negative', () async {
    final m = await b.studentModelApi.fetch(subject: 'english');

    // Invariants (both backends).
    expect(m.dataAvailable, isA<bool>());
    if (m.dataAvailable) {
      expect(m.streakDays, greaterThanOrEqualTo(0));
      expect(m.recentXp, greaterThanOrEqualTo(0));
      if (m.totalXp != null) expect(m.totalXp, greaterThanOrEqualTo(0));
      if (m.levelNumber != null) {
        expect(m.levelNumber, inInclusiveRange(1, 15));
      }
      expect(m.nearAchievements.length, lessThanOrEqualTo(3));
      expect(m.recentAchievements.length, lessThanOrEqualTo(5));
    }

    if (exact) {
      expect(m.studentName, 'lilymay');
      expect(m.dataAvailable, isTrue);
      expect(m.streakDays, 6);
      expect(m.levelName, 'Learner');
      expect(m.recentXp, 240);
      expect(m.totalXp, 640);
      expect(m.levelNumber, 5);
      expect(m.xpIntoLevel, 40);
      expect(m.xpToNextLevel, 460);
      expect(m.longestStreak, 8);
      expect(m.topicConfidence['macbeth'], 0.7);
      expect(m.recentAchievements.first.id, 'three_day_run');
      expect(m.nearAchievements.first.id, 'morning_star');
      expect(m.nextUnlock?.level, 6);
    }
  });

  test('student-model read requires a valid token → Unauthenticated', () async {
    // reset() leaves the backend signed out (contract §3). A read with no
    // valid credential is Unauthenticated on both backends — the fake gates on
    // principal presence (interface-only, KC-D7-proofing), the live server on
    // the token (ASSUM-001).
    await b.reset();
    await expectLater(
      b.studentModelApi.fetch(subject: 'english'),
      throwsA(isA<Unauthenticated>()),
    );
  });
}
