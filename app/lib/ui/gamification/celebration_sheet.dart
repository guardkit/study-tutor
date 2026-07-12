import 'package:flutter/material.dart';

import '../../domain/gamification.dart';
import '../theme/app_theme.dart';
import '../theme/motion.dart';
import 'confetti.dart';

/// Show the session-end celebration sheet (spec §6.2). Call this ONLY with a
/// non-null [SessionGamification] block — an absent block gets the plain end
/// path, never this chrome. Completes when the user dismisses the sheet.
Future<void> showCelebrationSheet(
  BuildContext context,
  SessionGamification block,
) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (sheetContext) => _CelebrationSheet(block: block),
  );
}

class _CelebrationSheet extends StatefulWidget {
  const _CelebrationSheet({required this.block});

  final SessionGamification block;

  @override
  State<_CelebrationSheet> createState() => _CelebrationSheetState();
}

class _CelebrationSheetState extends State<_CelebrationSheet>
    with TickerProviderStateMixin {
  /// XP count-up (spec §1: 800 ms).
  late final AnimationController _xp = AnimationController(
    vsync: this,
    duration: AppMotion.xpCountUp,
  );

  /// One-shot flame "tick" when the streak was extended (spec §6.2).
  late final AnimationController _streakTick = AnimationController(
    vsync: this,
    duration: AppMotion.standard,
  );

  /// Drives the staggered reveal of the unlock cards (spec §6.2).
  late final AnimationController _stagger;

  bool get _celebratory =>
      widget.block.levelUp || widget.block.achievementsUnlocked.isNotEmpty;

  @override
  void initState() {
    super.initState();
    final count = widget.block.achievementsUnlocked.length;
    _stagger = AnimationController(
      vsync: this,
      duration: AppMotion.stagger * (count == 0 ? 1 : count),
    );
    _xp.forward();
    if (widget.block.streakExtended) _streakTick.forward();
    if (count > 0) _stagger.forward();
  }

  @override
  void dispose() {
    _xp.dispose();
    _streakTick.dispose();
    _stagger.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final block = widget.block;

    final content = SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Session complete',
              textAlign: TextAlign.center,
              style: theme.textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            _xpCountUp(theme),
            const SizedBox(height: 16),
            _streakRow(theme),
            if (block.levelUp) ...[
              const SizedBox(height: 20),
              _levelUp(theme),
            ],
            if (block.achievementsUnlocked.isNotEmpty) ...[
              const SizedBox(height: 20),
              ..._unlockCards(theme),
            ],
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Nice work'),
            ),
          ],
        ),
      ),
    );

    // Confetti overlays the content, non-interactive, only when celebratory.
    return KeyedSubtree(
      key: const Key('celebration-sheet'),
      child: _celebratory
          ? Stack(
              children: [
                content,
                const Positioned.fill(
                  child: IgnorePointer(child: ConfettiBurst()),
                ),
              ],
            )
          : content,
    );
  }

  Widget _xpCountUp(ThemeData theme) {
    return AnimatedBuilder(
      animation: _xp,
      builder: (context, _) {
        final shown = (widget.block.xpAwarded * _xp.value).round();
        return Text(
          '+$shown XP',
          key: const Key('celebration-xp'),
          textAlign: TextAlign.center,
          style: AppTheme.celebrationXpNumeral
              .copyWith(color: theme.colorScheme.tertiary),
        );
      },
    );
  }

  Widget _streakRow(ThemeData theme) {
    final block = widget.block;
    return AnimatedBuilder(
      animation: _streakTick,
      builder: (context, child) {
        final scale = 1 + 0.2 * Curves.easeOut.transform(
              _streakTick.value < 0.5
                  ? _streakTick.value * 2
                  : (1 - _streakTick.value) * 2,
            );
        return Transform.scale(
          scale: block.streakExtended ? scale : 1.0,
          child: child,
        );
      },
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.local_fire_department,
              color: theme.colorScheme.tertiary, size: 22),
          const SizedBox(width: 6),
          Text(
            block.streakExtended
                ? '${block.streakDays}-day streak — kept alive!'
                : '${block.streakDays}-day streak',
            style: theme.textTheme.titleMedium,
          ),
        ],
      ),
    );
  }

  Widget _levelUp(ThemeData theme) {
    final block = widget.block;
    // The prior title is the design §3.1 catalog entry one below the new level
    // — a decorative crossfade source, not a wire value.
    final priorTitle = block.levelNumber >= 2 &&
            block.levelNumber - 2 < GamificationEconomy.titles.length
        ? GamificationEconomy.titles[block.levelNumber - 2]
        : null;
    return Column(
      children: [
        Text('Level up!',
            style: theme.textTheme.labelLarge
                ?.copyWith(color: theme.colorScheme.tertiary)),
        const SizedBox(height: 4),
        AnimatedSwitcher(
          duration: AppMotion.standard,
          switchInCurve: AppMotion.standardCurve,
          child: Text(
            'Level ${block.levelNumber} · ${block.levelName}',
            key: ValueKey(block.levelNumber),
            style: theme.textTheme.headlineSmall,
          ),
        ),
        if (priorTitle != null)
          Text(
            'from $priorTitle',
            style: theme.textTheme.labelMedium
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
      ],
    );
  }

  List<Widget> _unlockCards(ThemeData theme) {
    final unlocked = widget.block.achievementsUnlocked;
    return [
      for (var i = 0; i < unlocked.length; i++)
        AnimatedBuilder(
          animation: _stagger,
          builder: (context, child) {
            final start = unlocked.length == 1 ? 0.0 : i / unlocked.length;
            final t = ((_stagger.value - start) /
                    (1 - start).clamp(0.0001, 1.0))
                .clamp(0.0, 1.0);
            return Opacity(
              opacity: t,
              child: Transform.translate(
                offset: Offset(0, 12 * (1 - t)),
                child: child,
              ),
            );
          },
          child: Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Card(
              color: theme.colorScheme.tertiaryContainer,
              margin: EdgeInsets.zero,
              child: ListTile(
                leading: Icon(Icons.emoji_events,
                    color: theme.colorScheme.onTertiaryContainer),
                title: Text(
                  unlocked[i].name,
                  style: theme.textTheme.titleMedium?.copyWith(
                      color: theme.colorScheme.onTertiaryContainer),
                ),
                subtitle: Text(
                  'Achievement unlocked · +${unlocked[i].xp} XP',
                  style: theme.textTheme.labelLarge?.copyWith(
                      color: theme.colorScheme.onTertiaryContainer),
                ),
              ),
            ),
          ),
        ),
    ];
  }
}
