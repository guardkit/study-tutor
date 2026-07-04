// Wave-1 unit tests: model equality / ordering basics
// (build plan wave-1; shapes from contract §4–§6).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/principal.dart';
import 'package:study_tutor_app/domain/session.dart';

void main() {
  final t0 = DateTime.utc(2026, 7, 4, 1, 0);
  final t1 = DateTime.utc(2026, 7, 4, 1, 5);

  group('SessionStatus / TurnRole wire names', () {
    test('status names match contract §4', () {
      expect(SessionStatus.active.name, 'active');
      expect(SessionStatus.ended.name, 'ended');
    });

    test('role names match contract §5/§6', () {
      expect(TurnRole.user.name, 'user');
      expect(TurnRole.tutor.name, 'tutor');
    });
  });

  group('TurnEntry', () {
    test('value equality', () {
      final a = TurnEntry(role: TurnRole.user, content: 'hi', ts: t0);
      final b = TurnEntry(role: TurnRole.user, content: 'hi', ts: t0);
      expect(a, b);
      expect(a.hashCode, b.hashCode);
    });

    test('differs by role, content, and ts', () {
      final base = TurnEntry(role: TurnRole.user, content: 'hi', ts: t0);
      expect(base, isNot(TurnEntry(role: TurnRole.tutor, content: 'hi', ts: t0)));
      expect(base, isNot(TurnEntry(role: TurnRole.user, content: 'yo', ts: t0)));
      expect(base, isNot(TurnEntry(role: TurnRole.user, content: 'hi', ts: t1)));
    });

    test('transcript lists preserve insertion order (append-only, §6)', () {
      final transcript = [
        TurnEntry(role: TurnRole.user, content: 'first', ts: t0),
        TurnEntry(role: TurnRole.tutor, content: 'second', ts: t0),
        TurnEntry(role: TurnRole.user, content: 'third', ts: t1),
      ];
      expect(transcript.map((t) => t.content), ['first', 'second', 'third']);
    });
  });

  group('Session', () {
    Session make() => Session(
          id: 's-1',
          studentId: 'lilymay',
          subject: 'maths',
          topic: 'fractions',
          status: SessionStatus.active,
          startedAt: t0,
          lastActivity: t0,
          turnCount: 0,
        );

    test('value equality', () {
      expect(make(), make());
      expect(make().hashCode, make().hashCode);
    });

    test('copyWith advances status / lastActivity / turnCount only', () {
      final advanced = make().copyWith(
        status: SessionStatus.ended,
        lastActivity: t1,
        turnCount: 3,
      );
      expect(advanced.status, SessionStatus.ended);
      expect(advanced.lastActivity, t1);
      expect(advanced.turnCount, 3);
      // Identity fields are untouched.
      expect(advanced.id, 's-1');
      expect(advanced.studentId, 'lilymay');
      expect(advanced.subject, 'maths');
      expect(advanced.topic, 'fractions');
      expect(advanced.startedAt, t0);
    });

    test('copyWith with no args is identity', () {
      expect(make().copyWith(), make());
    });
  });

  group('SessionSummary', () {
    SessionSummary make() => SessionSummary(
          sessionId: 's-1',
          subject: 'maths',
          topic: 'fractions',
          status: SessionStatus.active,
          startedAt: t0,
          lastActivity: t1,
          turnCount: 2,
        );

    test('value equality', () {
      expect(make(), make());
      expect(make().hashCode, make().hashCode);
    });

    test('differs by turnCount', () {
      final other = SessionSummary(
        sessionId: 's-1',
        subject: 'maths',
        topic: 'fractions',
        status: SessionStatus.active,
        startedAt: t0,
        lastActivity: t1,
        turnCount: 3,
      );
      expect(make(), isNot(other));
    });
  });

  group('Principal', () {
    test('value equality on (token, displayName)', () {
      const a = Principal(token: 'tok-1', displayName: 'Lilymay');
      const b = Principal(token: 'tok-1', displayName: 'Lilymay');
      expect(a, b);
      expect(a, isNot(const Principal(token: 'tok-2', displayName: 'Lilymay')));
    });

    test('carries no studentId — derivation is the backend port\'s job (§3)',
        () {
      // Compile-time shape check by construction: Principal exposes only
      // token + displayName.
      const p = Principal(token: 'tok-1', displayName: 'Lilymay');
      expect(p.token, 'tok-1');
      expect(p.displayName, 'Lilymay');
    });
  });
}
