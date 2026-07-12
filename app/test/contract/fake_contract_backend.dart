// The fake ContractBackend — reproduces the v1 harness exactly (one fake
// identity provider + one shared in-memory store + a deterministic ticking
// clock + secondClient() over the same store), behind the phase-2
// abstraction so the same test bodies also run live (p2-wave-6).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_student_model_api.dart';
import 'package:study_tutor_app/ports/session_api.dart';
import 'package:study_tutor_app/ports/student_model_api.dart';

import 'contract_backend.dart';

class FakeContractBackend implements ContractBackend {
  FakeContractBackend() {
    _build();
  }

  late FakeIdentityProvider _identity;
  late InMemorySessionStore _store;
  late FakeSessionApi _api;
  late FakeStudentModelApi _studentModelApi;
  late DateTime _now;

  void _build() {
    _identity = FakeIdentityProvider();
    _store = InMemorySessionStore();
    _now = DateTime.utc(2026, 7, 4, 0, 0, 0);
    _api = FakeSessionApi(identity: _identity, store: _store, clock: _tick);
    _studentModelApi = FakeStudentModelApi(identity: _identity);
  }

  /// Deterministic clock: every consult advances time by one second, so
  /// `last_activity` ordering is exact and tests never depend on wall time.
  DateTime _tick() {
    _now = _now.add(const Duration(seconds: 1));
    return _now;
  }

  @override
  SessionApi get api => _api;

  @override
  StudentModelApi get studentModelApi => _studentModelApi;

  @override
  String get defaultStudentId => 'lilymay';

  /// Rebuild the in-memory world — the hermetic analogue of the live dev
  /// reset route. Constructor state is already fresh; calling this in every
  /// setUp keeps the suite honest about needing per-test isolation.
  @override
  Future<void> reset() async => _build();

  @override
  Future<void> signIn() => _identity.signIn().then((_) {});

  @override
  Future<void> signInSecondStudent() =>
      _identity.signInAs(FakeIdentityProvider.secondStudent).then((_) {});

  @override
  void invalidateCurrentToken() => _identity.invalidateCurrentToken();

  @override
  bool get hasLocalPrincipal => _identity.currentPrincipal != null;

  /// A second client object over the same store and identity — models a
  /// second device signed in as the same student (contract §3 pickup rule).
  @override
  SessionApi secondClient() =>
      FakeSessionApi(identity: _identity, store: _store, clock: _tick);

  /// The fake pins the exact canned reply — scope §2.3: determinism is what
  /// makes the contract tests exact.
  @override
  Matcher expectedTutorReply(int turnIndex) => equals(FakeSessionApi
      .cannedReplies[turnIndex % FakeSessionApi.cannedReplies.length]);

  /// The ticking clock consults once per timestamped operation, so any
  /// intervening activity strictly advances time.
  @override
  Matcher advancedFrom(DateTime earlier) => predicate<DateTime>(
      (t) => t.isAfter(earlier), 'a DateTime strictly after $earlier');
}
