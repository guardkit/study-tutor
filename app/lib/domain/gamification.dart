/// Gamification domain models (S-A3).
///
/// Wire shapes come VERBATIM from the ratified contract docs:
/// - `end_session`'s nullable `gamification` block:
///   `API-session-cross-device.md` §5 (Revision 2) — the settlement block.
/// - `GET /api/student-model` (enriched): `API-session-http-binding.md`
///   §2.2 / §2.2.1 (Phase-R S-R2 enrichment).
///
/// These are consumed at the S-R2 ratification commit
/// `53f2fc51a35aa051c3dd899563a5cdbb7b620061` (BINDING_SHA / CONTRACT_SHA).
/// Field names are the Dart-cased forms of the contract's snake_case wire
/// names; no field is invented or anticipated beyond those docs.
library;

// ---------------------------------------------------------------------------
// end_session settlement block (contract §5 Rev 2)
// ---------------------------------------------------------------------------

/// One achievement newly banked by a settlement — each `{id, name, xp}`
/// (contract §5 Rev 2; `xp` per `design.md` §5).
class UnlockedAchievement {
  const UnlockedAchievement({
    required this.id,
    required this.name,
    required this.xp,
  });

  final String id;
  final String name;
  final int xp;

  @override
  bool operator ==(Object other) =>
      other is UnlockedAchievement &&
      other.id == id &&
      other.name == name &&
      other.xp == xp;

  @override
  int get hashCode => Object.hash(id, name, xp);

  @override
  String toString() => 'UnlockedAchievement($id, $name, $xp)';
}

/// The nullable `gamification` block returned by `end_session` once the engine
/// settles the session (contract §5 Rev 2). Absent/`null` ⇒ "settlement not
/// yet reflected", NEVER an error and NEVER a fabricated celebration.
class SessionGamification {
  const SessionGamification({
    required this.xpAwarded,
    required this.totalXp,
    required this.levelNumber,
    required this.levelName,
    required this.levelUp,
    required this.achievementsUnlocked,
    required this.streakDays,
    required this.streakExtended,
  });

  /// XP banked for *this* session (engagement-band base, `design.md` §13.1 D5).
  final int xpAwarded;

  /// `SUM(session.xp_awarded)+SUM(achievement.xp_awarded)` after this
  /// settlement (ADR-ARCH-030 D2).
  final int totalXp;

  /// The level (number/name) after this settlement.
  final int levelNumber;
  final String levelName;

  /// True iff this settlement crossed a level threshold.
  final bool levelUp;

  /// Achievements newly banked this settlement (may be empty).
  final List<UnlockedAchievement> achievementsUnlocked;

  /// Current consecutive-London-day streak after this settlement (D6).
  final int streakDays;

  /// True iff this session advanced the streak.
  final bool streakExtended;

  /// Parse the wire block. Tolerates a missing `achievements_unlocked`
  /// (defaults to empty), never invents other fields.
  factory SessionGamification.fromJson(Map<String, dynamic> json) {
    final unlocked = (json['achievements_unlocked'] as List<dynamic>?) ??
        const <dynamic>[];
    return SessionGamification(
      xpAwarded: json['xp_awarded'] as int,
      totalXp: json['total_xp'] as int,
      levelNumber: json['level_number'] as int,
      levelName: json['level_name'] as String,
      levelUp: json['level_up'] as bool,
      achievementsUnlocked: unlocked
          .map((a) => UnlockedAchievement(
                id: (a as Map<String, dynamic>)['id'] as String,
                name: a['name'] as String,
                xp: a['xp'] as int,
              ))
          .toList(),
      streakDays: json['streak_days'] as int,
      streakExtended: json['streak_extended'] as bool,
    );
  }
}

// ---------------------------------------------------------------------------
// GET /api/student-model (binding §2.2 + §2.2.1 enrichment)
// ---------------------------------------------------------------------------

/// A recent unlock in the durable record — `{id, name, unlocked_at,
/// xp_awarded}` (binding §2.2.1, last 5 newest-first).
class RecentAchievement {
  const RecentAchievement({
    required this.id,
    required this.name,
    required this.unlockedAt,
    required this.xpAwarded,
  });

  final String id;
  final String name;
  final DateTime unlockedAt;
  final int xpAwarded;

  factory RecentAchievement.fromJson(Map<String, dynamic> json) =>
      RecentAchievement(
        id: json['id'] as String,
        name: json['name'] as String,
        unlockedAt: DateTime.parse(json['unlocked_at'] as String),
        xpAwarded: json['xp_awarded'] as int,
      );
}

/// A near-miss achievement — `{id, name, description, progress, target, hint}`
/// (binding §2.2.1, top-3). `progress`/`target` are integers on the same
/// scale; `hint` is the ready-made "what gets you there" string.
class NearAchievement {
  const NearAchievement({
    required this.id,
    required this.name,
    required this.description,
    required this.progress,
    required this.target,
    required this.hint,
  });

  final String id;
  final String name;
  final String description;
  final int progress;
  final int target;
  final String hint;

  factory NearAchievement.fromJson(Map<String, dynamic> json) =>
      NearAchievement(
        id: json['id'] as String,
        name: json['name'] as String,
        description: json['description'] as String,
        progress: json['progress'] as int,
        target: json['target'] as int,
        hint: json['hint'] as String,
      );
}

/// The next level-gated feature — `{level, feature}` (binding §2.2.1).
class NextUnlock {
  const NextUnlock({required this.level, required this.feature});

  final int level;
  final String feature;

  factory NextUnlock.fromJson(Map<String, dynamic> json) => NextUnlock(
        level: json['level'] as int,
        feature: json['feature'] as String,
      );
}

/// The durable learner record served by `GET /api/student-model` (binding
/// §2.2 base + §2.2.1 enrichment). Consumers **gate on [dataAvailable]**: a
/// seeded student with nothing banked returns `data_available:false` and the
/// enrichment fields absent — those parse as nulls / empty lists here, never a
/// throw.
class StudentModel {
  const StudentModel({
    required this.studentName,
    required this.streakDays,
    required this.levelName,
    required this.recentXp,
    required this.topicConfidence,
    required this.dataAvailable,
    this.totalXp,
    this.levelNumber,
    this.xpIntoLevel,
    this.xpToNextLevel,
    this.longestStreak,
    this.recentAchievements = const [],
    this.nearAchievements = const [],
    this.nextUnlock,
  });

  // Base R05 fields (always present).
  final String studentName;
  final int streakDays;
  final String levelName;
  final int recentXp;
  final Map<String, double> topicConfidence;
  final bool dataAvailable;

  // Enrichment fields (S-R2; absent until the engine settles → nullable).
  final int? totalXp;
  final int? levelNumber;
  final int? xpIntoLevel;
  final int? xpToNextLevel;
  final int? longestStreak;
  final List<RecentAchievement> recentAchievements;
  final List<NearAchievement> nearAchievements;
  final NextUnlock? nextUnlock;

  factory StudentModel.fromJson(Map<String, dynamic> json) {
    final confidence = (json['topic_confidence'] as Map<String, dynamic>?) ??
        const <String, dynamic>{};
    final near =
        (json['near_achievements'] as List<dynamic>?) ?? const <dynamic>[];
    final recent =
        (json['recent_achievements'] as List<dynamic>?) ?? const <dynamic>[];
    final nextUnlock = json['next_unlock'] as Map<String, dynamic>?;
    return StudentModel(
      studentName: json['student_name'] as String,
      streakDays: json['streak_days'] as int,
      levelName: json['level_name'] as String,
      recentXp: json['recent_xp'] as int,
      topicConfidence: confidence.map(
        (k, v) => MapEntry(k, (v as num).toDouble()),
      ),
      dataAvailable: json['data_available'] as bool,
      totalXp: json['total_xp'] as int?,
      levelNumber: json['level_number'] as int?,
      xpIntoLevel: json['xp_into_level'] as int?,
      xpToNextLevel: json['xp_to_next_level'] as int?,
      longestStreak: json['longest_streak'] as int?,
      // near_achievements is `[]` (R05) or a list of objects (S-R2). The
      // objects path is the only one with map entries; the `[]` path yields [].
      recentAchievements: recent
          .map((a) => RecentAchievement.fromJson(a as Map<String, dynamic>))
          .toList(),
      nearAchievements: near
          .map((a) => NearAchievement.fromJson(a as Map<String, dynamic>))
          .toList(),
      nextUnlock:
          nextUnlock == null ? null : NextUnlock.fromJson(nextUnlock),
    );
  }
}

// ---------------------------------------------------------------------------
// Confidence bands (design.md §6.1) — UI banding of a [0,1] confidence value.
// ---------------------------------------------------------------------------

/// A topic-mastery confidence band (`design.md` §6.1). Used to colour the
/// mastery grid and to label cells with the design's phrasings. This is UI
/// *banding of a wire confidence value*, not recomputation of a wire field.
enum ConfidenceBand {
  struggling('Struggling', 'needs more work'),
  developing('Developing', 'coming along'),
  secure('Secure', 'feeling confident'),
  mastered('Mastered', 'really strong');

  const ConfidenceBand(this.label, this.phrasing);

  /// The band name shown as the cell label (`design.md` §6.1).
  final String label;

  /// The design's interpretation phrasing, shown in the "how bands work" sheet.
  final String phrasing;

  /// Band for a confidence in `[0,1]` (`design.md` §6.1 ranges).
  static ConfidenceBand forConfidence(double c) {
    if (c < 0.4) return ConfidenceBand.struggling;
    if (c < 0.6) return ConfidenceBand.developing;
    if (c < 0.8) return ConfidenceBand.secure;
    return ConfidenceBand.mastered;
  }
}

// ---------------------------------------------------------------------------
// Level economy (design.md §3.1) — FAKE-SIDE synthesis only.
// ---------------------------------------------------------------------------

/// A resolved level: its number (1–15) and named title.
class LevelInfo {
  const LevelInfo(this.number, this.name);
  final int number;
  final String name;
}

/// The `design.md` §3.1 level economy. **Used only by the fakes** to synthesise
/// a deterministic wire response — the UI reads `level_number`/`level_name`
/// straight off the wire and never recomputes them here.
abstract final class GamificationEconomy {
  /// Total-XP thresholds to *reach* levels 1–15 (`design.md` §3.1, re-affirmed
  /// by §13.1).
  static const List<int> thresholds = [
    0, 100, 300, 600, 1000, 1500, 2200, 3100, 4200, 5600, 7300, 9400, 11900,
    14900, 18500,
  ];

  /// Level titles 1–15 (`design.md` §3.1).
  static const List<String> titles = [
    'Beginner', 'Novice', 'Apprentice', 'Student', 'Learner', 'Scholar',
    'Academic', 'Intellectual', 'Expert', 'Master', 'Sage', 'Virtuoso',
    'Luminary', 'Prodigy', 'Grandmaster',
  ];

  /// The level for a non-negative [totalXp].
  static LevelInfo levelForXp(int totalXp) {
    var index = 0;
    for (var i = 0; i < thresholds.length; i++) {
      if (totalXp >= thresholds[i]) index = i;
    }
    return LevelInfo(index + 1, titles[index]);
  }
}
