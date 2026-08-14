// S-A3: HttpStudentModelApi against canned JSON fixtures derived from the
// binding table (API-session-http-binding.md §2.2 / §2.2.1 at BINDING_SHA
// 53f2fc51…). Pins the outgoing request (method, path, subject query,
// Authorization header) and the JSON → domain mapping, plus the auth / error
// posture (401 → Unauthenticated; 400 and everything else → TransportError).
// Hermetic: MockClient, no sockets.
import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:study_tutor_app/adapters/http_student_model_api.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/ports/student_model_api.dart';

void main() {
  late FakeIdentityProvider identity;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn(); // dev table entry #1 (binding §5.1)
  });

  StudentModelApi apiWith(
          Future<http.Response> Function(http.Request) handler) =>
      HttpStudentModelApi(
        baseUrl: 'http://gb10.tail:8100',
        identity: identity,
        client: MockClient(handler),
      );

  http.Response jsonResponse(Object body, [int status = 200]) => http.Response(
        jsonEncode(body),
        status,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );

  const enriched = {
    'student_name': 'lilymay',
    'streak_days': 6,
    'level_name': 'Learner',
    'recent_xp': 240,
    'topic_confidence': {'macbeth': 0.7, 'poetry': 0.55},
    'data_available': true,
    'total_xp': 640,
    'level_number': 5,
    'xp_into_level': 40,
    'xp_to_next_level': 460,
    'longest_streak': 8,
    'recent_achievements': [
      {
        'id': 'three_day_run',
        'name': 'Three Day Run',
        'unlocked_at': '2026-07-11T18:20:00+01:00',
        'xp_awarded': 100,
      },
    ],
    'near_achievements': [
      {
        'id': 'morning_star',
        'name': 'Morning Star',
        'description': '5 sessions started before 09:00',
        'progress': 4,
        'target': 5,
        'hint': 'One more early-morning session (4/5).',
      },
    ],
    'next_unlock': {'level': 6, 'feature': 'Exam-style practice questions'},
  };

  group('binding §2.2 — request shape', () {
    test('GET /api/student-model?subject=…, bearer token', () async {
      late http.Request seen;
      final api = apiWith((request) async {
        seen = request;
        return jsonResponse(enriched);
      });

      await api.fetch(subject: 'english');

      expect(seen.method, 'GET');
      expect(seen.url.path, '/api/student-model');
      expect(seen.url.queryParameters, {'subject': 'english'});
      expect(seen.headers['authorization'],
          'Bearer ${FakeIdentityProvider.lilymay.token}');
    });

    test('signed out → no auth header (server 401s, never a client guess)',
        () async {
      await identity.signOut();
      late http.Request seen;
      final api = apiWith((request) async {
        seen = request;
        return jsonResponse(enriched);
      });

      await api.fetch(subject: 'english');
      expect(seen.headers.containsKey('authorization'), isFalse);
    });
  });

  group('binding §2.2.1 — enriched JSON → domain', () {
    test('every field maps by its wire name', () async {
      final api = apiWith((_) async => jsonResponse(enriched));

      final m = await api.fetch(subject: 'english');

      expect(m.studentName, 'lilymay');
      expect(m.streakDays, 6);
      expect(m.levelName, 'Learner');
      expect(m.recentXp, 240);
      expect(m.topicConfidence, {'macbeth': 0.7, 'poetry': 0.55});
      expect(m.dataAvailable, isTrue);
      expect(m.totalXp, 640);
      expect(m.levelNumber, 5);
      expect(m.xpIntoLevel, 40);
      expect(m.xpToNextLevel, 460);
      expect(m.longestStreak, 8);
      expect(m.recentAchievements, hasLength(1));
      expect(m.recentAchievements.first.id, 'three_day_run');
      expect(m.recentAchievements.first.xpAwarded, 100);
      expect(m.nearAchievements, hasLength(1));
      expect(m.nearAchievements.first.id, 'morning_star');
      expect(m.nearAchievements.first.progress, 4);
      expect(m.nearAchievements.first.target, 5);
      expect(m.nextUnlock?.level, 6);
      expect(m.nextUnlock?.feature, 'Exam-style practice questions');
    });

    test('empty record (data_available:false, enrichment absent)', () async {
      final api = apiWith((_) async => jsonResponse({
            'student_name': 'lilymay',
            'streak_days': 0,
            'level_name': 'Beginner',
            'recent_xp': 0,
            'near_achievements': <Object>[],
            'topic_confidence': <String, Object>{},
            'data_available': false,
          }));

      final m = await api.fetch(subject: 'english');

      expect(m.dataAvailable, isFalse);
      expect(m.totalXp, isNull);
      expect(m.levelNumber, isNull);
      expect(m.nearAchievements, isEmpty);
      expect(m.recentAchievements, isEmpty);
      expect(m.nextUnlock, isNull);
    });
  });

  group('binding §2.2 / §4 — auth + error posture', () {
    test('401 → Unauthenticated (unseeded/invalid token, ASSUM-001)', () async {
      final api = apiWith((_) async => jsonResponse(
          {'error': 'missing or invalid token', 'error_type': 'Unauthenticated'},
          401));
      await expectLater(
          api.fetch(subject: 'english'), throwsA(isA<Unauthenticated>()));
    });

    test('400 (missing subject) → TransportError (no error_type)', () async {
      final api = apiWith((_) async =>
          jsonResponse({'error': 'Validation failed: subject is required'}, 400));
      await expectLater(
          api.fetch(subject: ''), throwsA(isA<TransportError>()));
    });

    test('500 → TransportError', () async {
      final api = apiWith(
          (_) async => jsonResponse({'error': 'Internal server error'}, 500));
      await expectLater(
          api.fetch(subject: 'english'), throwsA(isA<TransportError>()));
    });

    test('malformed 2xx body → TransportError', () async {
      final api = apiWith((_) async => http.Response('{not json', 200));
      await expectLater(
          api.fetch(subject: 'english'), throwsA(isA<TransportError>()));
    });

    test('2xx wrong shape → TransportError, never a raw TypeError', () async {
      final api = apiWith((_) async => jsonResponse({'unexpected': 'shape'}));
      await expectLater(
          api.fetch(subject: 'english'), throwsA(isA<TransportError>()));
    });

    test('network failure → TransportError', () async {
      final api = apiWith(
          (_) async => throw http.ClientException('Connection refused'));
      await expectLater(
          api.fetch(subject: 'english'), throwsA(isA<TransportError>()));
    });

    test('deadline exceeded → TransportError', () async {
      final never = Completer<http.Response>();
      final api = HttpStudentModelApi(
        baseUrl: 'http://gb10.tail:8100',
        identity: identity,
        client: MockClient((_) => never.future),
        readDeadline: const Duration(milliseconds: 20),
      );
      await expectLater(
          api.fetch(subject: 'english'), throwsA(isA<TransportError>()));
    });
  });
}
