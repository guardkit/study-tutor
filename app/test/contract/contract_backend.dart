// The contract suite's backend abstraction (phase-2 scope §3.4): one
// mechanism, two implementations. The suite drives identity switching, token
// invalidation, a second client, per-test reset, and timing/reply
// expectations THROUGH this interface, so the same 35 test bodies run
// against the in-memory fake (hermetic gate, `main()` in each file here) and
// — from p2-wave-6 — against the real HTTP adapter (`test_live/`, outside
// the default `flutter test` tree).
//
// This abstraction is for the contract suite only: unit/ui/errors/slice
// tests keep constructing fakes directly (build plan p2-wave-2).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/ports/session_api.dart';
import 'package:study_tutor_app/ports/student_model_api.dart';

abstract interface class ContractBackend {
  /// The device-under-test client. Sign-in state changes ([signIn],
  /// [signInSecondStudent], [invalidateCurrentToken]) affect subsequent
  /// calls through it — contract §3: the backend derives the caller from
  /// the token, never from a passed `student_id`.
  SessionApi get api;

  /// The student-model read client (S-A3), bound to the same principal as
  /// [api]. Fake: deterministic exact-value snapshot; live: real read, and the
  /// live suite asserts invariants only.
  StudentModelApi get studentModelApi;

  /// The `student_id` the backend derives from the default principal's
  /// token ('lilymay' in the fake; whatever the dev token table says live).
  String get defaultStudentId;

  /// Return the backend to empty state. Fake: rebuild the in-memory world.
  /// Live: the dev-only reset route from the binding doc — the isolation
  /// that lets tests assert absolute state (`hasLength(1)`, `isEmpty`).
  /// Every setUp calls this FIRST; after it the caller is signed out.
  ///
  /// Live caveat: the reset is GLOBAL server state shared by every suite
  /// file, so `test_live/` must run with `--concurrency=1` (wave-6's README
  /// owns the run command) — the default parallel isolates would clobber
  /// each other's state.
  Future<void> reset();

  /// Authenticate as the default student (Lilymay).
  Future<void> signIn();

  /// Principal switch: authenticate as the second student, for ownership
  /// tests. Live: a different entry in the dev token table.
  Future<void> signInSecondStudent();

  /// The stale-token shape: the backend stops accepting the current
  /// credential but the client still holds it — [hasLocalPrincipal] stays
  /// true and the next call earns `Unauthenticated`. Live: swap the sent
  /// token for garbage.
  void invalidateCurrentToken();

  /// True while the client side still holds a principal — what makes the
  /// invalidated-token state "stale" rather than "signed out".
  bool get hasLocalPrincipal;

  /// A second client over the SAME backend state and current principal —
  /// the §4 second-device / per-turn-durability analogue.
  SessionApi secondClient();

  /// Matcher for the tutor reply of the [turnIndex]-th turn (0-based) in a
  /// fresh session. The fake pins the exact canned string (determinism is
  /// what makes the contract tests exact — scope §2.3); a live backend can
  /// only promise a non-empty reply.
  Matcher expectedTutorReply(int turnIndex);

  /// Clock expectation (scope §3.4: relative ordering, no tick-clock
  /// exactness): matches a timestamp that advanced past [earlier] after
  /// intervening activity. The fake's ticking clock guarantees strict
  /// advancement; a live implementation may relax to at-or-after if server
  /// clock resolution demands it.
  Matcher advancedFrom(DateTime earlier);
}
