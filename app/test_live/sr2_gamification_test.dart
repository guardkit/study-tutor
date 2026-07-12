// The S-R2 gamification contract body against the REAL adapter — invariants
// only (`exact:false`): a settled block is non-negative with a monotonic total,
// and the student-model read is data-gated. The exact-value pins stay on the
// fake (an LLM/engine is not canned). Outside the default `flutter test` tree;
// run with the test_live README's command (--concurrency=1 + API_BASE_URL).
@Timeout(Duration(minutes: 5))
library;

import 'package:flutter_test/flutter_test.dart';

import '../test/contract/sr2_gamification_test.dart';
import 'live_contract_backend.dart';

void main() => runGamificationTests(LiveContractBackend.new, exact: false);
