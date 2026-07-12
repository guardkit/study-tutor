// p2-wave-3: HttpSessionApi happy paths against canned JSON fixtures derived
// from the binding table (API-session-http-binding.md §2/§3 at
// BINDING_SHA=53f2fc51a35aa051c3dd899563a5cdbb7b620061 — Revision 2).
// Each test pins BOTH directions of the wire: the outgoing request (method,
// path, query, Authorization header, JSON body) and the JSON → domain
// mapping. Hermetic: MockClient, no sockets.
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:study_tutor_app/adapters/http_session_api.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/ports/session_api.dart';

void main() {
  late FakeIdentityProvider identity;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn(); // token-lilymay — dev table entry #1 (binding §5.1)
  });

  /// An adapter whose "server" is [handler]; requests are captured there.
  SessionApi apiWith(Future<http.Response> Function(http.Request) handler) =>
      HttpSessionApi(
        baseUrl: 'http://gb10.tail:8100',
        identity: identity,
        client: MockClient(handler),
      );

  http.Response jsonResponse(Object body) => http.Response(
        jsonEncode(body),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );

  group('binding §2/§3 — request shapes', () {
    test('start_session: POST /api/sessions/start, bearer token, JSON body',
        () async {
      late http.Request seen;
      final api = apiWith((request) async {
        seen = request;
        return jsonResponse(
            {'session_id': 's-1', 'student_id': 'lilymay', 'resumed': false});
      });

      await api.startSession(subject: 'maths', topic: 'fractions');

      expect(seen.method, 'POST');
      expect(seen.url.toString(), 'http://gb10.tail:8100/api/sessions/start');
      expect(seen.headers['authorization'], 'Bearer token-lilymay');
      expect(seen.headers['content-type'], startsWith('application/json'));
      expect(jsonDecode(seen.body), {
        'subject': 'maths',
        'topic': 'fractions',
        'resume_if_active': false,
      });
    });

    test('start_session omits absent optional fields, carries the flag',
        () async {
      late http.Request seen;
      final api = apiWith((request) async {
        seen = request;
        return jsonResponse(
            {'session_id': 's-1', 'student_id': 'lilymay', 'resumed': false});
      });

      await api.startSession(subject: 'maths', resumeIfActive: true);

      expect(jsonDecode(seen.body), {
        'subject': 'maths',
        'resume_if_active': true,
      });
    });

    test('list_sessions: GET /api/sessions, filters as query params',
        () async {
      final urls = <Uri>[];
      final api = apiWith((request) async {
        urls.add(request.url);
        expect(request.method, 'GET');
        expect(request.headers['authorization'], 'Bearer token-lilymay');
        return jsonResponse([]);
      });

      await api.listSessions();
      await api.listSessions(status: SessionStatus.active, limit: 2);

      expect(urls[0].toString(), 'http://gb10.tail:8100/api/sessions',
          reason: 'no filters → no query string');
      expect(urls[1].path, '/api/sessions');
      expect(urls[1].queryParameters, {'status': 'active', 'limit': '2'});
    });

    test('turn: POST /api/sessions/{id}/turn with {user_message}, no stream '
        'field (HTTP is the whole-response variant)', () async {
      late http.Request seen;
      final api = apiWith((request) async {
        seen = request;
        return jsonResponse({'tutor_response': 'well done'});
      });

      await api.turn('s-42', 'what is a fraction?');

      expect(seen.method, 'POST');
      expect(seen.url.path, '/api/sessions/s-42/turn');
      expect(seen.headers['authorization'], 'Bearer token-lilymay');
      expect(jsonDecode(seen.body), {'user_message': 'what is a fraction?'});
    });

    test('resume/status/end hit their bound paths and methods, each under '
        'the bearer header (binding §3: every request carries it)', () async {
      final calls = <String>[];
      final api = apiWith((request) async {
        calls.add('${request.method} ${request.url.path}');
        expect(request.headers['authorization'], 'Bearer token-lilymay');
        if (request.url.path.endsWith('/end')) {
          expect(request.body, isEmpty,
              reason: 'binding §2: end_session takes a path param only');
        }
        if (request.url.path.endsWith('/resume')) {
          return jsonResponse({
            'session_id': 's-7',
            'status': 'active',
            'turns': <Object>[],
            'student_id': 'lilymay',
          });
        }
        if (request.url.path.endsWith('/status')) {
          return jsonResponse({
            'session_id': 's-7',
            'student_id': 'lilymay',
            'status': 'active',
            'turn_count': 0,
            'started_at': '2026-07-05T10:00:00Z',
            'last_activity': '2026-07-05T10:00:00Z',
            'resumable': true,
          });
        }
        return jsonResponse({'session_id': 's-7', 'status': 'ended'});
      });

      await api.resumeSession('s-7');
      await api.sessionStatus('s-7');
      await api.endSession('s-7');

      expect(calls, [
        'GET /api/sessions/s-7/resume',
        'GET /api/sessions/s-7/status',
        'POST /api/sessions/s-7/end',
      ]);
    });
  });

  group('contract §5 shapes — JSON → domain round-trips', () {
    test('start_session: new session (resumed: false, no turns)', () async {
      final api = apiWith((_) async => jsonResponse({
            'session_id': '3f2b1c9e',
            'student_id': 'lilymay',
            'resumed': false,
          }));

      final started = await api.startSession(subject: 'maths');

      expect(started.sessionId, '3f2b1c9e');
      expect(started.studentId, 'lilymay');
      expect(started.resumed, isFalse);
      expect(started.turns, isNull);
    });

    test('start_session: resumed existing session carries ordered turns',
        () async {
      final api = apiWith((_) async => jsonResponse({
            'session_id': '3f2b1c9e',
            'student_id': 'lilymay',
            'resumed': true,
            'turns': [
              {
                'role': 'user',
                'content': 'what is a fraction?',
                'ts': '2026-07-05T10:00:01Z',
              },
              {
                'role': 'tutor',
                'content': 'a part of a whole',
                'ts': '2026-07-05T10:00:05Z',
              },
            ],
          }));

      final started = await api.startSession(
          subject: 'maths', resumeIfActive: true);

      expect(started.resumed, isTrue);
      expect(started.turns, [
        TurnEntry(
            role: TurnRole.user,
            content: 'what is a fraction?',
            ts: DateTime.utc(2026, 7, 5, 10, 0, 1)),
        TurnEntry(
            role: TurnRole.tutor,
            content: 'a part of a whole',
            ts: DateTime.utc(2026, 7, 5, 10, 0, 5)),
      ]);
    });

    test('list_sessions: rows map to SessionSummary in wire order', () async {
      final api = apiWith((_) async => jsonResponse([
            {
              'session_id': 's-2',
              'subject': 'science',
              'topic': null,
              'status': 'active',
              'started_at': '2026-07-05T11:00:00Z',
              'last_activity': '2026-07-05T11:30:00Z',
              'turn_count': 3,
            },
            {
              'session_id': 's-1',
              'subject': 'maths',
              'topic': 'fractions',
              'status': 'ended',
              'started_at': '2026-07-05T09:00:00Z',
              'last_activity': '2026-07-05T09:45:00Z',
              'turn_count': 5,
            },
          ]));

      final rows = await api.listSessions();

      expect(rows, hasLength(2));
      expect(rows[0].sessionId, 's-2');
      expect(rows[0].topic, isNull);
      expect(rows[0].status, SessionStatus.active);
      expect(rows[0].lastActivity, DateTime.utc(2026, 7, 5, 11, 30));
      expect(rows[1].sessionId, 's-1',
          reason: 'wire order is preserved, never re-sorted client-side');
      expect(rows[1].status, SessionStatus.ended);
      expect(rows[1].turnCount, 5);
    });

    test('resume_session: full ordered transcript + owner', () async {
      final api = apiWith((_) async => jsonResponse({
            'session_id': 's-7',
            'status': 'active',
            'turns': [
              {'role': 'user', 'content': 'one', 'ts': '2026-07-05T10:00:01Z'},
              {
                'role': 'tutor',
                'content': 'reply one',
                'ts': '2026-07-05T10:00:04Z'
              },
              {'role': 'user', 'content': 'two', 'ts': '2026-07-05T10:01:00Z'},
              {
                'role': 'tutor',
                'content': 'reply two',
                'ts': '2026-07-05T10:01:03Z'
              },
            ],
            'student_id': 'lilymay',
          }));

      final resumed = await api.resumeSession('s-7');

      expect(resumed.sessionId, 's-7');
      expect(resumed.status, SessionStatus.active);
      expect(resumed.studentId, 'lilymay');
      expect(resumed.turns.map((t) => t.role).toList(),
          [TurnRole.user, TurnRole.tutor, TurnRole.user, TurnRole.tutor]);
      expect(resumed.turns.map((t) => t.content).toList(),
          ['one', 'reply one', 'two', 'reply two']);
    });

    test('turn: {tutor_response} maps to TurnResult', () async {
      final api = apiWith(
          (_) async => jsonResponse({'tutor_response': 'walk me through it'}));

      final result = await api.turn('s-7', 'first');

      expect(result.tutorResponse, 'walk me through it');
    });

    test('turn: non-ASCII survives the wire (UTF-8 over bodyBytes)',
        () async {
      final api = apiWith(
          (_) async => jsonResponse({'tutor_response': '½ — that’s right'}));

      final result = await api.turn('s-7', '1/2?');

      expect(result.tutorResponse, '½ — that’s right');
    });

    test('session_status: full shape incl. resumable + timestamps', () async {
      final api = apiWith((_) async => jsonResponse({
            'session_id': 's-7',
            'student_id': 'lilymay',
            'status': 'ended',
            'turn_count': 4,
            'started_at': '2026-07-05T10:00:00Z',
            'last_activity': '2026-07-05T10:20:00Z',
            'resumable': false,
          }));

      final status = await api.sessionStatus('s-7');

      expect(status.sessionId, 's-7');
      expect(status.studentId, 'lilymay');
      expect(status.status, SessionStatus.ended);
      expect(status.turnCount, 4);
      expect(status.startedAt, DateTime.utc(2026, 7, 5, 10));
      expect(status.lastActivity, DateTime.utc(2026, 7, 5, 10, 20));
      expect(status.resumable, isFalse);
    });

    test('end_session: {session_id, status:"ended"} — no block (pre-settlement)',
        () async {
      final api = apiWith((_) async =>
          jsonResponse({'session_id': 's-7', 'status': 'ended'}));

      final ended = await api.endSession('s-7');

      expect(ended.sessionId, 's-7');
      expect(ended.status, SessionStatus.ended);
      expect(ended.gamification, isNull,
          reason: 'absent block ⇒ not yet settled, never fabricated');
    });

    test('end_session: Rev 2 gamification block maps by wire name', () async {
      final api = apiWith((_) async => jsonResponse({
            'session_id': 's-7',
            'status': 'ended',
            'gamification': {
              'xp_awarded': 120,
              'total_xp': 640,
              'level_number': 5,
              'level_name': 'Learner',
              'level_up': false,
              'achievements_unlocked': [
                {'id': 'first_steps', 'name': 'First Steps', 'xp': 50},
              ],
              'streak_days': 6,
              'streak_extended': true,
            },
          }));

      final ended = await api.endSession('s-7');
      final g = ended.gamification;

      expect(g, isNotNull);
      expect(g!.xpAwarded, 120);
      expect(g.totalXp, 640);
      expect(g.levelNumber, 5);
      expect(g.levelName, 'Learner');
      expect(g.levelUp, isFalse);
      expect(g.achievementsUnlocked.single.id, 'first_steps');
      expect(g.streakDays, 6);
      expect(g.streakExtended, isTrue);
    });
  });
}
