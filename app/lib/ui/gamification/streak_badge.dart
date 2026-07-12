import 'package:flutter/material.dart';

import '../theme/motion.dart';

/// The streak badge (spec §6.1): a flame + the day count.
///
/// - Alive today (a session extended the streak this app run): the flame glows
///   in the gold tertiary role and gets the subtle idle pulse (spec §1 — the
///   pulse runs ONLY while today's streak is alive).
/// - Streak > 0 but not yet extended today (yesterday-anchored): greyed, with
///   the warm "ends tonight" hint — no shaming, just a nudge (spec §1 register).
/// - No streak yet: a neutral flame at 0, no hint, no pulse.
///
/// There is no wire field for "alive today", so [aliveToday] is app-local UX
/// state threaded from [ProgressStore.streakAliveToday]; nothing is invented on
/// the wire.
class StreakBadge extends StatefulWidget {
  const StreakBadge({
    super.key,
    required this.streakDays,
    required this.aliveToday,
  });

  final int streakDays;
  final bool aliveToday;

  @override
  State<StreakBadge> createState() => _StreakBadgeState();
}

class _StreakBadgeState extends State<StreakBadge>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: AppMotion.flamePulse,
  );

  @override
  void initState() {
    super.initState();
    _syncPulse();
  }

  @override
  void didUpdateWidget(StreakBadge oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.aliveToday != widget.aliveToday) _syncPulse();
  }

  void _syncPulse() {
    if (widget.aliveToday && widget.streakDays > 0) {
      _pulse.repeat(reverse: true);
    } else {
      _pulse.stop();
      _pulse.value = 0;
    }
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasStreak = widget.streakDays > 0;
    final alive = hasStreak && widget.aliveToday;

    final flameColor = alive
        ? theme.colorScheme.tertiary
        : theme.colorScheme.onSurfaceVariant;
    final countStyle = theme.textTheme.titleMedium?.copyWith(
      color: alive
          ? theme.colorScheme.onSurface
          : theme.colorScheme.onSurfaceVariant,
      fontWeight: FontWeight.w600,
    );

    return Semantics(
      label: streakSemanticLabel(widget.streakDays, widget.aliveToday),
      container: true,
      excludeSemantics: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedBuilder(
                animation: _pulse,
                builder: (context, child) {
                  final scale = alive ? 1 + 0.12 * _pulse.value : 1.0;
                  return Transform.scale(scale: scale, child: child);
                },
                child: Icon(
                  Icons.local_fire_department,
                  color: flameColor,
                  size: 22,
                ),
              ),
              const SizedBox(width: 4),
              Text('${widget.streakDays}', style: countStyle),
            ],
          ),
          Text(
            hasStreak ? 'day streak' : 'no streak yet',
            style: theme.textTheme.labelMedium
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
          if (hasStreak && !widget.aliveToday)
            Text(
              'ends tonight',
              style: theme.textTheme.labelMedium
                  ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
        ],
      ),
    );
  }
}

/// A screen-reader phrase for a streak state, shared by the badge and the Home
/// header card's composite label. Warm, never shaming (spec §1 register).
String streakSemanticLabel(int streakDays, bool aliveToday) {
  if (streakDays <= 0) return 'No streak yet';
  if (aliveToday) return '$streakDays day streak, kept alive today';
  return '$streakDays day streak, ends tonight';
}
