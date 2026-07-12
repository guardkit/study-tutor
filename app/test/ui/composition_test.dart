// p2-wave-5: the composition rule (scope §3.3). The hermetic gate runs with
// API_BASE_URL unset, so the composed backend MUST be the fake — this test
// is what makes "the hermetic gate never sees a socket" an assertion rather
// than a convention. The set-flavour half is a pure type assertion (no
// request is ever sent).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/adapters/http_session_api.dart';
import 'package:study_tutor_app/adapters/http_voice_api.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/main.dart';
import 'package:study_tutor_app/ui/app.dart';

void main() {
  test('the define is unset in every hermetic run', () {
    expect(apiBaseUrl, isEmpty,
        reason: 'the gate must never run against a configured backend');
  });

  test('empty base URL composes the fake; set composes the HTTP adapter',
      () {
    final identity = FakeIdentityProvider();
    expect(composeSessionApi('', identity), isA<FakeSessionApi>());
    expect(composeSessionApi('http://10.0.2.2:8100', identity),
        isA<HttpSessionApi>());
    expect(composeVoiceApi('', identity), isA<FakeVoiceApi>());
    expect(composeVoiceApi('http://10.0.2.2:8100', identity),
        isA<HttpVoiceApi>());
  });

  testWidgets('the default composition boots and works end-to-end on the '
      'fake (v1 behaviour untouched)', (tester) async {
    final identity = FakeIdentityProvider();
    final sessionApi = composeSessionApi(apiBaseUrl, identity);
    final voiceApi = composeVoiceApi(apiBaseUrl, identity);
    expect(sessionApi, isA<FakeSessionApi>());
    expect(voiceApi, isA<FakeVoiceApi>());

    await tester.pumpWidget(StudyTutorApp(
      identity: identity,
      sessionApi: sessionApi,
      voiceApi: voiceApi,
    ));
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    expect(find.text('English'), findsOneWidget);
  });
}
