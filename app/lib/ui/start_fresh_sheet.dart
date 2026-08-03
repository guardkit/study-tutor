import 'package:flutter/material.dart';

import '../domain/session.dart';
import 'formatting.dart';

/// The learner's choice from [showStartFreshSheet].
sealed class StartFreshChoice {
  const StartFreshChoice();
}

/// Continue the existing active session.
class ContinueActive extends StartFreshChoice {
  const ContinueActive();
}

/// End the active session and start fresh; [topic] is the learner's own
/// topic override, or null to let the planner pick.
class StartFresh extends StartFreshChoice {
  const StartFresh({this.topic});
  final String? topic;
}

/// The "you already have a session going" sheet (Lilymay's 2026-08-03
/// "switched to Macbeth" defect — Rich's product ruling, full app fix):
/// starting a session while one is active for the SAME subject must never
/// silently resume it. The learner sees what the active session is about
/// (`Continue: <topic>`) and can instead name her own topic — chips from
/// her known topics plus free text (Rich's call) — which ends the active
/// session and starts fresh with the topic override. Both verbs already
/// exist; no contract change.
Future<StartFreshChoice?> showStartFreshSheet(
  BuildContext context, {
  required SessionSummary active,
  required List<String> knownTopics,
}) {
  return showModalBottomSheet<StartFreshChoice>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) =>
        _StartFreshSheet(active: active, knownTopics: knownTopics),
  );
}

class _StartFreshSheet extends StatefulWidget {
  const _StartFreshSheet({required this.active, required this.knownTopics});

  final SessionSummary active;
  final List<String> knownTopics;

  @override
  State<_StartFreshSheet> createState() => _StartFreshSheetState();
}

class _StartFreshSheetState extends State<_StartFreshSheet> {
  final _topic = TextEditingController();

  @override
  void dispose() {
    _topic.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final activeTopic = widget.active.topic?.trim();
    final continueLabel = (activeTopic == null || activeTopic.isEmpty)
        ? 'Continue your ${titleCaseSubject(widget.active.subject)} session'
        : 'Continue: ${titleCaseSubject(activeTopic)}';

    return SafeArea(
      // Keep the sheet above the keyboard while the topic field is focused,
      // and SCROLL the content: at the S-A4 1.3x text-scale bar with the
      // keyboard up the column exceeds the sheet height (review finding —
      // probe-confirmed overflow).
      child: Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'You already have a session going',
                style: theme.textTheme.titleLarge,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                "Pick up where you left off, or end it and start fresh on "
                'something else.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () =>
                    Navigator.of(context).pop(const ContinueActive()),
                child: Text(continueLabel),
              ),
              const SizedBox(height: 20),
              Text(
                'Or start fresh on…',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              if (widget.knownTopics.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final topic in widget.knownTopics)
                      ActionChip(
                        label: Text(titleCaseSubject(topic)),
                        onPressed: () => setState(() => _topic.text = topic),
                      ),
                  ],
                ),
              ],
              const SizedBox(height: 12),
              TextField(
                controller: _topic,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  labelText: 'Topic',
                  hintText: 'e.g. An Inspector Calls',
                ),
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => _startFresh(),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: 12),
              FilledButton.tonal(
                onPressed: _startFresh,
                child: Text(
                  _topic.text.trim().isEmpty
                      ? 'End it and start fresh'
                      : 'End it and start fresh on '
                            '${titleCaseSubject(_topic.text.trim())}',
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _startFresh() {
    final topic = _topic.text.trim();
    Navigator.of(context).pop(StartFresh(topic: topic.isEmpty ? null : topic));
  }
}
