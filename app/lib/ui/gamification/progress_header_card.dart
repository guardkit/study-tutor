import 'package:flutter/material.dart';

import '../../domain/gamification.dart';
import 'level_progress_bar.dart';
import 'streak_badge.dart';

/// The Home progress header card (spec §6.1): level title in the display face,
/// the XP-into-level bar, the streak badge, and this-week XP. Tapping it opens
/// the Progress screen.
///
/// The card is NEVER hidden: a null snapshot (still loading) or one with
/// `data_available:false` renders a warm zero-state (spec §1 register), not an
/// empty gap.
class ProgressHeaderCard extends StatelessWidget {
  const ProgressHeaderCard({
    super.key,
    required this.model,
    required this.aliveToday,
    required this.onTap,
  });

  /// The cached student-model snapshot, or null before the first load.
  final StudentModel? model;
  final bool aliveToday;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final snapshot = model;
    final isZeroState = snapshot == null || !snapshot.dataAvailable;

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: isZeroState
              ? _zeroState(theme)
              : _populated(theme, snapshot),
        ),
      ),
    );
  }

  Widget _zeroState(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Your progress', style: theme.textTheme.titleLarge),
        const SizedBox(height: 8),
        Text(
          'Finish your first session to earn XP, start a streak, and level up '
          'from Beginner.',
          style: theme.textTheme.bodyLarge
              ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
        ),
      ],
    );
  }

  Widget _populated(ThemeData theme, StudentModel m) {
    final hasBar = m.xpIntoLevel != null && m.xpToNextLevel != null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    m.levelNumber == null
                        ? m.levelName
                        : 'Level ${m.levelNumber} · ${m.levelName}',
                    style: theme.textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${m.recentXp} XP this week',
                    style: theme.textTheme.labelLarge
                        ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            StreakBadge(streakDays: m.streakDays, aliveToday: aliveToday),
          ],
        ),
        if (hasBar) ...[
          const SizedBox(height: 12),
          LevelProgressBar(
            xpIntoLevel: m.xpIntoLevel!,
            xpToNextLevel: m.xpToNextLevel!,
          ),
        ],
      ],
    );
  }
}
