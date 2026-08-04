// The dedicated live-suite identity (server-queue item 1, 2026-08-04):
// token `token-suite` → student `suite-runner`, seeded in the deployed dev
// table so suite runs never touch a real learner's rows. `__dev__/reset`
// authenticates and deletes ONLY the caller's sessions, so a reset with
// these tokens can never repeat the 2026-08-03 whole-store wipe.
import 'dart:async';

import 'package:http/http.dart' as http;
import 'package:study_tutor_app/domain/principal.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';

/// The suite's own principal — NEVER a real learner.
const suitePrincipal = Principal(
  token: 'token-suite',
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
