import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../domain/session.dart';

/// A read-only transcript renderer (spec §3): the chat bubbles for an ordered
/// list of [TurnEntry], with no input bar. Extracted from `session_screen.dart`
/// so both the live session screen and the read-only Session-History view render
/// the exact same bubbles.
///
/// Long-press a bubble to reveal its timestamp (as the session screen always
/// did). [trailing] widgets are appended after the turn bubbles — the session
/// screen passes its optimistic bubble + typing indicator there; a pure history
/// view leaves it empty. When there are no turns and no trailing items,
/// [emptyState] is shown instead of an empty list.
class TranscriptView extends StatefulWidget {
  const TranscriptView({
    super.key,
    required this.turns,
    this.controller,
    this.trailing = const [],
    this.padding,
    this.emptyState,
  });

  /// The ordered transcript (§6 append-only order — never re-sorted here).
  final List<TurnEntry> turns;

  /// Optional scroll controller so an owner (the session screen) can drive
  /// auto-scroll-to-bottom against this list.
  final ScrollController? controller;

  /// Extra items rendered after the turn bubbles (optimistic bubble, typing
  /// indicator). Empty for a pure read-only view.
  final List<Widget> trailing;

  final EdgeInsetsGeometry? padding;

  /// Shown when there are no turns AND no trailing items — e.g. the session
  /// screen's "ask your first question" prompt, or the history "no messages"
  /// note. When null, an empty transcript renders nothing.
  final Widget? emptyState;

  @override
  State<TranscriptView> createState() => _TranscriptViewState();
}

class _TranscriptViewState extends State<TranscriptView> {
  /// Turn indices whose timestamp is currently revealed (long-press, spec §3).
  final Set<int> _revealedTimestamps = {};

  double _bubbleMaxWidth(BuildContext context) {
    // Spec §4: 76% of screen width, capped at 560.
    return math.min(560.0, MediaQuery.of(context).size.width * 0.76);
  }

  String _formatClock(DateTime ts) {
    final local = ts.toLocal();
    final hh = local.hour.toString().padLeft(2, '0');
    final mm = local.minute.toString().padLeft(2, '0');
    return '$hh:$mm';
  }

  Widget _bubble(BuildContext context, int index, TurnEntry turn) {
    final isUser = turn.role == TurnRole.user;
    final colors = Theme.of(context).colorScheme;
    final revealed = _revealedTimestamps.contains(index);
    final speaker = isUser ? 'You said' : 'Tutor said';
    return Semantics(
      label: '$speaker: ${turn.content}',
      child: Align(
        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
        child: GestureDetector(
          onLongPress: () => setState(() {
            revealed
                ? _revealedTimestamps.remove(index)
                : _revealedTimestamps.add(index);
          }),
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            constraints: BoxConstraints(maxWidth: _bubbleMaxWidth(context)),
            decoration: BoxDecoration(
              color: isUser
                  ? colors.primaryContainer
                  : colors.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment:
                  isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(turn.content),
                if (revealed)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      _formatClock(turn.ts),
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: colors.onSurfaceVariant,
                          ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final total = widget.turns.length + widget.trailing.length;
    if (total == 0) return widget.emptyState ?? const SizedBox.shrink();

    return ListView.builder(
      controller: widget.controller,
      padding: widget.padding,
      itemCount: total,
      itemBuilder: (context, i) {
        if (i < widget.turns.length) {
          return _bubble(context, i, widget.turns[i]);
        }
        return widget.trailing[i - widget.turns.length];
      },
    );
  }
}
