// Live run of the shared contract suite body (see test_live/README.md for
// the required run command — API_BASE_URL + --concurrency=1).
@Timeout(Duration(minutes: 10))
library;

import 'package:flutter_test/flutter_test.dart';

import '../test/contract/s4_s6_append_only_transcript_test.dart' show runAppendOnlyTranscriptTests;
import 'live_contract_backend.dart';

void main() => runAppendOnlyTranscriptTests(LiveContractBackend.new);
