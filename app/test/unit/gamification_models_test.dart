// S-A3: the gamification domain models parse the ratified wire shapes VERBATIM
// (end_session §5 Rev 2 block; GET /api/student-model §2.2 / §2.2.1). Locks
// field names and the data_available gating so a rename on the wire fails here.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/gamification.dart';

void main() {
  group('SessionGamification.fromJson (contract §5 Rev 2)', () {
    test('the enriched block maps by wire name', () {
      final block = SessionGamification.fromJson(const {
        'xp_awarded': 120,
        'total_xp': 640,
        'level_number': 5,
        'level_name': 'Learner',
        'level_up': false,
        'achievements_unlocked': [
          {'id': 'first_steps', 'name': 'First Steps', 'xp': 50},
        ],
        'streak_days': 6,
        'streak_extended': true,
      });

      expect(block.xpAwarded, 120);
      expect(block.totalXp, 640);
      expect(block.levelNumber, 5);
      expect(block.levelName, 'Learner');
      expect(block.levelUp, isFalse);
      expect(block.achievementsUnlocked, hasLength(1));
      expect(block.achievementsUnlocked.single.id, 'first_steps');
      expect(block.achievementsUnlocked.single.xp, 50);
      expect(block.streakDays, 6);
      expect(block.streakExtended, isTrue);
    });

    test('a missing achievements list defaults to empty (never a throw)', () {
      final block = SessionGamification.fromJson(const {
        'xp_awarded': 0,
        'total_xp': 0,
        'level_number': 1,
        'level_name': 'Beginner',
        'level_up': false,
        'streak_days': 1,
        'streak_extended': true,
      });
      expect(block.achievementsUnlocked, isEmpty);
    });
  });

  group('StudentModel.fromJson (binding §2.2 / §2.2.1)', () {
    test('data_available:false with enrichment absent → nulls, never a throw',
        () {
      final m = StudentModel.fromJson(const {
        'student_name': 'lilymay',
        'streak_days': 0,
        'level_name': 'Beginner',
        'recent_xp': 0,
        'near_achievements': <Object>[],
        'topic_confidence': <String, Object>{},
        'data_available': false,
      });
      expect(m.dataAvailable, isFalse);
      expect(m.totalXp, isNull);
      expect(m.nearAchievements, isEmpty);
      expect(m.nextUnlock, isNull);
    });

    test('R05 near_achievements:[] parses to an empty list', () {
      final m = StudentModel.fromJson(const {
        'student_name': 'lilymay',
        'streak_days': 5,
        'level_name': 'Learner',
        'recent_xp': 240,
        'near_achievements': <Object>[],
        'topic_confidence': {'macbeth': 0.7},
        'data_available': true,
      });
      expect(m.nearAchievements, isEmpty);
      expect(m.topicConfidence['macbeth'], 0.7);
    });
  });

  group('ConfidenceBand.forConfidence (design §6.1 ranges)', () {
    test('band boundaries', () {
      expect(ConfidenceBand.forConfidence(0.0), ConfidenceBand.struggling);
      expect(ConfidenceBand.forConfidence(0.39), ConfidenceBand.struggling);
      expect(ConfidenceBand.forConfidence(0.4), ConfidenceBand.developing);
      expect(ConfidenceBand.forConfidence(0.59), ConfidenceBand.developing);
      expect(ConfidenceBand.forConfidence(0.6), ConfidenceBand.secure);
      expect(ConfidenceBand.forConfidence(0.79), ConfidenceBand.secure);
      expect(ConfidenceBand.forConfidence(0.8), ConfidenceBand.mastered);
      expect(ConfidenceBand.forConfidence(1.0), ConfidenceBand.mastered);
    });

    test('labels and phrasings are the design §6.1 wording', () {
      expect(ConfidenceBand.struggling.label, 'Struggling');
      expect(ConfidenceBand.struggling.phrasing, 'needs more work');
      expect(ConfidenceBand.mastered.label, 'Mastered');
      expect(ConfidenceBand.mastered.phrasing, 'really strong');
    });
  });

  group('GamificationEconomy.levelForXp (design §3.1)', () {
    test('threshold lookups', () {
      expect(GamificationEconomy.levelForXp(0).name, 'Beginner');
      expect(GamificationEconomy.levelForXp(99).number, 1);
      expect(GamificationEconomy.levelForXp(100).number, 2);
      expect(GamificationEconomy.levelForXp(100).name, 'Novice');
      expect(GamificationEconomy.levelForXp(1000).name, 'Learner');
      expect(GamificationEconomy.levelForXp(18500).number, 15);
      expect(GamificationEconomy.levelForXp(18500).name, 'Grandmaster');
      expect(GamificationEconomy.levelForXp(999999).number, 15);
    });
  });
}
