// p2-wave-4: HttpSessionApi wire-error mapping + deadlines (binding §4,
// contract §9). Every `error_type` in the binding table maps to its typed
// exception; everything outside the envelope — network failure, deadline
// exceeded, 400/500 without an `error_type`, undecodable or wrong-shape
// bodies — maps to the client-local TransportError. Hermetic: MockClient,
// no sockets; deadline tests inject tiny budgets through the test-only
// constructor seam.
import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:study_tutor_app/adapters/http_session_api.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/ports/session_api.dart';

void main() {
  late FakeIdentityProvider identity;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn();
  });

  SessionApi apiWith(Future<http.Response> Function(http.Request) handler) =>
      HttpSessionApi(
        baseUrl: 'http://gb10.tail:8100',
        identity: identity,
        client: MockClient(handler),
      );

  SessionApi apiAlwaysReturning(int status, Object? body) =>
      apiWith((_) async => http.Response(
            body == null ? '' : (body is String ? body : jsonEncode(body)),
            status,
            headers: {'content-type': 'application/json'},
          ));

  group('binding §4.1 — the §9 envelope maps 1:1 onto the typed exceptions',
      () {
    test('404 SessionNotFoundError', () async {
      final api = apiAlwaysReturning(404,
          {'error': 'session_id unknown', 'error_type': 'SessionNotFoundError'});
      await expectLater(
          api.resumeSession('s-999'), throwsA(isA<SessionNotFoundError>()));
    });

    test('410 SessionEnded', () async {
      final api = apiAlwaysReturning(
          410, {'error': 'session is ended', 'error_type': 'SessionEnded'});
      await expectLater(api.turn('s-1', 'hello'), throwsA(isA<SessionEnded>()));
    });

    test('403 SessionForbidden', () async {
      final api = apiAlwaysReturning(403, {
        'error': 'session not owned by caller',
        'error_type': 'SessionForbidden'
      });
      await expectLater(
          api.sessionStatus('s-1'), throwsA(isA<SessionForbidden>()));
    });

    test('401 Unauthenticated (incl. the ASSUM-001 unseeded-student case)',
        () async {
      final api = apiAlwaysReturning(401,
          {'error': 'missing or invalid token', 'error_type': 'Unauthenticated'});
      await expectLater(api.listSessions(), throwsA(isA<Unauthenticated>()));
    });

    test('the wire message is carried into the exception', () async {
      final api = apiAlwaysReturning(404, {
        'error': 'no session with id s-404',
        'error_type': 'SessionNotFoundError'
      });
      await expectLater(
        api.endSession('s-404'),
        throwsA(isA<SessionNotFoundError>()
            .having((e) => e.message, 'message', 'no session with id s-404')),
      );
    });

    test('every verb maps the envelope, not just session_id verbs', () async {
      final api = apiAlwaysReturning(401,
          {'error': 'missing or invalid token', 'error_type': 'Unauthenticated'});
      await expectLater(
          api.startSession(subject: 'maths'), throwsA(isA<Unauthenticated>()));
    });
  });

  group('binding §4.2 — outside the closed set → TransportError', () {
    test('400 validation failure (no error_type)', () async {
      final api = apiAlwaysReturning(
          400, {'error': 'Validation failed: user_message is required'});
      await expectLater(api.turn('s-1', ''), throwsA(isA<TransportError>()));
    });

    test('500 internal error (no error_type)', () async {
      final api =
          apiAlwaysReturning(500, {'error': 'Internal server error'});
      await expectLater(
          api.resumeSession('s-1'), throwsA(isA<TransportError>()));
    });

    test('non-JSON error body (e.g. a proxy HTML page)', () async {
      final api = apiAlwaysReturning(502, '<html>Bad Gateway</html>');
      await expectLater(api.listSessions(), throwsA(isA<TransportError>()));
    });

    test('unknown error_type never crashes the closed-set switch', () async {
      final api = apiAlwaysReturning(
          418, {'error': 'novel failure', 'error_type': 'SomethingNew'});
      await expectLater(
          api.sessionStatus('s-1'), throwsA(isA<TransportError>()));
    });

    test('non-string error field (nested proxy object) without error_type '
        'degrades to TransportError, never a raw TypeError', () async {
      final api = apiAlwaysReturning(502, {
        'error': {'code': 502, 'message': 'bad gateway'},
      });
      await expectLater(api.listSessions(), throwsA(isA<TransportError>()));
    });

    test('non-string error field with a VALID error_type still maps — the '
        'discriminator wins, the message falls back to the status', () async {
      final api = apiAlwaysReturning(404, {
        'error': {'code': 404},
        'error_type': 'SessionNotFoundError',
      });
      await expectLater(
        api.resumeSession('s-999'),
        throwsA(isA<SessionNotFoundError>()
            .having((e) => e.message, 'message', 'HTTP 404')),
      );
    });

    test('fallback TransportError message carries the status exactly once',
        () async {
      final api = apiAlwaysReturning(401, null);
      await expectLater(
        api.listSessions(),
        throwsA(isA<TransportError>()
            .having((e) => e.message, 'message', 'HTTP 401')),
      );
    });
  });

  group('malformed 2xx bodies → TransportError', () {
    test('undecodable JSON', () async {
      final api = apiAlwaysReturning(200, '{not json');
      await expectLater(api.listSessions(), throwsA(isA<TransportError>()));
    });

    test('decodes but does not fit the §5 shape', () async {
      final api = apiAlwaysReturning(200, {'unexpected': 'shape'});
      await expectLater(
          api.turn('s-1', 'hello'), throwsA(isA<TransportError>()));
    });

    test('out-of-enum turn role → TransportError, never a raw ArgumentError',
        () async {
      final api = apiAlwaysReturning(200, {
        'session_id': 's-1',
        'status': 'active',
        'turns': [
          {'role': 'system', 'content': 'x', 'ts': '2026-07-05T10:00:00Z'},
        ],
        'student_id': 'lilymay',
      });
      await expectLater(
          api.resumeSession('s-1'), throwsA(isA<TransportError>()));
    });

    test('out-of-enum session status (a newer backend\'s "paused", say) → '
        'TransportError, never a raw ArgumentError', () async {
      final api = apiAlwaysReturning(200, [
        {
          'session_id': 's-1',
          'subject': 'maths',
          'topic': null,
          'status': 'paused',
          'started_at': '2026-07-05T10:00:00Z',
          'last_activity': '2026-07-05T10:00:00Z',
          'turn_count': 1,
        },
      ]);
      await expectLater(api.listSessions(), throwsA(isA<TransportError>()));
    });
  });

  group('network failure and deadlines → TransportError', () {
    test('connection failure (ClientException)', () async {
      final api = apiWith(
          (_) async => throw http.ClientException('Connection refused'));
      await expectLater(
          api.startSession(subject: 'maths'), throwsA(isA<TransportError>()));
    });

    test('read verb exceeding its deadline', () async {
      final never = Completer<http.Response>();
      final api = HttpSessionApi(
        baseUrl: 'http://gb10.tail:8100',
        identity: identity,
        client: MockClient((_) => never.future),
        readDeadline: const Duration(milliseconds: 20),
      );
      await expectLater(api.listSessions(), throwsA(isA<TransportError>()));
    });

    test('turn exceeding its (longer) deadline', () async {
      final never = Completer<http.Response>();
      final api = HttpSessionApi(
        baseUrl: 'http://gb10.tail:8100',
        identity: identity,
        client: MockClient((_) => never.future),
        turnDeadline: const Duration(milliseconds: 20),
      );
      await expectLater(
          api.turn('s-1', 'hello'), throwsA(isA<TransportError>()));
    });

    test('default deadlines sit at the product budgets (90s turn — LLM path '
        'on the spark topology; 5s reads)', () {
      expect(HttpSessionApi.turnBudget, const Duration(seconds: 90));
      expect(HttpSessionApi.readBudget, const Duration(seconds: 5));
    });
  });
}
