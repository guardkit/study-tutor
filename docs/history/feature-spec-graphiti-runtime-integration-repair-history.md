
/feature-spec "Graphiti runtime integration repair — wire local LLM + embedder via llama-swap on GB10:9000 (no cloud APIs per DECISION-DF-001); load config from .guardkit/graphiti.yaml; mirror guardkit's canonical OpenAIGenericClient/OpenAIEmbedder pattern; re-seed Lilymay; run end-to-end MCP demo" \
  --context tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md \
  --context docs/research/ideas/phase-1-validation.md \
  --context src/study_tutor/knowledge/graphiti_client.py \
  --context src/study_tutor/knowledge/queries.py \
  --context src/study_tutor/knowledge/async_write.py \
  --context src/study_tutor/knowledge/student_model.py \
  --context src/study_tutor/knowledge/episodes.py \
  --context scripts/seed_student_model.py \
  --context tests/unit/knowledge/test_async_write.py \
  --context .guardkit/graphiti.yaml \
  --context ../guardkit/guardkit/knowledge/graphiti_client.py \
  --context ../guardkit/docs/research/dgx-spark/README.md \
  --context ../guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md \
  --context ../guardkit/docs/research/dgx-spark/llama-swap-config.yaml

  I'll execute the six-phase Propose-Review methodology for this feature spec. Starting with Phase 1: Context Gathering.

Bash Detect Python stack signal
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/pyproject.toml 2>/dev/null && echo "py: yes" || echo "py: no"

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/pyproject.toml
py: yes
Read TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
Read phase-1-validation.md
Read graphiti_client.py
Read queries.py
Read async_write.py
Read student_model.py
Read episodes.py
Read seed_student_model.py
Read test_async_write.py
Read graphiti.yaml
Read graphiti_client.py
I'll read the canonical guardkit client in segments and the dgx-spark research files.

Bash Locate key methods/classes in guardkit's canonical client
IN
grep -nE "def _build_llm_client|def _build_embedder|def _build_cross_encoder|class.*Config|def get_client|def _construct_graphiti|class GraphitiClient|@dataclass" /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py | head -60

OUT
134:@dataclass(frozen=True)
135:class GraphitiConfig:
245:class GraphitiClient:
571:    def _build_embedder(self):
593:    def _build_llm_client(self):
2198:class GraphitiClientFactory:
Read llama-swap-config.yaml
Bash File sizes
IN
wc -l /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/dgx-spark/README.md /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md

OUT
    2496 /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py
      86 /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/dgx-spark/README.md
     218 /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md
    2800 total
Read graphiti_client.py (lines 131-250)
Read graphiti_client.py (lines 561-680)
Read README.md
Bash List existing feature files
IN
find /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features -name "*.feature" 2>/dev/null | head -20; ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features 2>/dev/null

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/graphiti-student-model/graphiti-student-model.feature
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/deepagents-tutoring-loop/deepagents-tutoring-loop.feature
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/deterministic-session-planner/deterministic-session-planner.feature
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier.feature
conftest.py
deepagents-tutoring-loop
deterministic-session-planner
graphiti-student-model
primary-text-rag-and-quote-verifier
Read graphiti-student-model.feature

Context loaded: stack=python, 4 existing .feature files (study-tutor pattern is domain-language Gherkin with @task:<TASK-ID> tags), guardkit canonical client read (134-line GraphitiConfig dataclass, _build_llm_client at L593, _build_embedder at L571), DECISION-DF-001 confirmed (no cloud APIs on dark factory critical path), llama-swap on :9000 with qwen-graphiti + nomic-embed forever-loaded, current YAML active provider = ollama (laptop fallback)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: Graphiti Runtime Integration Repair
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature: Graphiti Runtime Integration Repair
  As the Study Tutor system
  I want the Graphiti client constructed with an explicitly wired local LLM and local embedder
  So that every entity-extraction round-trip stays on the local inference fleet — never the cloud —
  and the learner's profile, sessions, and misconceptions actually persist.

  Background:
    Given the canonical project configuration file ".guardkit/graphiti.yaml" exists at the repo root
    And the local inference fleet is reachable on its configured endpoint
    And the configured graph store is FalkorDB on the configured host
    And Lilymay is the single learner identity in scope
    And no cloud LLM or embedding provider is permitted on the runtime path (DECISION-DF-001)

━━ GROUP A: Key Examples (5 scenarios) ━━

  # Why: Root-cause fix — the broken state was that Graphiti was constructed with no LLM,
  #      no embedder, and no cross-encoder, silently defaulting all three to cloud clients.
  @task:TASK-PH2-GR-001
  @key-example @smoke @client-construction
  Scenario: Constructing the Graphiti client wires a local LLM and a local embedder explicitly
    Given the canonical configuration names a local LLM provider and a local embedding provider
    When the system constructs a Graphiti client
    Then the client should be wired with an explicit LLM speaking to the configured local endpoint
    And the client should be wired with an explicit embedder speaking to the configured local endpoint
    And no cloud-provider default should be reachable from the constructed client
    And a structured event recording the wired endpoints should be emitted

  # Why: Single source of truth — the YAML is the contract every appmilla repo shares.
  @task:TASK-PH2-GR-001
  @key-example @smoke @config-loader
  Scenario: The Graphiti client loads its connection, LLM, and embedder details from the canonical configuration file
    Given the canonical configuration file specifies a graph store host, an LLM provider with endpoint and model, and an embedding provider with endpoint and model
    When the system loads the runtime configuration
    Then the loaded configuration should expose the graph-store connection details
    And it should expose the LLM provider, endpoint, and model
    And it should expose the embedding provider, endpoint, and model
    And the seed script and the tutor-session entry points should both consume this loader rather than hand-constructing connection details

  # Why: This is the gate that closes G2 — the Phase 1 falsified item.
  @task:TASK-PH2-GR-001
  @key-example @smoke @seed-baseline
  Scenario: Running the baseline seed populates Lilymay's complete learner profile in the live graph store
    Given a freshly-cleared learner partition for Lilymay
    When the system runs the baseline seed
    Then every baseline entity (one student, two subjects, four texts, six assessment objectives, six topics, six initial topic confidences) should be persisted
    And the persisted student should carry the configured year group and target grade
    And re-running the seed should be a no-op that records "seeding skipped"

  # Why: Read path closes G3 — planner produces explainable plans against live state.
  @task:TASK-PH2-GR-001
  @key-example @read-path
  Scenario: After seeding, the learner's state can be retrieved end-to-end
    Given the baseline seed has completed for Lilymay
    When the system requests Lilymay's learner state
    Then her identity, year group, and target grade should be returned
    And her enrolled subjects should be returned
    And her per-topic confidence bands and percentages should be returned

  # Why: This is the gate that closes G4 / G5 / G6 / G13 — full demo loop runs end-to-end.
  @task:TASK-PH2-GR-001
  @key-example @smoke @end-to-end
  Scenario: Running a tutoring session end-to-end persists a session-completed episode visible to operators
    Given Lilymay's baseline is loaded
    When a tutor session is started, several tutor turns are exchanged, and the session is ended
    Then at least one Coach revision should have been observed during the turns
    And a session-completed episode should be persisted in Lilymay's learner partition
    And operators should be able to retrieve the session episode by group identifier

━━ GROUP B: Boundary Conditions (4 scenarios) ━━

  # Why: Just-inside boundary — the configured cap on extraction concurrency must not throttle the seed.
  @task:TASK-PH2-GR-001
  @boundary @seed-concurrency
  Scenario Outline: The seed completes within budget when extraction concurrency is at or below the configured cap
    Given the configured chunk-extraction concurrency is <cap>
    When the system runs the baseline seed
    Then the seed should complete and report every dispatched write as either succeeded or abandoned (never silently dropped)

    Examples:
      | cap |
      | 1   |
      | 4   |

  # Why: Idempotency — re-running the seed once a baseline already exists is the documented happy path.
  @task:TASK-PH2-GR-001
  @boundary @idempotency
  Scenario: Re-running the seed when a complete baseline already exists is idempotent
    Given Lilymay's baseline was previously seeded successfully
    When the system runs the baseline seed again
    Then no new write should be dispatched
    And a "seeding skipped" event should be recorded with reason "already seeded"

  # Why: Just-inside vs just-outside on the fire-and-forget shutdown boundary.
  @task:TASK-PH2-GR-001
  @boundary
  Scenario: In-flight writes complete inside the configured shutdown grace
    Given the system has dispatched a fire-and-forget write that takes slightly less than the configured shutdown grace
    When the system shuts down
    Then the in-flight write should complete and the shutdown should report zero abandoned writes

  # Why: Just-outside boundary — writes that exceed the budget are reported, not silently lost.
  @task:TASK-PH2-GR-001
  @boundary @negative
  Scenario: In-flight writes that exceed the shutdown grace are explicitly abandoned
    Given the system has dispatched a fire-and-forget write that takes longer than the configured shutdown grace
    When the system shuts down
    Then the shutdown should report the write as abandoned
    And a structured "write abandoned at shutdown" event should be emitted

━━ GROUP C: Negative Cases (4 scenarios) ━━

  # Why: DECISION-DF-001 is the load-bearing policy — the runtime must refuse cloud at config load, not at first call.
  @task:TASK-PH2-GR-001
  @negative @policy @decision-df-001
  Scenario Outline: Configuring a cloud LLM or embedding provider is rejected at configuration load
    Given the configuration names a cloud-hosted provider for <surface>
    When the system loads the runtime configuration
    Then the load should fail with an error citing "cloud LLM providers disabled per DECISION-DF-001"
    And no Graphiti client should be constructed

    Examples:
      | surface         |
      | LLM provider    |
      | embedding provider |

  # Why: Graceful degradation — when the local fleet is offline the client must not raise into callers.
  @task:TASK-PH2-GR-001
  @negative @degradation
  Scenario: An unreachable local inference endpoint surfaces a degraded client, not a thrown exception
    Given the configured local LLM endpoint is unreachable
    When the system constructs a Graphiti client
    Then the client should be reported as degraded with a structured event
    And callers requesting learner state should receive an empty learner state without exception

  # Why: AC-003 — the cross-encoder default would silently call a cloud reranker; runtime must refuse.
  @task:TASK-PH2-GR-001
  @negative @cross-encoder-guard @decision-df-001
  Scenario: A code path that would invoke the cross-encoder reranker is treated as a critical error
    Given a Graphiti client is constructed without an explicitly-wired cross-encoder
    When the system attempts an operation that would invoke the reranker
    Then the operation should be rejected as a critical error before any cloud call is made
    And a structured event indicating the reranker would have hit a cloud endpoint should be emitted

  # Why: Belt-and-braces — even if the wiring drifts, the wired path must never read the OPENAI_API_KEY env var.
  @task:TASK-PH2-GR-001
  @negative @policy @decision-df-001
  Scenario: The wired client construction never reads the OpenAI API key from the environment
    Given the OpenAI API key environment variable is set to a placeholder
    When the system constructs the Graphiti client and dispatches a baseline write
    Then the write should reach the local endpoint with the placeholder local-key
    And no inspection of the OpenAI API key environment variable should occur on the client construction path

━━ GROUP D: Edge Cases (5 scenarios) ━━

  # Why: The whole point of the loader pattern — provider swap is a YAML edit, not a code change.
  @task:TASK-PH2-GR-001
  @edge-case @config-swap
  Scenario: Switching the active LLM provider in the canonical configuration does not require a code change
    Given the configuration is currently set to the laptop fallback provider
    When the configuration is updated to the dedicated inference fleet provider and the system is restarted
    Then the Graphiti client should construct against the dedicated fleet endpoint without code modification
    And the structured "client ready" event should record the new endpoint

  # Why: Split-fleet is the live deployment shape — LLM on one host, embedder on another.
  @task:TASK-PH2-GR-001
  @edge-case @split-fleet
  Scenario: The LLM and the embedder may live on different endpoints
    Given the configuration names different endpoints for the LLM and the embedder
    When the system constructs the Graphiti client
    Then the LLM should be wired to its endpoint
    And the embedder should be wired to its endpoint independently

  # Why: Live-rate-limit handling — the local fleet 429s under burst; writes must surface as logged failures, not silent drops.
  @task:TASK-PH2-GR-001
  @edge-case @rate-limit
  Scenario: Local-inference rate-limiting is reported as a logged write failure, not a silent drop
    Given the local inference fleet rate-limits a burst of seed writes
    When the seed completes
    Then each rate-limited write should be recorded as a "write failed" structured event
    And the seed exit code should reflect any abandoned writes rather than reporting success

  # Why: Regression-prevention — the autobuild stayed green throughout Phase 1 because no test booted a real client.
  @task:TASK-PH2-GR-001
  @edge-case @regression @smoke
  Scenario: A graphiti library upgrade that drifts the LLM-client constructor surface is caught by the live smoke test
    Given the live-Graphiti smoke test is enabled
    When the smoke test runs
    Then the test should construct a real Graphiti instance using the wired LLM and embedder
    And the test should round-trip a single episode and read it back via the learner partition
    And any drift in the constructor surface should fail the smoke test loudly

  # Why: The repair is only complete once Phase 1's gate flips — this is the closure condition.
  @task:TASK-PH2-GR-001
  @edge-case @validation-gate
  Scenario: The Phase 1 validation gate flips its falsified items to "Held" once the runtime path is repaired
    Given the runtime integration repair has landed
    And the baseline seed has completed for Lilymay
    And an end-to-end demo session has been recorded
    When the Phase 1 validation document is updated
    Then items G2, G3, G4, G5, G6, and G13 should each move from "Falsified" to "Held"
    And inline live-run evidence should accompany each flipped item

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 18 scenarios across 4 groups (incl. 2 Scenario Outlines)
Inferred assumptions: 6 (will be resolved in Phase 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review each group
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each group, you may:

  [A] Accept  — include all scenarios in this group as-is
  [R] Reject  — exclude all scenarios in this group
  [M] Modify  — accept but specify changes (provide inline)
  [+] Add     — accept and add additional scenarios you describe
  [?] Defer   — mark group for future specification; excluded from output

Fast path: type "A A A A" to accept all four groups at once.

GROUP A — Key Examples (5 scenarios): _
GROUP B — Boundary Conditions (4 scenarios): _
GROUP C — Negative Cases (4 scenarios): _
GROUP D — Edge Cases (5 scenarios): _
Awaiting your curation decision per group. After Phase 3, I'll offer Phase 4 edge-case expansion (security, concurrency, integration boundaries) and then resolve the inferred assumptions in Phase 5 before writing the three output files to features/graphiti-runtime-integration-repair/.

command-history.md
A A A A
Curation recorded: all four groups accepted as-is.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've identified 6 additional scenarios covering security, concurrency,
and integration boundaries that the existing 18 scenarios don't yet
exercise:

Security (2):
  - Misconception text containing a coarse prompt-injection pattern is
    still sanitised before reaching the now-real local extraction LLM
    (the wired-up LLM is not a free pass — input sanitisation must hold)
  - The canonical configuration file containing a cloud-provider value
    cannot be silently overridden via a permissive environment variable

Concurrency (2):
  - A tutor session running concurrently with a seed re-run does not
    deadlock and does not silently drop either path's writes
  - Two simultaneous Graphiti client constructions against the same
    configuration share the loaded config rather than racing on parse

Integration boundaries (2):
  - A malformed (non-OpenAI-compatible) response from the local
    inference fleet surfaces as a logged write failure with a clear
    error class, not as a swallowed exception
  - A pre-existing FalkorDB vector index at a dimension that does not
    match the configured embedder produces a single explicit warning,
    not a silent retrieval-quality regression

[Y] Yes — show all 6 and curate them with the same A/R/M/+/? actions
[S] Sample — show 2 examples and decide
[N] No — skip and proceed to Phase 5

Your choice [Y/S/N]:
Awaiting your choice on the optional edge-case expansion.

Y

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION — full proposals (6 scenarios)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━ GROUP E: Security (2 scenarios) ━━

  # Why: Wiring up a real local LLM does not relax existing input-sanitisation guarantees;
  #      the extraction LLM is now a real call site, not a mock, so injection probes matter more.
  @task:TASK-PH2-GR-001
  @edge-case @security @sanitisation
  Scenario: Misconception text containing a prompt-injection pattern is dropped before the wired extraction LLM is invoked
    Given the Graphiti client has been constructed with the local LLM and embedder wired
    When the system attempts to record a misconception whose text matches a coarse prompt-injection pattern
    Then the write should be dropped before any call to the extraction LLM
    And a structured "write dropped (injection)" event should be emitted
    And no record of the misconception should appear in the learner's partition

  # Why: DECISION-DF-001 must hold even if an operator tries to back-door cloud config via the environment.
  @task:TASK-PH2-GR-001
  @edge-case @security @policy @decision-df-001
  Scenario: A cloud provider value cannot be silently introduced via an environment-variable override
    Given the canonical configuration file names a local provider for both LLM and embedding
    And an environment variable attempts to override the LLM provider with a cloud-hosted value
    When the system loads the runtime configuration
    Then the load should fail with the same DECISION-DF-001 policy error as a YAML-only cloud value
    And no Graphiti client should be constructed

━━ GROUP F: Concurrency (2 scenarios) ━━

  # Why: Real deployment will overlap a tutor session with operator re-runs of the seed; neither path can starve the other.
  @task:TASK-PH2-GR-001
  @edge-case @concurrency
  Scenario: A live tutor session running concurrently with a seed re-run completes without deadlock or silent drop
    Given a tutor session is in progress for Lilymay
    And the seed script is re-run against the same learner partition
    When both flows complete
    Then every dispatched write from each flow should be reported as either succeeded, failed, or abandoned
    And neither flow should observe a hang exceeding its own configured budget
    And the learner-state read after both complete should reflect every successful write from both flows

  # Why: The loader is consumed from multiple entry points (seed script + MCP handlers); a parse race must not duplicate work.
  @task:TASK-PH2-GR-001
  @edge-case @concurrency @config-loader
  Scenario: Two simultaneous Graphiti client constructions share the loaded configuration rather than racing on parse
    Given the canonical configuration file has not yet been loaded in this process
    When two callers request a Graphiti client simultaneously
    Then both callers should receive a client wired against the same configuration values
    And the configuration file should not produce two independent parses with diverging results

━━ GROUP G: Integration Boundaries (2 scenarios) ━━

  # Why: llama-swap is a young tool; an alias or upstream model returning a non-spec response must surface as a logged failure, not be swallowed.
  @task:TASK-PH2-GR-001
  @edge-case @integration-boundary
  Scenario: A malformed response from the local inference fleet surfaces as a logged write failure
    Given the local inference fleet returns a response that does not match the OpenAI-compatible contract
    When the system dispatches a baseline write through the wired Graphiti client
    Then the write should be recorded as a "write failed" structured event with a specific error class
    And the failure should not propagate as an unhandled exception to the caller
    And the seed exit code should reflect the failure rather than reporting success

  # Why: A pre-existing FalkorDB vector index at the wrong dimension would silently corrupt retrieval — the existing pre-flight must remain audible.
  @task:TASK-PH2-GR-001
  @edge-case @integration-boundary @embedding-dim
  Scenario: A pre-existing graph-store vector index at a dimension different from the configured embedder produces a single explicit warning
    Given the graph store has an existing vector index at one dimension
    And the configured embedder produces vectors at a different dimension
    When the Graphiti client is constructed
    Then a single structured warning should be emitted naming both dimensions and a remediation hint
    And the warning should appear at most once per client construction (not per write)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURATION: Review each expansion group

For each group, you may:

  [A] Accept  — include all scenarios in this group as-is
  [R] Reject  — exclude all scenarios in this group
  [M] Modify  — accept but specify changes (provide inline)
  [+] Add     — accept and add additional scenarios you describe
  [?] Defer   — mark group for future specification; excluded from output

Fast path: type "A A A" to accept all three expansion groups at once.

GROUP E — Security (2 scenarios): _
GROUP F — Concurrency (2 scenarios): _
GROUP G — Integration Boundaries (2 scenarios): _
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Awaiting your decision on the three expansion groups.

A A A
All expansion groups recorded. Moving to Phase 5.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSUMPTION RESOLUTION (6 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each assumption has a proposed default. Press Enter to accept, or
type the actual value. Confirmed values flow into the .feature file
as `# [ASSUMPTION: confidence=...]` comments above the affected step.

[1] Tutor-turn latency budget for the end-to-end demo (AC-007)
    AC-007 says "capture p50/p95 latency" but does not name a target.
    Without a target, the @end-to-end scenario can only assert "the
    session completes" — no slow-loop regression guard.
    Proposed: p50 ≤ 30s, p95 ≤ 90s per turn (laptop-ollama fallback;
              halve when GB10 vllm is active)
    Confidence: low  Basis: graphiti-latency-spike measured 78s/write;
                            tutor turns are LLM-bound by Player + Coach
    Accept or enter value: _

[2] Default behaviour when ".guardkit/graphiti.yaml" is missing or malformed
    AC-004 specifies the fields read but not the failure mode when the
    file is absent or unreadable. Three plausible defaults: raise loudly
    (refuse to start), degrade to None (graceful empty), or fall back to
    the existing GraphitiConnectionConfig defaults.
    Proposed: raise loudly with a clear "config file missing" error —
              seeding and tutor handlers cannot proceed without an
              explicit local-fleet configuration (DECISION-DF-001 forbids
              an "implicit cloud default" path)
    Confidence: medium  Basis: aligns with AC-001 fail-loud policy
    Accept or enter value: _

[3] Smoke-test latency budget — single add_episode + read round-trip (AC-005)
    AC-005 says the smoke test "fails loudly if construction skips the
    local-endpoint config" but does not name a wall-clock budget for the
    round-trip. Without one, a 600s hang would still pass.
    Proposed: 180 seconds for one episode + read on the laptop fallback;
              60 seconds when GB10 vllm is active
    Confidence: low  Basis: 2× the measured 78s/write median plus read
                            overhead
    Accept or enter value: _

[4] Seed pre-flight semantics on a partially-seeded baseline
    The current `_is_already_seeded` helper returns True if any of
    subjects / topic_confidences / year_group is present. A partial
    seed (e.g. 13 of 25 entities) would be treated as "already seeded"
    and the second 12 would never be written. The spec is silent on
    whether that is the intended idempotency semantics.
    Proposed: keep the current "any signal = already seeded" semantics
              for this repair task; flag partial-seed recovery as a
              follow-up rather than scope-creeping the repair
    Confidence: medium  Basis: matches existing `_is_already_seeded`
                               implementation; explicit recovery path
                               would broaden the task
    Accept or enter value: _

[5] Concurrent-construction loader semantics (Group F scenario 2)
    The "two simultaneous Graphiti client constructions share the
    loaded configuration" scenario can be satisfied by either:
    (a) a process-wide cached config (parsed once), or
    (b) two parses producing identical immutable values.
    Proposed: (b) two parses returning equivalent immutable
              GraphitiConnectionConfig values — no new caching layer
              is required for the repair task
    Confidence: medium  Basis: avoids introducing a singleton/cache;
                               YAGNI for this repair scope
    Accept or enter value: _

[6] "Burst of seed writes" rate-limit threshold (Group D rate-limit scenario)
    The risk-register notes guardkit's chunk_extraction_concurrency=4
    eliminated 429s in production. The scenario asserts rate-limited
    writes are logged, not silently dropped — but does not specify
    burst size to trigger the test.
    Proposed: a synthetic burst of 25 simultaneous writes (matches the
              full Lilymay seed footprint), validated against a fake
              client that returns "rate limited" for the second 21
    Confidence: low  Basis: the seed itself is the realistic worst case
    Accept or enter value: _
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Three of these (1, 3, 6) are low-confidence and will produce a REVIEW REQUIRED flag in the output summary unless you override with a stated value. Awaiting your resolutions.

ok let's review 1,3,6 so we can make an informed decision
Sure — here is the trade-off space for each, with what I think the right framing is. None of these need a final answer in this turn; happy to discuss before we lock them in.

[1] Tutor-turn latency budget
Current scenario asserts only: "the session completes" + "at least one Coach revision observed" + "session-completed episode persisted."

What AC-007 actually requires: "Capture turn p50/p95 latency in phase-1-validation.md." That's a measure-and-record instruction, not a pass/fail gate.

Three options

Option	Behaviour	Pro	Con
(a) No budget — record only	Scenario asserts that latency was measured + appended to phase-1-validation.md	Aligns precisely with AC-007 wording; avoids over-specifying a moving target (laptop vs GB10 differs ~3–5×)	No regression guard
(b) Hard budget (proposed: p50 ≤ 30s / p95 ≤ 90s)	Scenario fails if budget exceeded	Catches Player/Coach regressions early	Risk: budget is wrong for laptop-fallback or wrong for GB10; first run defines truth, not the spec
(c) Soft budget	Record + structured warning if exceeded, but don't fail	Middle ground	Adds spec complexity for marginal value
My read: this is a Phase-1-closure measurement task, not a perf-regression task. Option (a) matches the AC literally and avoids encoding a number we'd just have to revise once GB10 takes over. We can always add a budget in a follow-up once we have two data points (laptop + GB10).

Per-turn latency context: A turn is dominated by Player + Coach LLM calls (NOT by add_episode — that's fire-and-forget on F3). The 78s/write spike is a write-path number, irrelevant here. On 14B-Q4 local, individual model calls are typically 3–15s; a single turn with Player + Coach + possible revision is plausibly 10–45s. So if you do want a budget, p50 ≤ 30s / p95 ≤ 90s is roughly right for the laptop fallback — but I'd still prefer not to encode it.

[3] Smoke-test round-trip budget
What's at stake: this test gates on STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1 so it's opt-in (won't run in default CI). But every test needs some timeout — without one, a misconfigured local fleet hangs forever.

Two real questions

Should the budget be encoded in the spec or only in the test fixture?

The spec can say "the round-trip completes within budget" without naming the number — that's a normal Gherkin pattern.
The actual seconds belong in pytest.mark.timeout(...) or asyncio.wait_for(...).
Domain language argument: scenarios shouldn't carry implementation magic numbers.
What number to use in the fixture?

78s/write median is the documented baseline.
One write + one read ≈ 78s + a few hundred ms (reads are 0.07s per the latency spike).
180s on laptop fallback = 2× headroom — generous but defensible.
60s on GB10 = tight but achievable; vllm 14B-FP8 typically ~3–5× faster than ollama Q4_K_M.
My read: keep the budget out of the .feature file; mention it in the assumption manifest as an implementation hint for the smoke test. The scenario already says "the test should round-trip a single episode and read it back" — that's the contract; the seconds are mechanism. 180s laptop / 60s GB10 is my fixture-level proposal.

[6] Burst size for the rate-limit scenario
Re-reading my own scenario: the Gherkin doesn't name a number — it says "the local inference fleet rate-limits a burst of seed writes". The behavioural assertion is "each rate-limited write should be recorded as a 'write failed' event" and "the seed exit code should reflect any abandoned writes."

So what is this assumption actually for? It's only for the test author who constructs the fake client — they need to decide how many writes to dispatch and how many to mark as rate-limited. That's not a spec-level concern.

My read: drop this assumption entirely. The scenario is correct as drafted; whoever writes the step definitions can pick any burst that triggers the failure (5 writes, 25 writes, doesn't matter — the assertion is about what happens when rate-limiting occurs, not about when it occurs). If we want anchor numbers, we can mention the seed's 25-entity footprint in the assumption manifest as a hint, not an assumption.

Recommended set after this review
#	Original	Recommended action
1	Tutor-turn budget	Drop — change scenario to "latency was measured and recorded"
3	Smoke-test budget	Move out of spec — keep 180s laptop / 60s GB10 as a fixture hint in the assumptions manifest
6	Burst size	Drop — scenario doesn't need it; mention 25-entity seed footprint as an implementer hint
This would leave us with three remaining assumptions (2, 4, 5 from the original list — all medium confidence) and no REVIEW REQUIRED flag on the output.

Want me to proceed with the drops above, or hold any of them as explicit assumptions?

yes proceed with your recommendations
Locking in: drop 1/3/6 as discussed; accept 2, 4, 5 with their proposed medium-confidence defaults. Now writing the three output files.

Bash Create output directory for feature spec
IN
mkdir -p /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/graphiti-runtime-integration-repair

OUT
(Bash completed with no output)
Write graphiti-runtime-integration-repair.feature
294 lines
# Generated by /feature-spec
# Feature: Graphiti Runtime Integration Repair
# Stack: python
# Assumptions: 3 (see graphiti-runtime-integration-repair_assumptions.yaml)
# Generated: 2026-05-02

@phase-2 @task-ph2-gr-001 @graphiti-repair
Feature: Graphiti Runtime Integration Repair
  As the Study Tutor system
  I want the Graphiti client constructed with an explicitly wired local LLM and local embedder
  So that every entity-extraction round-trip stays on the local inference fleet — never the cloud —
  and the learner's profile, sessions, and misconceptions actually persist.

  Background:
    Given the canonical project configuration file ".guardkit/graphiti.yaml" exists at the repo root
    And the local inference fleet is reachable on its configured endpoint
    And the configured graph store is FalkorDB on the configured host
    And Lilymay is the single learner identity in scope
    And no cloud LLM or embedding provider is permitted on the runtime path (DECISION-DF-001)

  # ==========================================================================
  # GROUP A: Key Examples
  # ==========================================================================

  # Why: Root-cause fix — the broken state was that Graphiti was constructed with no LLM,
  #      no embedder, and no cross-encoder, silently defaulting all three to cloud clients.
  @task:TASK-PH2-GR-001
  @key-example @smoke @client-construction
  Scenario: Constructing the Graphiti client wires a local LLM and a local embedder explicitly
    Given the canonical configuration names a local LLM provider and a local embedding provider
    When the system constructs a Graphiti client
    Then the client should be wired with an explicit LLM speaking to the configured local endpoint
    And the client should be wired with an explicit embedder speaking to the configured local endpoint
    And no cloud-provider default should be reachable from the constructed client
    And a structured event recording the wired endpoints should be emitted

  # Why: Single source of truth — the YAML is the contract every appmilla repo shares.
  @task:TASK-PH2-GR-001
  @key-example @smoke @config-loader
  Scenario: The Graphiti client loads its connection, LLM, and embedder details from the canonical configuration file
    Given the canonical configuration file specifies a graph store host, an LLM provider with endpoint and model, and an embedding provider with endpoint and model
    When the system loads the runtime configuration
    Then the loaded configuration should expose the graph-store connection details
    And it should expose the LLM provider, endpoint, and model
    And it should expose the embedding provider, endpoint, and model
    And the seed script and the tutor-session entry points should both consume this loader rather than hand-constructing connection details

  # Why: This is the gate that closes G2 — the Phase 1 falsified item.
  @task:TASK-PH2-GR-001
  @key-example @smoke @seed-baseline
  Scenario: Running the baseline seed populates Lilymay's complete learner profile in the live graph store
    Given a freshly-cleared learner partition for Lilymay
    When the system runs the baseline seed
    Then every baseline entity (one student, two subjects, four texts, six assessment objectives, six topics, six initial topic confidences) should be persisted
    And the persisted student should carry the configured year group and target grade
    And re-running the seed should be a no-op that records "seeding skipped"

  # Why: Read path closes G3 — planner produces explainable plans against live state.
  @task:TASK-PH2-GR-001
  @key-example @read-path
  Scenario: After seeding, the learner's state can be retrieved end-to-end
    Given the baseline seed has completed for Lilymay
    When the system requests Lilymay's learner state
    Then her identity, year group, and target grade should be returned
    And her enrolled subjects should be returned
    And her per-topic confidence bands and percentages should be returned

  # Why: This is the gate that closes G4 / G5 / G6 / G13 — full demo loop runs end-to-end.
  @task:TASK-PH2-GR-001
  @key-example @smoke @end-to-end
  Scenario: Running a tutoring session end-to-end persists a session-completed episode visible to operators
    Given Lilymay's baseline is loaded
    When a tutor session is started, several tutor turns are exchanged, and the session is ended
    Then at least one Coach revision should have been observed during the turns
    And a session-completed episode should be persisted in Lilymay's learner partition
    And operators should be able to retrieve the session episode by group identifier
    And per-turn p50 and p95 latency should be recorded in the Phase 1 validation document

  # ==========================================================================
  # GROUP B: Boundary Conditions
  # ==========================================================================

  # Why: Just-inside boundary — the configured cap on extraction concurrency must not throttle the seed.
  @task:TASK-PH2-GR-001
  @boundary @seed-concurrency
  Scenario Outline: The seed completes within budget when extraction concurrency is at or below the configured cap
    Given the configured chunk-extraction concurrency is <cap>
    When the system runs the baseline seed
    Then the seed should complete and report every dispatched write as either succeeded or abandoned (never silently dropped)

    Examples:
      | cap |
      | 1   |
      | 4   |

  # Why: Idempotency — re-running the seed once a baseline already exists is the documented happy path.
  # [ASSUMPTION: confidence=medium] Pre-flight idempotency treats any baseline signal (subjects, topic confidences, or year_group) as "already seeded"; partial-seed recovery is a follow-up, not in scope here.
  @task:TASK-PH2-GR-001
  @boundary @idempotency
  Scenario: Re-running the seed when a complete baseline already exists is idempotent
    Given Lilymay's baseline was previously seeded successfully
    When the system runs the baseline seed again
    Then no new write should be dispatched
    And a "seeding skipped" event should be recorded with reason "already seeded"

  # Why: Just-inside vs just-outside on the fire-and-forget shutdown boundary.
  @task:TASK-PH2-GR-001
  @boundary
  Scenario: In-flight writes complete inside the configured shutdown grace
    Given the system has dispatched a fire-and-forget write that takes slightly less than the configured shutdown grace
    When the system shuts down
    Then the in-flight write should complete and the shutdown should report zero abandoned writes

  # Why: Just-outside boundary — writes that exceed the budget are reported, not silently lost.
  @task:TASK-PH2-GR-001
  @boundary @negative
  Scenario: In-flight writes that exceed the shutdown grace are explicitly abandoned
    Given the system has dispatched a fire-and-forget write that takes longer than the configured shutdown grace
    When the system shuts down
    Then the shutdown should report the write as abandoned
    And a structured "write abandoned at shutdown" event should be emitted

  # ==========================================================================
  # GROUP C: Negative Cases
  # ==========================================================================

  # Why: DECISION-DF-001 is the load-bearing policy — the runtime must refuse cloud at config load, not at first call.
  @task:TASK-PH2-GR-001
  @negative @policy @decision-df-001
  Scenario Outline: Configuring a cloud LLM or embedding provider is rejected at configuration load
    Given the configuration names a cloud-hosted provider for <surface>
    When the system loads the runtime configuration
    Then the load should fail with an error citing "cloud LLM providers disabled per DECISION-DF-001"
    And no Graphiti client should be constructed

    Examples:
      | surface            |
      | LLM provider       |
      | embedding provider |

  # Why: Graceful degradation — when the local fleet is offline the client must not raise into callers.
  @task:TASK-PH2-GR-001
  @negative @degradation
  Scenario: An unreachable local inference endpoint surfaces a degraded client, not a thrown exception
    Given the configured local LLM endpoint is unreachable
    When the system constructs a Graphiti client
    Then the client should be reported as degraded with a structured event
    And callers requesting learner state should receive an empty learner state without exception

  # Why: AC-003 — the cross-encoder default would silently call a cloud reranker; runtime must refuse.
  @task:TASK-PH2-GR-001
  @negative @cross-encoder-guard @decision-df-001
  Scenario: A code path that would invoke the cross-encoder reranker is treated as a critical error
    Given a Graphiti client is constructed without an explicitly-wired cross-encoder
    When the system attempts an operation that would invoke the reranker
    Then the operation should be rejected as a critical error before any cloud call is made
    And a structured event indicating the reranker would have hit a cloud endpoint should be emitted

  # Why: Belt-and-braces — even if the wiring drifts, the wired path must never read the OPENAI_API_KEY env var.
  @task:TASK-PH2-GR-001
  @negative @policy @decision-df-001
  Scenario: The wired client construction never reads the OpenAI API key from the environment
    Given the OpenAI API key environment variable is set to a placeholder
    When the system constructs the Graphiti client and dispatches a baseline write
    Then the write should reach the local endpoint with the placeholder local-key
    And no inspection of the OpenAI API key environment variable should occur on the client construction path

  # ==========================================================================
  # GROUP D: Edge Cases
  # ==========================================================================

  # Why: The whole point of the loader pattern — provider swap is a YAML edit, not a code change.
  @task:TASK-PH2-GR-001
  @edge-case @config-swap
  Scenario: Switching the active LLM provider in the canonical configuration does not require a code change
    Given the configuration is currently set to the laptop fallback provider
    When the configuration is updated to the dedicated inference fleet provider and the system is restarted
    Then the Graphiti client should construct against the dedicated fleet endpoint without code modification
    And the structured "client ready" event should record the new endpoint

  # Why: Split-fleet is the live deployment shape — LLM on one host, embedder on another.
  @task:TASK-PH2-GR-001
  @edge-case @split-fleet
  Scenario: The LLM and the embedder may live on different endpoints
    Given the configuration names different endpoints for the LLM and the embedder
    When the system constructs the Graphiti client
    Then the LLM should be wired to its endpoint
    And the embedder should be wired to its endpoint independently

  # Why: Live-rate-limit handling — the local fleet 429s under burst; writes must surface as logged failures, not silent drops.
  @task:TASK-PH2-GR-001
  @edge-case @rate-limit
  Scenario: Local-inference rate-limiting is reported as a logged write failure, not a silent drop
    Given the local inference fleet rate-limits a burst of seed writes
    When the seed completes
    Then each rate-limited write should be recorded as a "write failed" structured event
    And the seed exit code should reflect any abandoned writes rather than reporting success

  # Why: Regression-prevention — the autobuild stayed green throughout Phase 1 because no test booted a real client.
  @task:TASK-PH2-GR-001
  @edge-case @regression @smoke
  Scenario: A graphiti library upgrade that drifts the LLM-client constructor surface is caught by the live smoke test
    Given the live-Graphiti smoke test is enabled
    When the smoke test runs
    Then the test should construct a real Graphiti instance using the wired LLM and embedder
    And the test should round-trip a single episode and read it back via the learner partition
    And any drift in the constructor surface should fail the smoke test loudly

  # Why: The repair is only complete once Phase 1's gate flips — this is the closure condition.
  @task:TASK-PH2-GR-001
  @edge-case @validation-gate
  Scenario: The Phase 1 validation gate flips its falsified items to "Held" once the runtime path is repaired
    Given the runtime integration repair has landed
    And the baseline seed has completed for Lilymay
    And an end-to-end demo session has been recorded
    When the Phase 1 validation document is updated
    Then items G2, G3, G4, G5, G6, and G13 should each move from "Falsified" to "Held"
    And inline live-run evidence should accompany each flipped item

  # ==========================================================================
  # GROUP E: Security
  # ==========================================================================

  # Why: Wiring up a real local LLM does not relax existing input-sanitisation guarantees;
  #      the extraction LLM is now a real call site, not a mock, so injection probes matter more.
  @task:TASK-PH2-GR-001
  @edge-case @security @sanitisation
  Scenario: Misconception text containing a prompt-injection pattern is dropped before the wired extraction LLM is invoked
    Given the Graphiti client has been constructed with the local LLM and embedder wired
    When the system attempts to record a misconception whose text matches a coarse prompt-injection pattern
    Then the write should be dropped before any call to the extraction LLM
    And a structured "write dropped (injection)" event should be emitted
    And no record of the misconception should appear in the learner's partition

  # Why: DECISION-DF-001 must hold even if an operator tries to back-door cloud config via the environment.
  @task:TASK-PH2-GR-001
  @edge-case @security @policy @decision-df-001
  Scenario: A cloud provider value cannot be silently introduced via an environment-variable override
    Given the canonical configuration file names a local provider for both LLM and embedding
    And an environment variable attempts to override the LLM provider with a cloud-hosted value
    When the system loads the runtime configuration
    Then the load should fail with the same DECISION-DF-001 policy error as a YAML-only cloud value
    And no Graphiti client should be constructed

  # ==========================================================================
  # GROUP F: Concurrency
  # ==========================================================================

  # Why: Real deployment will overlap a tutor session with operator re-runs of the seed; neither path can starve the other.
  @task:TASK-PH2-GR-001
  @edge-case @concurrency
  Scenario: A live tutor session running concurrently with a seed re-run completes without deadlock or silent drop
    Given a tutor session is in progress for Lilymay
    And the seed script is re-run against the same learner partition
    When both flows complete
    Then every dispatched write from each flow should be reported as either succeeded, failed, or abandoned
    And neither flow should observe a hang exceeding its own configured budget
    And the learner-state read after both complete should reflect every successful write from both flows

  # Why: The loader is consumed from multiple entry points (seed script + MCP handlers); a parse race must not duplicate work.
  # [ASSUMPTION: confidence=medium] Concurrent loaders return equivalent immutable values rather than sharing a process-wide cache; no caching layer is introduced for this repair task.
  @task:TASK-PH2-GR-001
  @edge-case @concurrency @config-loader
  Scenario: Two simultaneous Graphiti client constructions share the loaded configuration rather than racing on parse
    Given the canonical configuration file has not yet been loaded in this process
    When two callers request a Graphiti client simultaneously
    Then both callers should receive a client wired against the same configuration values
    And the configuration file should not produce two independent parses with diverging results

  # ==========================================================================
  # GROUP G: Integration Boundaries
  # ==========================================================================

  # Why: llama-swap is a young tool; an alias or upstream model returning a non-spec response must surface as a logged failure, not be swallowed.
  @task:TASK-PH2-GR-001
  @edge-case @integration-boundary
  Scenario: A malformed response from the local inference fleet surfaces as a logged write failure
    Given the local inference fleet returns a response that does not match the OpenAI-compatible contract
    When the system dispatches a baseline write through the wired Graphiti client
    Then the write should be recorded as a "write failed" structured event with a specific error class
    And the failure should not propagate as an unhandled exception to the caller
    And the seed exit code should reflect the failure rather than reporting success

  # Why: A pre-existing FalkorDB vector index at the wrong dimension would silently corrupt retrieval — the existing pre-flight must remain audible.
  # [ASSUMPTION: confidence=medium] When ".guardkit/graphiti.yaml" is missing or malformed the loader raises loudly with a clear "config file missing/invalid" error; degradation is not a permitted path because DECISION-DF-001 forbids any implicit cloud default.
  @task:TASK-PH2-GR-001
  @edge-case @integration-boundary @embedding-dim
  Scenario: A pre-existing graph-store vector index at a dimension different from the configured embedder produces a single explicit warning
    Given the graph store has an existing vector index at one dimension
    And the configured embedder produces vectors at a different dimension
    When the Graphiti client is constructed
    Then a single structured warning should be emitted naming both dimensions and a remediation hint
    And the warning should appear at most once per client construction (not per write)
Write graphiti-runtime-integration-repair_assumptions.yaml
102 lines
# Assumptions manifest for graphiti-runtime-integration-repair.feature
# Generated by /feature-spec on 2026-05-02

feature: "Graphiti Runtime Integration Repair"
generated: "2026-05-02"
stack: "python"
review_required: false

assumptions:
  - id: "ASSUM-001"
    scenario: "Re-running the seed when a complete baseline already exists is idempotent"
    assumption: >-
      Pre-flight idempotency treats any baseline signal (subjects, topic
      confidences, or recorded year_group) as "already seeded". A partial
      seed (some entities present, others missing) is also reported as
      "already seeded" and no recovery write is dispatched.
    confidence: medium
    basis: >-
      Matches existing _is_already_seeded() semantics in
      scripts/seed_student_model.py. Partial-seed recovery would broaden
      the repair task's blast radius; deferred to a follow-up if it ever
      occurs in practice.
    human_response: "confirmed"

  - id: "ASSUM-002"
    scenario: >-
      A pre-existing graph-store vector index at a dimension different
      from the configured embedder produces a single explicit warning
    assumption: >-
      When ".guardkit/graphiti.yaml" is missing or malformed the loader
      raises loudly with a clear "config file missing/invalid" error.
      Degradation is not a permitted path because DECISION-DF-001 forbids
      any implicit cloud default.
    confidence: medium
    basis: >-
      Aligns with AC-001 fail-loud policy on cloud-provider rejection at
      config-load time. A silent fallback to GraphitiConnectionConfig
      defaults would risk re-introducing OpenAI clients; explicit failure
      is the only safe behaviour.
    human_response: "confirmed"

  - id: "ASSUM-003"
    scenario: >-
      Two simultaneous Graphiti client constructions share the loaded
      configuration rather than racing on parse
    assumption: >-
      Concurrent loaders return equivalent immutable
      GraphitiConnectionConfig values rather than sharing a process-wide
      cache. No caching layer is introduced for this repair task.
    confidence: medium
    basis: >-
      Avoids introducing a singleton or cache for marginal value; YAGNI
      for this repair scope. Two parses producing the same values from
      the same on-disk YAML is sufficient to satisfy the "share the
      loaded configuration" assertion.
    human_response: "confirmed"

# Implementer hints (not formal assumptions; recorded for the test author)
implementer_hints:
  - context: "smoke-test wall-clock budget (AC-005)"
    hint: >-
      Suggested asyncio.wait_for / pytest timeout for the live smoke
      test: 180 seconds against the laptop fallback (ollama Q4_K_M),
      60 seconds when GB10 vllm is the active provider. Anything
      longer than 180s on laptop-fallback indicates a wiring problem.
      These are fixture-level timeouts, not contract assertions; the
      .feature file deliberately keeps the magic number out of the
      Gherkin so the spec stays portable across endpoints.
  - context: "rate-limit scenario fixture sizing (Group D rate-limit)"
    hint: >-
      The scenario asserts behaviour when rate-limited writes occur,
      not at what burst size. The full Lilymay seed footprint (one
      student + two subjects + four texts + six AOs + six topics +
      six initial confidences = 25 entities) is a realistic worst-case
      anchor for the test fixture, but any burst large enough to
      trigger the fake client's rate-limit response is sufficient.
  - context: "tutor-turn latency in the end-to-end demo (AC-007)"
    hint: >-
      The end-to-end scenario records p50 and p95 per-turn latency to
      phase-1-validation.md as a measurement, not a pass/fail gate.
      Phase 1 closure only requires the numbers to exist; budget gates
      are deliberately left for a follow-up after the laptop-fallback
      and GB10 baselines are both observed.

dropped_assumptions:
  - context: "tutor-turn latency budget"
    reason: >-
      AC-007 says "capture p50/p95 latency", which is a measure-and-
      record instruction, not a pass/fail gate. The scenario was
      updated to assert "latency was recorded" instead of asserting a
      specific budget. Avoids encoding a number that would be wrong
      for either laptop fallback or GB10.
  - context: "smoke-test wall-clock budget"
    reason: >-
      Magic numbers belong in the test fixture, not the .feature file.
      Moved to implementer_hints as a non-binding suggestion.
  - context: "rate-limit burst size"
    reason: >-
      The scenario asserts behaviour, not throughput; burst size is an
      implementation detail of the test fixture. Moved to
      implementer_hints as a non-binding suggestion.
Write graphiti-runtime-integration-repair_summary.md
103 lines
# Feature Spec Summary: Graphiti Runtime Integration Repair

**Stack**: python
**Generated**: 2026-05-02
**Scenarios**: 24 total (6 smoke, 1 regression)
**Assumptions**: 3 total (0 high / 3 medium / 0 low confidence)
**Review required**: No

## Scope

Repair the Graphiti runtime integration so every entity-extraction round-trip
hits the local inference fleet (llama-swap on `:9000`) instead of silently
defaulting to cloud LLM/embedding clients keyed off `OPENAI_API_KEY`. Wire
[get_client](../../src/study_tutor/knowledge/graphiti_client.py) with explicit
`OpenAIGenericClient` + `OpenAIEmbedder` per the canonical pattern in
`guardkit/guardkit/knowledge/graphiti_client.py:_build_llm_client` /
`_build_embedder`, load configuration from
[.guardkit/graphiti.yaml](../../.guardkit/graphiti.yaml), enforce
DECISION-DF-001 at config-load time, re-seed Lilymay's baseline against live
FalkorDB, and run an end-to-end MCP demo session to flip the Phase 1
falsified items (G2/G3/G4/G5/G6/G13) from "Falsified" to "Held".

## Scenario Counts by Category

| Category                                | Count |
|-----------------------------------------|------:|
| Key examples (`@key-example`)           |     5 |
| Boundary conditions (`@boundary`)       |     4 |
| Negative cases (`@negative`)            |     5 |
| Edge cases (`@edge-case`)               |    11 |
| Smoke (`@smoke`)                        |     6 |
| Regression (`@regression`)              |     1 |

(Counts overlap because scenarios may carry multiple tags.)

### Group breakdown

| Group | Theme                    | Count |
|-------|--------------------------|------:|
| A     | Key examples             |     5 |
| B     | Boundary conditions      |     4 |
| C     | Negative cases           |     4 |
| D     | Edge cases               |     5 |
| E     | Security                 |     2 |
| F     | Concurrency              |     2 |
| G     | Integration boundaries   |     2 |

Two of those entries are `Scenario Outline` blocks (B1 with 2 examples,
C1 with 2 examples), so the file contains 22 scenario *blocks* expanding
to 24 individual examples.

## Deferred Items

None — all proposed groups were accepted.

## Open Assumptions (low confidence)

None — three medium-confidence assumptions documented in
[graphiti-runtime-integration-repair_assumptions.yaml](./graphiti-runtime-integration-repair_assumptions.yaml).
Three originally-low-confidence items (tutor-turn latency budget, smoke-test
wall-clock budget, rate-limit burst size) were dropped after review on the
grounds that they are either (a) measure-and-record instructions per the
acceptance criteria, or (b) test-fixture magic numbers that don't belong in
domain-language Gherkin.

## Phase 1 Validation Gate Coupling

Five scenarios are explicitly tied to the Phase 1 falsification cluster:

| Scenario                                                                        | Closes |
|---------------------------------------------------------------------------------|--------|
| Running the baseline seed populates Lilymay's complete learner profile         | G2     |
| After seeding, the learner's state can be retrieved end-to-end                  | G3     |
| Running a tutoring session end-to-end persists a session-completed episode     | G4/G5/G6/G13 |
| The Phase 1 validation gate flips its falsified items to "Held"                | G2/G3/G4/G5/G6/G13 (closure) |
| A graphiti library upgrade that drifts the constructor surface is caught       | regression-prevention |

## DECISION-DF-001 Enforcement Surface

Five scenarios encode the no-cloud-API policy:

- C1 (Scenario Outline): cloud LLM provider rejected at config load
- C1 (Scenario Outline): cloud embedding provider rejected at config load
- C3: cross-encoder reranker rejected as critical error
- C4: OPENAI_API_KEY environment variable never read by wired client path
- E2: cloud provider value cannot be back-doored via environment override

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

```
/feature-plan "Graphiti Runtime Integration Repair" \
  --context features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_summary.md \
  --context tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
```

The feature file is already tagged with `@task:TASK-PH2-GR-001` on every
scenario, so the task-level BDD runner will pick up these scenarios as
Coach-blocking oracles automatically when `/task-work TASK-PH2-GR-001`
runs Phase 4 (per the task-scope tag convention documented in
`installer/core/commands/feature-spec.md`).
Bash Confirm output files exist
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/graphiti-runtime-integration-repair/

OUT
total 72
drwxr-xr-x  5 richardwoollcott  staff    160 May  2 10:25 .
drwxr-xr-x  8 richardwoollcott  staff    256 May  2 10:22 ..
-rw-r--r--  1 richardwoollcott  staff   4737 May  2 10:24 graphiti-runtime-integration-repair_assumptions.yaml
-rw-r--r--  1 richardwoollcott  staff   4638 May  2 10:25 graphiti-runtime-integration-repair_summary.md
-rw-r--r--  1 richardwoollcott  staff  18284 May  2 10:24 graphiti-runtime-integration-repair.feature

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: Graphiti Runtime Integration Repair
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
  features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair.feature
  features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_assumptions.yaml
  features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_summary.md

Scenarios: 24 total (22 blocks; 2 outlines × 2 examples)
  @key-example: 5    @boundary: 4
  @negative: 5       @edge-case: 11
  @smoke: 6          @regression: 1

Group breakdown:
  A Key examples · 5    B Boundary · 4    C Negative · 4
  D Edge cases · 5      E Security · 2    F Concurrency · 2
  G Integration · 2

Assumptions: 3 total
  high: 0
  medium: 3 (Coach review recommended)
  low: 0

Dropped after review: 3 (tutor-turn budget, smoke-test budget, rate-limit
burst size) — moved to implementer_hints in the assumptions manifest.

Deferred: 0

Next steps:
  Review:  features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair.feature
  Pass to feature-plan:
    /feature-plan "Graphiti Runtime Integration Repair" \
      --context features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_summary.md \
      --context tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Spec is ready. All 24 scenarios are tagged @task:TASK-PH2-GR-001, so the task-level BDD runner picks them up as Coach-blocking oracles automatically when you run /task-work TASK-PH2-GR-001 Phase 4.

are you sure about running the next command? /task-work TASK-PH2-GR-001 - shouldn't it be a /feature-plan?
You're right — I contradicted my own summary. The correct next step is /feature-plan, not /task-work.

The progression is:

/feature-spec (just done) → produces the BDD contract (the .feature file)
/feature-plan → reads the spec + the task file, decomposes TASK-PH2-GR-001 into the ~5 waves the task's "Implementation hint" already sketches, creates child sub-tasks, and (in its Step 11) invokes the bdd-linker subagent to retag scenarios from @task:TASK-PH2-GR-001 to the correct sub-task IDs (@task:TASK-PH2-GR-001-1, …-2, etc.) so the task-level BDD runner activates the right scenarios per wave
/task-work <sub-task> → implements one wave at a time, with that wave's scenarios as Coach-blocking oracles
Running /task-work TASK-PH2-GR-001 directly would technically work but skips the decomposition, jumping a complexity-5 task into one big implementation pass with all 24 scenarios as oracles. The wave structure (loader → wiring → smoke test → seed → demo) exists for a reason: each wave has a different blast radius and different verification evidence.

So the recommended next command is:


/feature-plan "Graphiti Runtime Integration Repair" \
  --context features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_summary.md \
  --context tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
Good catch.