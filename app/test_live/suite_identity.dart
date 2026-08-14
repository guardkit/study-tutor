// The dedicated live-suite identity (server-queue item 1, 2026-08-04): a
// bearer resolving to student `suite-runner`, seeded in the deployed dev
// table so suite runs never touch a real learner's rows. `__dev__/reset`
// authenticates and deletes ONLY the caller's sessions, so a reset with
// these tokens can never repeat the 2026-08-03 whole-store wipe.
import 'dart:async';

import 'package:http/http.dart' as http;
import 'package:study_tutor_app/domain/principal.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';

/// The suite's own principal — NEVER a real learner.
///
/// Supplied at run time (`--dart-define=SUITE_TOKEN=…`) alongside
/// `API_BASE_URL`, for the same reason the app's own bearer is
/// (see [FakeIdentityProvider]): this repo is public. The default is a
/// non-credential, so a live run without the define fails auth loudly
/// instead of quietly authenticating as whoever the literal used to name.
const suitePrincipal = Principal(
  token: String.fromEnvironment(
    'SUITE_TOKEN',
    defaultValue: 'fake-bearer-suite-not-a-credential',
  ),
  displayName: 'Suite Runner',
);

/// The student id the server derives from [suitePrincipal]'s token.
const suiteStudentId = 'suite-runner';

/// Scoped, authenticated dev reset for one principal's rows.
Future<void> scopedReset(
  String apiBaseUrl,
  Principal principal, {
  Duration deadline = const Duration(seconds: 10),
}) async {
  final response = await http.post(
    Uri.parse('$apiBaseUrl/__dev__/reset'),
    headers: {'authorization': 'Bearer ${principal.token}'},
  ).timeout(deadline);
  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw StateError(
        'scoped dev reset failed: HTTP ${response.statusCode} — is the '
        'adapter deployed in dev config with ${principal.displayName}\'s '
        'token seeded?');
  }
}

/// End-of-file cleanup: clear the suite student's rows AND the second
/// principal's (the ownership tests create sessions as the dev-table
/// second student to prove forbidden access — those leftovers are junk on
/// its Home otherwise).
Future<void> cleanupSuiteSessions(String apiBaseUrl) async {
  if (apiBaseUrl.isEmpty) return;
  await scopedReset(apiBaseUrl, suitePrincipal);
  await scopedReset(apiBaseUrl, FakeIdentityProvider.secondStudent);
}
