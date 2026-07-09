// Voice runtime configuration tests (TASK-VC-001)
//
// INVARIANT SCOPE: These tests verify that voice runtime dependencies and
// platform permissions remain properly configured. They assert LASTING
// requirements that will remain true across all voice-related tasks:
//
// - Dependencies: record, just_audio, web_socket_channel must be present
//   (no tasks in this feature will remove them)
// - Android: INTERNET and RECORD_AUDIO permissions must be declared in main
//   manifest (required for all voice operations)
// - iOS: NSMicrophoneUsageDescription must be present (required for App Store)
// - Network security: main manifest must reference network_security_config
//   (posture hygiene, affects native plugins like web_socket_channel)
//
// These are NOT point-in-time snapshots - they verify the foundation that
// all subsequent voice tasks (VC-002+) will build upon.

import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:yaml/yaml.dart';

void main() {
  group('Voice Runtime Dependencies', () {
    test('pubspec.yaml contains required voice dependencies', () {
      final pubspecFile = File('pubspec.yaml');
      expect(pubspecFile.existsSync(), isTrue,
          reason: 'pubspec.yaml must exist');

      final pubspecContent = pubspecFile.readAsStringSync();
      final pubspec = loadYaml(pubspecContent) as YamlMap;
      final dependencies = pubspec['dependencies'] as YamlMap;

      // INVARIANT: Voice runtime dependencies must be present
      // (no future task in this feature will remove them)
      expect(dependencies.containsKey('record'), isTrue,
          reason: 'record package required for audio recording');
      expect(dependencies.containsKey('just_audio'), isTrue,
          reason: 'just_audio package required for TTS playback');
      expect(dependencies.containsKey('web_socket_channel'), isTrue,
          reason: 'web_socket_channel required for voice streaming');
    });
  });

  group('Android Permissions', () {
    test('main manifest contains INTERNET permission', () {
      final manifestFile =
          File('android/app/src/main/AndroidManifest.xml');
      expect(manifestFile.existsSync(), isTrue,
          reason: 'Main AndroidManifest.xml must exist');

      final manifestContent = manifestFile.readAsStringSync();

      // INVARIANT: INTERNET permission required for WebSocket transport
      // and backend API calls (will remain true for all voice tasks)
      expect(manifestContent,
          contains('android.permission.INTERNET'),
          reason: 'INTERNET permission required in main manifest');
    });

    test('main manifest contains RECORD_AUDIO permission', () {
      final manifestFile =
          File('android/app/src/main/AndroidManifest.xml');
      expect(manifestFile.existsSync(), isTrue);

      final manifestContent = manifestFile.readAsStringSync();

      // INVARIANT: RECORD_AUDIO permission required for microphone access
      // (no task will remove this - it's fundamental to voice mode)
      expect(manifestContent,
          contains('android.permission.RECORD_AUDIO'),
          reason: 'RECORD_AUDIO permission required for voice input');
    });

    test('main manifest references network_security_config', () {
      final manifestFile =
          File('android/app/src/main/AndroidManifest.xml');
      expect(manifestFile.existsSync(), isTrue);

      final manifestContent = manifestFile.readAsStringSync();

      // INVARIANT: Network security config reference must be present for
      // posture hygiene (affects native plugins like web_socket_channel)
      expect(manifestContent,
          contains('android:networkSecurityConfig="@xml/network_security_config"'),
          reason: 'network_security_config reference required for security posture');
    });

    test('main network_security_config.xml exists and is restrictive', () {
      final nscFile =
          File('android/app/src/main/res/xml/network_security_config.xml');
      expect(nscFile.existsSync(), isTrue,
          reason: 'Main network_security_config.xml must exist');

      final nscContent = nscFile.readAsStringSync();

      // INVARIANT: Main config must NOT permit cleartext traffic
      // (production builds must use HTTPS only)
      expect(nscContent,
          contains('cleartextTrafficPermitted="false"'),
          reason: 'Main config must not permit cleartext traffic');

      // INVARIANT: Must NOT use usesCleartextTraffic (broad, unrestricted)
      // (per AC-004: NSC extension for hygiene only, not usesCleartextTraffic)
      expect(nscContent,
          isNot(contains('usesCleartextTraffic')),
          reason: 'usesCleartextTraffic must not be used (AC-004)');
    });
  });

  group('iOS Permissions', () {
    test('Info.plist contains NSMicrophoneUsageDescription', () {
      final infoPlistFile = File('ios/Runner/Info.plist');
      expect(infoPlistFile.existsSync(), isTrue,
          reason: 'iOS Info.plist must exist');

      final infoPlistContent = infoPlistFile.readAsStringSync();

      // INVARIANT: NSMicrophoneUsageDescription required for App Store
      // (no task will remove this - it's required for iOS microphone access)
      expect(infoPlistContent,
          contains('<key>NSMicrophoneUsageDescription</key>'),
          reason: 'NSMicrophoneUsageDescription required for iOS mic access');

      // Ensure it has a user-facing description (not empty)
      final lines = infoPlistContent.split('\n');
      final keyIndex = lines.indexWhere(
          (line) => line.contains('<key>NSMicrophoneUsageDescription</key>'));
      expect(keyIndex, greaterThan(-1));

      // The value should be in the next line (or nearby)
      final valueIndex = keyIndex + 1;
      expect(valueIndex, lessThan(lines.length));
      expect(lines[valueIndex], contains('<string>'),
          reason: 'NSMicrophoneUsageDescription must have a value');
      expect(lines[valueIndex].length, greaterThan(20),
          reason: 'Description should be user-facing, not empty');
    });
  });
}
