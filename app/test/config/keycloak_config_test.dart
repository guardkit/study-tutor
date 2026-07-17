import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/config/keycloak_config.dart';

void main() {
  group('KeycloakConfig', () {
    test('constructs with issuer and clientId, frozen constants for redirectUrl and scopes', () {
      final config = KeycloakConfig(
        issuer: 'https://keycloak.example.com/realms/study-tutor',
        clientId: 'study-tutor-app',
      );

      expect(config.issuer, 'https://keycloak.example.com/realms/study-tutor');
      expect(config.clientId, 'study-tutor-app');
      expect(config.redirectUrl, 'com.appmilla.studytutor:/oauth2redirect');
      expect(config.scopes, ['openid', 'offline_access']);
    });

    test('has default clientId of study-tutor-app', () {
      final config = KeycloakConfig(
        issuer: 'https://keycloak.example.com/realms/study-tutor',
      );

      expect(config.clientId, 'study-tutor-app');
    });

    test('has frozen redirectUrl constant', () {
      final config = KeycloakConfig(
        issuer: 'https://keycloak.example.com/realms/study-tutor',
      );

      expect(config.redirectUrl, 'com.appmilla.studytutor:/oauth2redirect');
    });

    test('has frozen scopes constant [openid, offline_access]', () {
      final config = KeycloakConfig(
        issuer: 'https://keycloak.example.com/realms/study-tutor',
      );

      expect(config.scopes, ['openid', 'offline_access']);
    });

    test('supports empty issuer for hermetic-fake flavour', () {
      final config = KeycloakConfig(
        issuer: '',
      );

      expect(config.issuer, '');
      expect(config.clientId, 'study-tutor-app');
    });

    test('fromEnvironment reads KEYCLOAK_ISSUER', () {
      final config = KeycloakConfig.fromEnvironment({
        'KEYCLOAK_ISSUER': 'https://keycloak.example.com/realms/study-tutor',
      });

      expect(config.issuer, 'https://keycloak.example.com/realms/study-tutor');
    });

    test('fromEnvironment reads KEYCLOAK_CLIENT_ID', () {
      final config = KeycloakConfig.fromEnvironment({
        'KEYCLOAK_ISSUER': 'https://keycloak.example.com/realms/study-tutor',
        'KEYCLOAK_CLIENT_ID': 'custom-client-id',
      });

      expect(config.clientId, 'custom-client-id');
    });

    test('fromEnvironment defaults to empty issuer when not set', () {
      final config = KeycloakConfig.fromEnvironment({});

      expect(config.issuer, '');
    });

    test('fromEnvironment defaults clientId to study-tutor-app when not set', () {
      final config = KeycloakConfig.fromEnvironment({
        'KEYCLOAK_ISSUER': 'https://keycloak.example.com/realms/study-tutor',
      });

      expect(config.clientId, 'study-tutor-app');
    });

    test('equality compares all fields', () {
      final config1 = KeycloakConfig(
        issuer: 'https://keycloak.example.com/realms/study-tutor',
        clientId: 'study-tutor-app',
      );

      final config2 = KeycloakConfig(
        issuer: 'https://keycloak.example.com/realms/study-tutor',
        clientId: 'study-tutor-app',
      );

      expect(config1, config2);
    });

    test('hashCode is consistent with equality', () {
      final config1 = KeycloakConfig(
        issuer: 'https://keycloak.example.com/realms/study-tutor',
      );

      final config2 = KeycloakConfig(
        issuer: 'https://keycloak.example.com/realms/study-tutor',
      );

      expect(config1.hashCode, config2.hashCode);
    });

    test('toString includes all fields', () {
      final config = KeycloakConfig(
        issuer: 'https://keycloak.example.com/realms/study-tutor',
        clientId: 'study-tutor-app',
      );

      final str = config.toString();
      expect(str, contains('issuer'));
      expect(str, contains('clientId'));
      expect(str, contains('redirectUrl'));
      expect(str, contains('scopes'));
    });

    test('redirect scheme matches Android and iOS configuration', () {
      final config = KeycloakConfig(
        issuer: 'https://keycloak.example.com/realms/study-tutor',
      );

      // ASSUM-003: redirect URI must be byte-identical across:
      // - Keycloak client Valid Redirect URIs
      // - Android manifest scheme
      // - iOS CFBundleURLSchemes
      expect(config.redirectUrl, 'com.appmilla.studytutor:/oauth2redirect');

      // Verify scheme part matches native config
      expect(config.redirectUrl.startsWith('com.appmilla.studytutor:'), isTrue);
    });
  });
}
