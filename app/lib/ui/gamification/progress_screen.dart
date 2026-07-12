import 'package:flutter/material.dart';

import '../../domain/gamification.dart';
import '../formatting.dart';
import '../progress_store.dart';
import '../theme/band_colors.dart';
import 'level_progress_bar.dart';

/// The Progress screen (spec §6.3), pushed from the Home header card. Sections:
/// level + progress · streak current/longest · mastery grid (band-coloured
/// `topic_confidence` cells with a "how bands work" sheet) · near-unlocks
/// (top-3 `near_achievements`) · recent achievements (last 5). Warm empty
/// states throughout. No quest / daily-challenge / boss chrome (not built —
/// no placeholder panels, spec §6.3 / §8).
class ProgressScreen extends StatelessWidget {
  const ProgressScreen({super.key, required this.store});

  final ProgressStore store;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Your progress')),
      body: ListenableBuilder(
        listenable: store,
        builder: (context, _) {
          final model = store.model;
          if (model == null) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!model.dataAvailable) {
            return _emptyRecord(context);
          }
          return _content(context, model);
        },
      ),
    );
  }

  Widget _emptyRecord(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(
          "Nothing to show yet — finish a session and your XP, streak, and "
          "topic mastery will start filling in here.",
          textAlign: TextAlign.center,
          style: theme.textTheme.bodyLarge?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }

  Widget _content(BuildContext context, StudentModel m) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _levelSection(context, m),
        const SizedBox(height: 24),
        _streakSection(context, m),
        const SizedBox(height: 24),
        _masterySection(context, m),
        const SizedBox(height: 24),
        _nearSection(context, m),
        const SizedBox(height: 24),
        _recentSection(context, m),
      ],
    );
  }

  Widget _sectionTitle(BuildContext context, String text, {Widget? trailing}) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Expanded(child: Text(text, style: theme.textTheme.titleLarge)),
          ?trailing,
        ],
      ),
    );
  }

  Widget _levelSection(BuildContext context, StudentModel m) {
    final theme = Theme.of(context);
    final hasBar = m.xpIntoLevel != null && m.xpToNextLevel != null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          m.levelNumber == null
              ? m.levelName
              : 'Level ${m.levelNumber} · ${m.levelName}',
          style: theme.textTheme.displayMedium,
        ),
        if (m.totalXp != null) ...[
          const SizedBox(height: 4),
          Text(
            '${m.totalXp} XP total',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
        if (hasBar) ...[
          const SizedBox(height: 12),
          LevelProgressBar(
            xpIntoLevel: m.xpIntoLevel!,
            xpToNextLevel: m.xpToNextLevel!,
          ),
        ],
        if (m.nextUnlock != null) ...[
          const SizedBox(height: 8),
          Text(
            'Next unlock at Level ${m.nextUnlock!.level}: '
            '${m.nextUnlock!.feature}',
            style: theme.textTheme.labelLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ],
    );
  }

  Widget _streakSection(BuildContext context, StudentModel m) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle(context, 'Streak'),
        Row(
          children: [
            Icon(
              Icons.local_fire_department,
              color: theme.colorScheme.tertiary,
            ),
            const SizedBox(width: 8),
            Text(
              '${m.streakDays}-day streak',
              style: theme.textTheme.titleMedium,
            ),
            const Spacer(),
            if (m.longestStreak != null)
              Text(
                'Longest: ${m.longestStreak}',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
          ],
        ),
      ],
    );
  }

  Widget _masterySection(BuildContext context, StudentModel m) {
    final theme = Theme.of(context);
    final entries = m.topicConfidence.entries.toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle(
          context,
          'Topic mastery',
          trailing: IconButton(
            icon: const Icon(Icons.info_outline),
            tooltip: 'How bands work',
            onPressed: () => _showBandsSheet(context),
          ),
        ),
        if (entries.isEmpty)
          Text(
            'No topics studied yet — your first session will land one here.',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          )
        else
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final e in entries) _masteryCell(context, e.key, e.value),
            ],
          ),
      ],
    );
  }

  Widget _masteryCell(BuildContext context, String topic, double confidence) {
    final theme = Theme.of(context);
    final bands = BandColors.of(context);
    final band = ConfidenceBand.forConfidence(confidence);
    final color = switch (band) {
      ConfidenceBand.struggling => bands.struggling,
      ConfidenceBand.developing => bands.developing,
      ConfidenceBand.secure => bands.secure,
      ConfidenceBand.mastered => bands.mastered,
    };
    return Container(
      width: 150,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(titleCaseSubject(topic), style: theme.textTheme.titleMedium),
          const SizedBox(height: 4),
          Row(
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              ),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  band.label,
                  style: theme.textTheme.labelLarge,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showBandsSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        final theme = Theme.of(sheetContext);
        final bands = BandColors.of(sheetContext);
        Color colorFor(ConfidenceBand b) => switch (b) {
          ConfidenceBand.struggling => bands.struggling,
          ConfidenceBand.developing => bands.developing,
          ConfidenceBand.secure => bands.secure,
          ConfidenceBand.mastered => bands.mastered,
        };
        return SafeArea(
          top: false,
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('How bands work', style: theme.textTheme.titleLarge),
                  const SizedBox(height: 12),
                  for (final b in ConfidenceBand.values)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 14,
                            height: 14,
                            margin: const EdgeInsets.only(top: 2),
                            decoration: BoxDecoration(
                              color: colorFor(b),
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  b.label,
                                  style: theme.textTheme.titleMedium,
                                ),
                                Text(
                                  b.phrasing,
                                  style: theme.textTheme.bodyMedium?.copyWith(
                                    color: theme.colorScheme.onSurfaceVariant,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _nearSection(BuildContext context, StudentModel m) {
    final theme = Theme.of(context);
    final near = m.nearAchievements.take(3).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle(context, 'Almost there'),
        if (near.isEmpty)
          Text(
            'Nothing close right now — keep going and near-misses will show up '
            'here.',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          )
        else
          for (final n in near)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(n.name, style: theme.textTheme.titleMedium),
                    const SizedBox(height: 6),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: n.target <= 0
                            ? 0
                            : (n.progress / n.target).clamp(0.0, 1.0),
                        minHeight: 6,
                        backgroundColor:
                            theme.colorScheme.surfaceContainerHighest,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          theme.colorScheme.tertiary,
                        ),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      n.hint,
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ),
      ],
    );
  }

  Widget _recentSection(BuildContext context, StudentModel m) {
    final theme = Theme.of(context);
    final recent = m.recentAchievements.take(5).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle(context, 'Recent achievements'),
        if (recent.isEmpty)
          Text(
            'No achievements yet — your first is a session away.',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          )
        else
          for (final a in recent)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(
                Icons.emoji_events,
                color: theme.colorScheme.tertiary,
              ),
              title: Text(a.name, style: theme.textTheme.titleMedium),
              subtitle: Text(relativeTime(a.unlockedAt)),
              trailing: Text(
                '+${a.xpAwarded} XP',
                style: theme.textTheme.labelLarge,
              ),
            ),
      ],
    );
  }
}
