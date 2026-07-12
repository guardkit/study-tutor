/// The `StudentModelApi` port — the durable learner record read (S-A3).
///
/// Binds `GET /api/student-model` (API-session-http-binding.md §2.2 + §2.2.1
/// enrichment, consumed at BINDING_SHA
/// `53f2fc51a35aa051c3dd899563a5cdbb7b620061`). Additive read verb: it never
/// touches the six session verbs. Like [SessionApi], the caller is identified
/// by their token (§3), never by passing `student_id`; `subject` is the one
/// required query param.
///
/// Two adapters mirror the `composeSessionApi` triplet: [HttpStudentModelApi]
/// (real transport) and `FakeStudentModelApi` (deterministic reference). Both
/// are composed against the [IdentityProvider] INTERFACE (KC-D7-proofing) so
/// Keycloak can slot in behind the same seam.
///
/// May throw the §9 closed error set (see domain/errors.dart): `Unauthenticated`
/// on a missing/invalid token (ASSUM-001), `TransportError` for everything the
/// wire can do wrong outside that envelope.
library;

import '../domain/gamification.dart';

abstract interface class StudentModelApi {
  /// `GET /api/student-model?subject=<subject>` — the learner record for the
  /// authenticated student. Consumers gate on [StudentModel.dataAvailable].
  Future<StudentModel> fetch({required String subject});
}
