// Hermetic tests for SecureSessionStore — no platform channel, only fakes.
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:study_tutor_app/adapters/secure_session_store.dart';

void main() {
  group('SecureSessionStore', () {
    late FakeSecureStorage fakeStorage;
    late SecureSessionStore store;

    setUp(() {
      fakeStorage = FakeSecureStorage();
      store = SecureSessionStore(storage: fakeStorage);
    });

    test('write/read round-trips a StoredSession', () async {
      final session = StoredSession(
        refreshToken: 'refresh_abc123',
        accessToken: 'access_xyz789',
        accessTokenExpiry: DateTime.utc(2026, 12, 31, 23, 59),
        displayName: 'Lilymay',
      );

      await store.write(session);
      final retrieved = await store.read();

      expect(retrieved, isNotNull);
      expect(retrieved!.refreshToken, 'refresh_abc123');
      expect(retrieved.accessToken, 'access_xyz789');
      expect(retrieved.accessTokenExpiry, DateTime.utc(2026, 12, 31, 23, 59));
      expect(retrieved.displayName, 'Lilymay');
    });

    test('read() returns null when key is absent', () async {
      final result = await store.read();
      expect(result, isNull);
    });

    test('read() returns null for corrupt/undeserializable blob', () async {
      fakeStorage.data['session'] = 'not valid json';
      final result = await store.read();
      expect(result, isNull);
    });

    test('read() returns null when backing store throws', () async {
      fakeStorage.throwOnRead = true;
      final result = await store.read();
      expect(result, isNull);
    });

    test('clear() removes the persisted session', () async {
      final session = StoredSession(
        refreshToken: 'refresh_abc123',
        accessToken: 'access_xyz789',
        accessTokenExpiry: DateTime.utc(2026, 12, 31, 23, 59),
        displayName: 'Lilymay',
      );

      await store.write(session);
      expect(await store.read(), isNotNull);

      await store.clear();
      expect(await store.read(), isNull);
    });

    test('StoredSession serializes to JSON', () {
      final session = StoredSession(
        refreshToken: 'refresh_abc123',
        accessToken: 'access_xyz789',
        accessTokenExpiry: DateTime.utc(2026, 12, 31, 23, 59),
        displayName: 'Lilymay',
      );

      final json = session.toJson();
      expect(json['refreshToken'], 'refresh_abc123');
      expect(json['accessToken'], 'access_xyz789');
      expect(json['accessTokenExpiry'], '2026-12-31T23:59:00.000Z');
      expect(json['displayName'], 'Lilymay');
    });

    test('StoredSession deserializes from JSON', () {
      final json = {
        'refreshToken': 'refresh_abc123',
        'accessToken': 'access_xyz789',
        'accessTokenExpiry': '2026-12-31T23:59:00.000Z',
        'displayName': 'Lilymay',
      };

      final session = StoredSession.fromJson(json);
      expect(session.refreshToken, 'refresh_abc123');
      expect(session.accessToken, 'access_xyz789');
      expect(session.accessTokenExpiry, DateTime.utc(2026, 12, 31, 23, 59));
      expect(session.displayName, 'Lilymay');
    });
  });
}

/// Fake implementation of FlutterSecureStorage for hermetic testing.
/// No platform channel - all state is in-memory.
class FakeSecureStorage implements FlutterSecureStorage {
  final Map<String, String> data = {};
  bool throwOnRead = false;

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (throwOnRead) {
      throw Exception('Simulated read error');
    }
    return data[key];
  }

  @override
  Future<void> write({
    required String key,
    required String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value == null) {
      data.remove(key);
    } else {
      data[key] = value;
    }
  }

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    data.remove(key);
  }

  @override
  Future<void> deleteAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    data.clear();
  }

  @override
  Future<Map<String, String>> readAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    return Map.from(data);
  }

  @override
  Future<bool> containsKey({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    return data.containsKey(key);
  }

  // Stub implementations for FlutterSecureStorage interface members
  @override
  AndroidOptions get aOptions => AndroidOptions();

  @override
  IOSOptions get iOptions => IOSOptions();

  @override
  LinuxOptions get lOptions => LinuxOptions();

  @override
  MacOsOptions get mOptions => MacOsOptions();

  @override
  WindowsOptions get wOptions => WindowsOptions();

  @override
  WebOptions get webOptions => WebOptions();

  @override
  Future<bool?> isCupertinoProtectedDataAvailable() async => null;

  @override
  Stream<bool>? get onCupertinoProtectedDataAvailabilityChanged => null;

  @override
  void registerListener({
    required String key,
    required void Function(String?) listener,
  }) {}

  @override
  void unregisterListener({
    required String key,
    required void Function(String?) listener,
  }) {}

  @override
  void unregisterAllListenersForKey({required String key}) {}

  @override
  void unregisterAllListeners() {}
}
