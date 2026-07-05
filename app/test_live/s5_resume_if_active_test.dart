// Live run of the shared contract suite body (see test_live/README.md for
// the required run command — API_BASE_URL + --concurrency=1).
@Timeout(Duration(minutes: 5))
library;

import 'package:flutter_test/flutter_test.dart';

import '../test/contract/s5_resume_if_active_test.dart' show runResumeIfActiveTests;
import 'live_contract_backend.dart';

void main() => runResumeIfActiveTests(LiveContractBackend.new);
