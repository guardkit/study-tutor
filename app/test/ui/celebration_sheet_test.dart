// S-A3 §6.2: the session-end celebration sheet. Driven from canned blocks —
// a full block (XP count-up, streak row, unlock card, level-up), and the
// critical absent-block path (plain end, NO celebration chrome, ever).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/gamification.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ports/session_api.dart';
import 'package:study_tutor_app/ui/gamification/celebration_sheet.dart';
import 'package:study_tutor_app/ui/session_screen.dart';
import 'package:study_tutor_app/ui/theme/app_theme.dart';

/// A SessionApi that delegates everything to an inner fake but strips the
/// settlement block off `end_session` — the "settlement not yet reflected"
/// wire shape (a nullable block that is absent).
class _NullBlockSessionApi implements SessionApi {
  _NullBlockSessionApi(this._inner);
  final SessionApi _inner;

  @override
  Future<EndSessionResult> endSession(String sessionId) async {
    final r = await _inner.endSession(sessionId);
    return EndSessionResult(sessionId: r.sessionId, status: r.status);
  }

  @override
  Future<StartSessionResult> startSession(
          {String? subject, String? topic, bool resumeIfActive = false}) =>
      _inner.startSession(
          subject: subject, topic: topic, resumeIfActive: resumeIfActive);

  @override
  Future<List<SessionSummary>> listSessions({SessionStatus? status, int? limit}) =>
      _inner.listSessions(status: status, limit: limit);

  @override
  Future<ResumeSessionResult> resumeSession(String sessionId) =>
      _inner.resumeSession(sessionId);

  @override
  Future<TurnsSinceResult> turnsSince(String sessionId, int since) =>
      _inner.turnsSince(sessionId, since);

  @override
  Future<TurnResult> turn(String sessionId, String userMessage) =>
      _inner.turn(sessionId, userMessage);

  @override
  Future<SessionStatusResult> sessionStatus(String sessionId) =>
      _inner.sessionStatus(sessionId);
}

void main() {
  Widget host(SessionGamification block) {
    return MaterialApp(
      theme: AppTheme.light(),
      home: Builder(
        builder: (context) => Scaffold(
          body: Center(
            child: FilledButton(
              onPressed: () => showCelebrationSheet(context, block),
              child: const Text('open'),
            ),
          ),
        ),
      ),
    );
  }

  testWidgets('full block: XP, streak, unlock card, level-up, then dismiss',
      (tester) async {
    const block = SessionGamification(
      xpAwarded: 120,
      totalXp: 170,
      levelNumber: 2,
      levelName: 'Novice',
      levelUp: true,
      achievementsUnlocked: [
        UnlockedAchievement(id: 'first_steps', name: 'First Steps', xp: 50),
      ],
      streakDays: 3,
      streakExtended: true,
    );
    await tester.pumpWidget(host(block));

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle(); // count-up + confetti are finite

    expect(find.byKey(const Key('celebration-sheet')), findsOneWidget);
    expect(find.text('+120 XP'), findsOneWidget,
        reason: 'the count-up lands on xp_awarded');
    expect(find.text('First Steps'), findsOneWidget);
    expect(find.textContaining('+50 XP'), findsOneWidget);
    expect(find.text('Level up!'), findsOneWidget);
    expect(find.textContaining('Novice'), findsWidgets);
    expect(find.textContaining('kept alive'), findsOneWidget);

    await tester.tap(find.text('Nice work'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('celebration-sheet')), findsNothing);
  });

  testWidgets('a plain block (no unlocks, no level-up) shows no confetti card',
      (tester) async {
    const block = SessionGamification(
      xpAwarded: 60,
      totalXp: 60,
      levelNumber: 1,
      levelName: 'Beginner',
      levelUp: false,
      achievementsUnlocked: [],
      streakDays: 1,
      streakExtended: true,
    );
    await tester.pumpWidget(host(block));
    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('celebration-sheet')), findsOneWidget);
    expect(find.text('+60 XP'), findsOneWidget);
    expect(find.text('Level up!'), findsNothing);
    expect(find.byIcon(Icons.emoji_events), findsNothing,
        reason: 'no unlock cards when nothing was unlocked');
  });

  testWidgets('absent block → plain pop, NO celebration chrome, ever',
      (tester) async {
    final identity = FakeIdentityProvider();
    await identity.signIn();
    final inner = FakeSessionApi(identity: identity);
    final started = await inner.startSession(subject: 'english');
    await inner.turn(started.sessionId, 'hi');

    await tester.pumpWidget(MaterialApp(
      theme: AppTheme.light(),
      home: SessionScreen(
        identity: identity,
        sessionApi: _NullBlockSessionApi(inner),
        voiceApi: FakeVoiceApi(),
        sessionId: started.sessionId,
        subject: 'english',
      ),
    ));

    await tester.tap(find.text('End session'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('celebration-sheet')), findsNothing,
        reason: 'a null gamification block never celebrates');
    expect(find.text('Session ended'), findsOneWidget);
    expect(find.text('End session'), findsNothing);
  });
}
