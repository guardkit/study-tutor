// TranscriptView: the extracted read-only transcript renderer (spec §3).
// Renders the ordered turns as bubbles with NO input bar, and shows an
// empty-state when there is nothing to render.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/ui/transcript_view.dart';

void main() {
  // A LOCAL time so the revealed clock label is timezone-stable (the bubble
  // formats `ts.toLocal()`).
  final t0 = DateTime(2026, 7, 4, 9);

  List<TurnEntry> transcript() => [
        TurnEntry(role: TurnRole.user, content: 'user-msg-0', ts: t0),
        TurnEntry(role: TurnRole.tutor, content: 'tutor-msg-0', ts: t0),
        TurnEntry(role: TurnRole.user, content: 'user-msg-1', ts: t0),
        TurnEntry(role: TurnRole.tutor, content: 'tutor-msg-1', ts: t0),
      ];

  Widget wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

  testWidgets('renders every turn, in transcript order', (tester) async {
    await tester.pumpWidget(wrap(TranscriptView(turns: transcript())));
    await tester.pumpAndSettle();

    expect(find.text('user-msg-0'), findsOneWidget);
    expect(find.text('tutor-msg-0'), findsOneWidget);
    expect(find.text('user-msg-1'), findsOneWidget);
    expect(find.text('tutor-msg-1'), findsOneWidget);

    // Order is turn order: each item sits below the previous one.
    double y(String t) => tester.getTopLeft(find.text(t)).dy;
    expect(y('user-msg-0'), lessThan(y('tutor-msg-0')));
    expect(y('tutor-msg-0'), lessThan(y('user-msg-1')));
    expect(y('user-msg-1'), lessThan(y('tutor-msg-1')));
  });

  testWidgets('is read-only: no text input field', (tester) async {
    await tester.pumpWidget(wrap(TranscriptView(turns: transcript())));
    await tester.pumpAndSettle();

    expect(find.byType(TextField), findsNothing);
  });

  testWidgets('long-press reveals a bubble timestamp', (tester) async {
    await tester.pumpWidget(wrap(TranscriptView(turns: transcript())));
    await tester.pumpAndSettle();

    expect(find.text('09:00'), findsNothing);
    await tester.longPress(find.text('user-msg-0'));
    await tester.pumpAndSettle();
    expect(find.text('09:00'), findsOneWidget);
  });

  testWidgets('empty turns + empty trailing shows the emptyState', (
    tester,
  ) async {
    await tester.pumpWidget(wrap(const TranscriptView(
      turns: [],
      emptyState: Text('nothing here'),
    )));
    await tester.pumpAndSettle();

    expect(find.text('nothing here'), findsOneWidget);
  });

  testWidgets('trailing widgets render after the turn bubbles', (tester) async {
    await tester.pumpWidget(wrap(TranscriptView(
      turns: transcript(),
      trailing: const [Text('pending-item')],
    )));
    await tester.pumpAndSettle();

    expect(find.text('pending-item'), findsOneWidget);
    expect(
      tester.getTopLeft(find.text('tutor-msg-1')).dy,
      lessThan(tester.getTopLeft(find.text('pending-item')).dy),
      reason: 'trailing items come after the confirmed turns',
    );
  });
}
