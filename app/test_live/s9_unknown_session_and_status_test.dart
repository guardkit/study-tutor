// Live run of the shared contract suite body (see test_live/README.md for
// the required run command — API_BASE_URL + --concurrency=1).
@Timeout(Duration(minutes: 10))
library;

import 'package:flutter_test/flutter_test.dart';

import '../test/contract/s9_unknown_session_and_status_test.dart' show runUnknownSessionAndStatusTests;
import 'live_contract_backend.dart';

void main() => runUnknownSessionAndStatusTests(LiveContractBackend.new);
