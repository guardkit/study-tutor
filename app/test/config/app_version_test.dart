/// Tests for the app version constant.
///
/// AC-002: asserts that the constant matches pubspec.yaml (the single source
/// of truth).  AC-004: widget test that the home screen renders the version.
library;

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/config/app_version.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/home_screen.dart';
import 'package:yaml/yaml.dart';

void main() {
  group('appVersion', () {
    test('matches pubspec.yaml version (pubspec is the single source of truth)',
        () {
      // Walk up from the current directory to find pubspec.yaml
      Directory? dir = Directory.current;
      File? pubspecFile;
      while (dir != null) {
        final candidate = File('${dir.path}/pubspec.yaml');
        if (candidate.existsSync()) {
          pubspecFile = candidate;
          break;
        }
        if (dir.path == dir.parent.path) break; // reached filesystem root
        dir = dir.parent;
      }
      expect(pubspecFile, isNotNull,
          reason: 'pubspec.yaml must be findable by walking up from test dir');
      final yaml =
          loadYaml(pubspecFile!.readAsStringSync()) as YamlMap;
      final pubspecVersion = yaml['version'] as String;
      expect(appVersion, pubspecVersion,
          reason:
              'appVersion must always match pubspec.yaml version to prevent drift');
    });
  });

  group('HomeScreen renders appVersion', () {
    late FakeIdentityProvider identity;
    late FakeSessionApi sessionApi;
    late FakeVoiceApi voiceApi;

    setUp(() async {
      identity = FakeIdentityProvider();
      await identity.signIn();
      sessionApi = FakeSessionApi(identity: identity);
      voiceApi = FakeVoiceApi();
    });

    Widget makeHome() {
      return MaterialApp(
        home: HomeScreen(
          identity: identity,
          sessionApi: sessionApi,
          voiceApi: voiceApi,
        ),
      );
    }

    testWidgets('shows the version as secondary text', (tester) async {
      await tester.pumpWidget(makeHome());
      await tester.pumpAndSettle();

      // The version should appear as a small text line like "v1.0.0+1"
      expect(find.textContaining(appVersion), findsOneWidget);
    });
  });
}
