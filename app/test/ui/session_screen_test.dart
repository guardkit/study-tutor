// SessionScreen tap-to-talk UX + VoiceUnavailable degradation widget tests.
// Covers AC-001 through AC-008 per TASK-VC-005.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ports/voice_api.dart';
import 'package:study_tutor_app/ui/session_screen.dart';

void main() {
  late FakeIdentityProvider identity;
  late FakeSessionApi sessionApi;
  late FakeVoiceApi voiceApi;
  late FlakyVoiceApi flakyVoice;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn();
    sessionApi = FakeSessionApi(identity: identity);
    voiceApi = FakeVoiceApi();
    flakyVoice = FlakyVoiceApi(voiceApi);
  });

  Widget makeScreen({VoiceApi? voice, String? sessionId}) {
    return MaterialApp(
      home: SessionScreen(
        identity: identity,
        sessionApi: sessionApi,
        sessionId: sessionId ?? 'test-session',
        voiceApi: voice ?? voiceApi,
      ),
    );
  }

  group('Mic button states', () {
    testWidgets('AC-001: mic button is present and enabled initially',
        (tester) async {
      await tester.pumpWidget(makeScreen());

      final micButton = find.widgetWithIcon(IconButton, Icons.mic);
      expect(micButton, findsOneWidget);

      final button = tester.widget<IconButton>(micButton);
      expect(button.onPressed, isNotNull,
          reason: 'mic should be enabled initially');
    });

    testWidgets('AC-001: press mic → icon changes to stop, elapsed indicator',
        (tester) async {
      await tester.pumpWidget(makeScreen());

      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();

      // Icon changes to stop
      expect(find.widgetWithIcon(IconButton, Icons.stop), findsOneWidget);
      expect(find.widgetWithIcon(IconButton, Icons.mic), findsNothing);

      // Elapsed indicator shows
      expect(find.text('0s'), findsOneWidget);
    });

    testWidgets('AC-001: press mic while sending does nothing', (tester) async {
      await tester.pumpWidget(makeScreen());

      // Start a text send
      await tester.enterText(find.byType(TextField), 'Hello');
      await tester.tap(find.widgetWithIcon(IconButton, Icons.send));
      await tester.pump();

      // Mic should be disabled during send
      final micButton = find.widgetWithIcon(IconButton, Icons.mic);
      final button = tester.widget<IconButton>(micButton);
      expect(button.onPressed, isNull,
          reason: 'mic disabled while sending');
    });

    testWidgets('AC-007: mic is disabled when session ended', (tester) async {
      // Create a session first so endSession can succeed
      final result = await sessionApi.startSession(subject: 'test subject');

      await tester.pumpWidget(makeScreen(sessionId: result.sessionId));

      await tester.tap(find.text('End session'));
      await tester.pumpAndSettle();

      final micButton = find.widgetWithIcon(IconButton, Icons.mic);
      final button = tester.widget<IconButton>(micButton);
      expect(button.onPressed, isNull, reason: 'mic disabled after session end');
    });
  });

  group('Voice turn flow', () {
    testWidgets('AC-002: transcript shows first, then spoken answer',
        (tester) async {
      await tester.pumpWidget(makeScreen());

      // Press mic to start recording
      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();

      // Press stop to send
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      // Should have 2 turns: user transcript + tutor answer
      // The fake returns: "What is the quadratic formula?" and answer
      expect(find.text('What is the quadratic formula?'), findsOneWidget);
      expect(
          find.textContaining("Let's break that down together"), findsOneWidget);
    });

    testWidgets('AC-002: multiple voice turns cycle through canned responses',
        (tester) async {
      await tester.pumpWidget(makeScreen());

      // First voice turn
      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      expect(find.text('What is the quadratic formula?'), findsOneWidget);

      // Second voice turn
      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      expect(find.text('How do I solve for x?'), findsOneWidget);
    });
  });

  group('VoiceUnavailable degradation', () {
    testWidgets('AC-003: amber notice with exact copy, mic disabled',
        (tester) async {
      flakyVoice.failing.add('voiceTurn');
      flakyVoice.errorToThrow = const VoiceUnavailable();

      await tester.pumpWidget(makeScreen(voice: flakyVoice));

      // Try to record and send
      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      // Amber notice with exact copy
      expect(
          find.text("Spoken answers aren't available right now — text still works"),
          findsOneWidget);

      // Mic should be disabled now
      final micButton = find.widgetWithIcon(IconButton, Icons.mic);
      final button = tester.widget<IconButton>(micButton);
      expect(button.onPressed, isNull,
          reason: 'mic disabled after VoiceUnavailable');
    });

    testWidgets('AC-003: mic stays visible after VoiceUnavailable',
        (tester) async {
      flakyVoice.failing.add('voiceTurn');
      flakyVoice.errorToThrow = const VoiceUnavailable();

      await tester.pumpWidget(makeScreen(voice: flakyVoice));

      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      // Mic icon should still be visible (but disabled)
      expect(find.widgetWithIcon(IconButton, Icons.mic), findsOneWidget);
    });
  });

  group('Error handling', () {
    testWidgets('AC-004: TransportError shows connection problem dialog',
        (tester) async {
      flakyVoice.failing.add('voiceTurn');
      flakyVoice.errorToThrow = const TransportError();

      await tester.pumpWidget(makeScreen(voice: flakyVoice));

      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      // Dialog shows
      expect(find.text('Connection problem'), findsOneWidget);
      expect(
          find.textContaining("Couldn't reach the tutor"), findsOneWidget);
    });

    testWidgets('AC-006: UnsupportedAudioFormat shows plain-terms message',
        (tester) async {
      flakyVoice.failing.add('voiceTurn');
      flakyVoice.errorToThrow = const UnsupportedAudioFormat();

      await tester.pumpWidget(makeScreen(voice: flakyVoice));

      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      expect(find.text("That audio format isn't supported — try recording again"),
          findsOneWidget);
    });

    testWidgets('AC-006: EmptyRecording shows plain-terms message',
        (tester) async {
      flakyVoice.failing.add('voiceTurn');
      flakyVoice.errorToThrow = const EmptyRecording();

      await tester.pumpWidget(makeScreen(voice: flakyVoice));

      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      expect(
          find.text(
              "That recording was too short — please speak your question clearly"),
          findsOneWidget);
    });

    testWidgets('AC-006: UnintelligibleQuery shows plain-terms message',
        (tester) async {
      flakyVoice.failing.add('voiceTurn');
      flakyVoice.errorToThrow = const UnintelligibleQuery();

      await tester.pumpWidget(makeScreen(voice: flakyVoice));

      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      expect(
          find.text(
              "I couldn't understand that — could you try again more clearly?"),
          findsOneWidget);
    });

    testWidgets('AC-006: QueryTooLong shows plain-terms message',
        (tester) async {
      flakyVoice.failing.add('voiceTurn');
      flakyVoice.errorToThrow = const QueryTooLong();

      await tester.pumpWidget(makeScreen(voice: flakyVoice));

      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      expect(
          find.text(
              "That question is too long — try breaking it into smaller parts"),
          findsOneWidget);
    });

    testWidgets('AC-006: RecordingTooLarge shows plain-terms message',
        (tester) async {
      flakyVoice.failing.add('voiceTurn');
      flakyVoice.errorToThrow = const RecordingTooLarge();

      await tester.pumpWidget(makeScreen(voice: flakyVoice));

      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      expect(
          find.text(
              "That recording is too large — keep your questions under a minute"),
          findsOneWidget);
    });
  });

  group('Regression: typing still works', () {
    testWidgets('AC-008: typing a question works exactly as before',
        (tester) async {
      // Create a session first so turn can succeed
      final result = await sessionApi.startSession(subject: 'test subject');

      await tester.pumpWidget(makeScreen(sessionId: result.sessionId));

      await tester.enterText(find.byType(TextField), 'Hello tutor');
      await tester.tap(find.widgetWithIcon(IconButton, Icons.send));
      await tester.pumpAndSettle();

      // User message and tutor response appear
      expect(find.text('Hello tutor'), findsOneWidget);
      expect(find.textContaining("Let's break that down together"),
          findsOneWidget);
    });

    testWidgets('AC-008: typing works after VoiceUnavailable', (tester) async {
      flakyVoice.failing.add('voiceTurn');
      flakyVoice.errorToThrow = const VoiceUnavailable();

      await tester.pumpWidget(makeScreen(voice: flakyVoice));

      // Trigger VoiceUnavailable
      await tester.tap(find.widgetWithIcon(IconButton, Icons.mic));
      await tester.pump();
      await tester.tap(find.widgetWithIcon(IconButton, Icons.stop));
      await tester.pumpAndSettle();

      // Amber notice should be showing
      expect(find.text("Spoken answers aren't available right now — text still works"),
          findsOneWidget);

      // Typing should still work
      await tester.enterText(find.byType(TextField), 'Test typing');
      await tester.tap(find.widgetWithIcon(IconButton, Icons.send));
      await tester.pumpAndSettle();

      expect(find.text('Test typing'), findsOneWidget);
    });
  });
}
