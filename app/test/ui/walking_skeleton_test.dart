// Wave-5 widget tests: the app boots to sign-in and navigation between the
// three skeleton screens works (build plan wave-5; placeholder content only).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/ui/app.dart';

void main() {
  testWidgets('app boots to the sign-in screen', (tester) async {
    await tester.pumpWidget(const StudyTutorApp());

    expect(find.text('Study Tutor'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Sign in'), findsOneWidget);
  });

  testWidgets('sign-in → home → session → back to home', (tester) async {
    await tester.pumpWidget(const StudyTutorApp());

    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Home'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Start new session'),
        findsOneWidget);
    expect(find.text('Sign in'), findsNothing,
        reason: 'sign-in is replaced, not stacked');

    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    expect(find.text('Session'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('No messages yet'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Home'), findsOneWidget);
  });
}
