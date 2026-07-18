/// SecureSessionStore — flutter_secure_storage-backed token-response persistence.
///
/// The persistence seam that keeps the family device signed in across restarts.
/// Wraps flutter_secure_storage and holds exactly the fields the adapter needs
/// to silently refresh: refresh token (offline_access), access token, and expiry.
///
/// Producer of the §4 STORED_SESSION contract (consumed by TASK-KCA3-003).
library;

import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Stored session data — library-agnostic value object.
/// No flutter_appauth types leak across this seam.
class StoredSession {
  const StoredSession({
    required this.refreshToken,
    required this.accessToken,
    required this.accessTokenExpiry,
    required this.displayName,
  });

  final String refreshToken;
  final String accessToken;
  final DateTime accessTokenExpiry;
  final String displayName;

  /// Deserialize from JSON. Throws if required fields are missing or malformed.
  factory StoredSession.fromJson(Map<String, dynamic> json) {
    return StoredSession(
      refreshToken: json['refreshToken'] as String,
      accessToken: json['accessToken'] as String,
      accessTokenExpiry: DateTime.parse(json['accessTokenExpiry'] as String),
      displayName: json['displayName'] as String,
    );
  }

  /// Serialize to JSON for persistence.
  Map<String, dynamic> toJson() => {
        'refreshToken': refreshToken,
        'accessToken': accessToken,
        'accessTokenExpiry': accessTokenExpiry.toIso8601String(),
        'displayName': displayName,
      };
}

/// SecureSessionStore — storage-shaped API over flutter_secure_storage.
///
/// Fail-closed design: any read error (missing key, corrupt blob, platform throw)
/// returns null, treating the device as signed out. Never propagates exceptions
/// from the backing store.
class SecureSessionStore {
  SecureSessionStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;
  static const _key = 'session';

  /// Read the persisted session. Returns null when:
  /// - The key is absent
  /// - The blob is unreadable/corrupt
  /// - The backing store throws
  ///
  /// Never propagates exceptions (fail-closed to signed-out).
  Future<StoredSession?> read() async {
    try {
      final blob = await _storage.read(key: _key);
      if (blob == null) return null;

      final json = jsonDecode(blob) as Map<String, dynamic>;
      return StoredSession.fromJson(json);
    } catch (e) {
      // Unreadable/corrupt blob or platform error → treat as absent.
      // This serves: "An unreadable stored session is treated as signed out"
      return null;
    }
  }

  /// Persist the session under a single key.
  Future<void> write(StoredSession session) async {
    final blob = jsonEncode(session.toJson());
    await _storage.write(key: _key, value: blob);
  }

  /// Remove the persisted session.
  Future<void> clear() async {
    await _storage.delete(key: _key);
  }
}
