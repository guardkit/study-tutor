// Live run of the shared contract suite body (see test_live/README.md for
// the required run command — API_BASE_URL + --concurrency=1).
@Timeout(Duration(minutes: 5))
library;

import 'package:flutter_test/flutter_test.dart';

import '../test/contract/s3_s9_authentication_test.dart' show runAuthenticationTests;
import 'live_contract_backend.dart';

void main() => runAuthenticationTests(LiveContractBackend.new);
