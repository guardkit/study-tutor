import 'package:flutter/material.dart';

/// The XP-into-level progress bar (spec §6.1): fills `xpIntoLevel /
/// (xpIntoLevel + xpToNextLevel)`. At the terminal level `xpToNextLevel` is 0
/// (design §3.1) → a full bar. Values come straight off the wire; nothing is
/// recomputed here.
class LevelProgressBar extends StatelessWidget {
  const LevelProgressBar({
    super.key,
    required this.xpIntoLevel,
    required this.xpToNextLevel,
    this.showLabel = true,
  });

  final int xpIntoLevel;
  final int xpToNextLevel;

  /// Whether to render the "N XP to the next level" caption under the bar.
  final bool showLabel;

  double get _fraction {
    final span = xpIntoLevel + xpToNextLevel;
    if (span <= 0) return 1; // terminal level (Grandmaster) — full.
    return (xpIntoLevel / span).clamp(0.0, 1.0);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: _fraction,
            minHeight: 8,
            backgroundColor: theme.colorScheme.surfaceContainerHighest,
            valueColor:
                AlwaysStoppedAnimation<Color>(theme.colorScheme.primary),
          ),
        ),
        if (showLabel) ...[
          const SizedBox(height: 4),
          Text(
            xpToNextLevel <= 0
                ? 'Top level reached'
                : '$xpToNextLevel XP to the next level',
            style: theme.textTheme.labelLarge
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
        ],
      ],
    );
  }
}
