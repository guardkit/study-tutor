/// Small presentation helpers shared by the screens (S-A2 refits, spec §3):
/// subject title-casing and relative timestamps. Pure functions — no widget or
/// theme dependency — so they are trivially unit-testable.
library;

/// Title-case a session subject for display (spec §3: "title-cased subject").
/// `null`/blank falls back to a neutral 'Session' so a subject-less screen
/// (e.g. a widget test that injects no subject) still has a sensible title.
String titleCaseSubject(String? subject) {
  final trimmed = subject?.trim() ?? '';
  if (trimmed.isEmpty) return 'Session';
  return trimmed
      .split(RegExp(r'\s+'))
      .map((word) => word.isEmpty
          ? word
          : '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}')
      .join(' ');
}

/// A short relative timestamp from [from] to [now] (spec §3: session cards get
/// a "relative timestamp from SessionSummary.lastActivity"). Deterministic and
/// clock-injectable for tests.
String relativeTime(DateTime from, {DateTime? now}) {
  final reference = now ?? DateTime.now();
  final delta = reference.difference(from);
  if (delta.isNegative || delta.inSeconds < 60) return 'just now';
  if (delta.inMinutes < 60) return '${delta.inMinutes}m ago';
  if (delta.inHours < 24) return '${delta.inHours}h ago';
  if (delta.inDays < 7) return '${delta.inDays}d ago';
  return '${(delta.inDays / 7).floor()}w ago';
}
