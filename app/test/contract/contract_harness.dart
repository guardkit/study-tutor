// Shared harness for the contract suite (scope §4): one fake identity
// provider + one shared in-memory store, a deterministic ticking clock, and
// the ability to build a second client over the SAME store (the §4 second-
// device / per-turn-durability analogue).
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';

class ContractHarness {
  ContractHarness() {
    api = FakeSessionApi(identity: identity, store: store, clock: tick);
  }

  final identity = FakeIdentityProvider();
  final store = InMemorySessionStore();
  late final FakeSessionApi api;

  DateTime _now = DateTime.utc(2026, 7, 4, 0, 0, 0);

  /// Deterministic clock: every consult advances time by one second, so
  /// `last_activity` ordering is exact and tests never depend on wall time.
  DateTime tick() {
    _now = _now.add(const Duration(seconds: 1));
    return _now;
  }

  /// A second client object over the same store and identity — models a
  /// second device signed in as the same student (contract §3 pickup rule).
  FakeSessionApi secondClient() =>
      FakeSessionApi(identity: identity, store: store, clock: tick);
}
