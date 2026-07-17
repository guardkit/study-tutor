// p2-wave-5: the composition rule (scope §3.3). The hermetic gate runs with
// API_BASE_URL unset, so the composed backend MUST be the fake — this test
// is what makes "the hermetic gate never sees a socket" an assertion rather
// than a convention. The set-flavour half is a pure type assertion (no
// request is ever sent).
//
// KC-D7 update: composition functions now accept the IdentityProvider port,
// not the concrete fake. Flavour selection keys on KEYCLOAK_ISSUER.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/adapters/http_session_api.dart';
import 'package:study_tutor_app/adapters/http_student_model_api.dart';
import 'package:study_tutor_app/adapters/http_voice_api.dart';
import 'package:study_tutor_app/adapters/keycloak_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_student_model_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ports/identity_provider.dart';
import 'package:study_tutor_app/main.dart';
import 'package:study_tutor_app/ui/app.dart';

void main() {
  test('the define is unset in every hermetic run', () {
    expect(apiBaseUrl, isEmpty,
        reason: 'the gate must never run against a configured backend');
  });

  test('composition functions accept IdentityProvider port, not concrete fake',
      () {
    // The de-typed signature: all three composition functions take the port
    final IdentityProvider identity = FakeIdentityProvider();
    expect(composeSessionApi('', identity), isA<FakeSessionApi>());
    expect(composeSessionApi('http://10.0.2.2:8100', identity),
        isA<HttpSessionApi>());
    expect(composeVoiceApi('', identity), isA<FakeVoiceApi>());
    expect(composeVoiceApi('http://10.0.2.2:8100', identity),
        isA<HttpVoiceApi>());
    expect(composeStudentModelApi('', identity), isA<FakeStudentModelApi>());
    expect(composeStudentModelApi('http://10.0.2.2:8100', identity),
        isA<HttpStudentModelApi>());
  });

  test('empty issuer ⇒ concrete FakeIdentityProvider (hermetic flavour)', () {
    final identity = composeIdentity(keycloakIssuer: '');
    expect(identity, isA<FakeIdentityProvider>(),
        reason: 'hermetic flavour keeps the concrete fake for studentIdForToken');
  });

  test('set issuer ⇒ KeycloakIdentityProvider built from KeycloakConfig', () {
    final identity = composeIdentity(
      keycloakIssuer: 'https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor',
    );
    expect(identity, isA<KeycloakIdentityProvider>(),
        reason: 'keycloak flavour wires the real adapter');
    // Contract: the adapter carries the SAME redirect the native config registers
    expect((identity as KeycloakIdentityProvider).config.redirectUrl,
        'com.appmilla.studytutor:/oauth2redirect');
  });

  testWidgets('the default composition boots and works end-to-end on the '
      'fake (v1 behaviour untouched)', (tester) async {
    final identity = FakeIdentityProvider();
    final sessionApi = composeSessionApi(apiBaseUrl, identity);
    final voiceApi = composeVoiceApi(apiBaseUrl, identity);
    final studentModelApi = composeStudentModelApi(apiBaseUrl, identity);
    expect(sessionApi, isA<FakeSessionApi>());
    expect(voiceApi, isA<FakeVoiceApi>());
    expect(studentModelApi, isA<FakeStudentModelApi>());

    await tester.pumpWidget(StudyTutorApp(
      identity: identity,
      sessionApi: sessionApi,
      voiceApi: voiceApi,
      studentModelApi: studentModelApi,
    ));
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    expect(find.text('English'), findsOneWidget);
  });
}
