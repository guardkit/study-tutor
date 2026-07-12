/// FakeStudentModelApi — a deterministic reference for the `StudentModelApi`
/// port (S-A3), mirroring the `composeSessionApi` fake triplet.
///
/// Composed against the [IdentityProvider] INTERFACE (KC-D7-proofing): auth is
/// decided by whether a principal is present, exactly as the real server
/// decides it from the token (§3). Signed out ⇒ [Unauthenticated] (ASSUM-001).
///
/// The snapshot is a fixed, deterministic learner record — contract tests pin
/// its exact values while live tests assert invariants. It mirrors the
/// enriched wire example in API-session-http-binding.md §2.2.1 so the Progress
/// screen reads coherently in the attended emulator walk.
library;

import '../domain/errors.dart';
import '../domain/gamification.dart';
import '../ports/identity_provider.dart';
import '../ports/student_model_api.dart';

class FakeStudentModelApi implements StudentModelApi {
  FakeStudentModelApi({required this._identity, StudentModel? model})
      : _model = model ?? defaultModel;

  final IdentityProvider _identity;
  final StudentModel _model;

  /// The deterministic seeded record (binding §2.2.1 enriched example).
  static final StudentModel defaultModel = StudentModel(
    studentName: 'lilymay',
    streakDays: 6,
    levelName: 'Learner',
    recentXp: 240,
    topicConfidence: const {
      'macbeth': 0.7,
      'poetry': 0.55,
      'jekyll and hyde': 0.35,
    },
    dataAvailable: true,
    totalXp: 640,
    levelNumber: 5,
    xpIntoLevel: 40,
    xpToNextLevel: 460,
    longestStreak: 8,
    recentAchievements: [
      RecentAchievement(
        id: 'three_day_run',
        name: 'Three Day Run',
        unlockedAt: DateTime.parse('2026-07-11T18:20:00+01:00'),
        xpAwarded: 100,
      ),
      RecentAchievement(
        id: 'first_steps',
        name: 'First Steps',
        unlockedAt: DateTime.parse('2026-07-06T08:05:00+01:00'),
        xpAwarded: 50,
      ),
    ],
    nearAchievements: const [
      NearAchievement(
        id: 'morning_star',
        name: 'Morning Star',
        description: '5 sessions started before 09:00',
        progress: 4,
        target: 5,
        hint: 'One more early-morning session (4/5).',
      ),
      NearAchievement(
        id: 'poetry_pioneer',
        name: 'Poetry Pioneer',
        description: 'Complete 2 sessions on Power & Conflict poetry',
        progress: 1,
        target: 2,
        hint: 'One more Power & Conflict poetry session (1/2).',
      ),
    ],
    nextUnlock: const NextUnlock(
      level: 6,
      feature: 'Exam-style practice questions',
    ),
  );

  /// The warm-zero-state record (`data_available:false`) — a seeded student
  /// with nothing banked yet. Enrichment fields absent (null / empty).
  static const StudentModel zeroState = StudentModel(
    studentName: 'lilymay',
    streakDays: 0,
    levelName: 'Beginner',
    recentXp: 0,
    topicConfidence: {},
    dataAvailable: false,
  );

  @override
  Future<StudentModel> fetch({required String subject}) async {
    if (_identity.currentPrincipal == null) {
      throw const Unauthenticated();
    }
    return _model;
  }
}
