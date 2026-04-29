# Feature Spec Summary: Graphiti Student Model

**Stack**: python
**Generated**: 2026-04-27
**Scenarios**: 38 total (4 smoke, 0 regression)
**Assumptions**: 8 total (4 high / 3 medium / 1 low confidence)
**Review required**: Yes

## Scope

This specification covers FEAT-PH1-001 from `phase-1-scope.md`: a persistent
knowledge-graph-backed student model providing a learner profile (identity,
subjects, texts, topics, AOs, misconceptions, topic confidence), three core
query helpers (state read, topic recommendation, session-completion record),
a one-off seeding script, and async fire-and-forget write-back at every
write point per ADR-ARCH-019 / DDR-002 / DDR-003.

Domain language is used throughout: scenarios describe learner-facing
outcomes ("recommendations should prioritise weak areas") and persistence
boundaries ("the caller-facing path should not wait on persistence") rather
than Graphiti-internal mechanics. ADR-ARCH-019's every-write-point fire-and-
forget rule is reflected in `@async` scenarios; CC-14 (runtime LLM params)
is out of scope here and lives in the Inference Runtime feature.

## Scenario Counts by Category

| Category                       | Count |
|--------------------------------|------:|
| Key examples (@key-example)    |     8 |
| Boundary conditions (@boundary)|     9 |
| Negative cases (@negative)     |     7 |
| Edge cases (@edge-case)        |    14 |
| Smoke (@smoke)                 |     4 |
| Regression (@regression)       |     0 |

Cross-cutting tags applied alongside the above:
- `@async` — 6 scenarios (every fire-and-forget write path)
- `@security` — 3 scenarios (prompt-injection-via-misconception, scoping leakage)
- `@concurrency` — 3 scenarios (overlapping writes, last-write-wins, no read-your-writes)
- `@scoping` — 3 scenarios (per-learner / fleet group-id isolation)
- `@integration-boundary` — 2 scenarios (extraction LLM, embeddings endpoint)
- `@seeding` — 3 scenarios (idempotency, store unreachable, unknown learner)
- `@module-load` — 1 scenario (graphiti-core absent)
- `@crash-recovery` — 1 scenario (process crash mid-write)

## Deferred Items

None — all four proposed groups and the edge-case expansion were accepted
without deferral.

## Open Assumptions (low confidence)

- **ASSUM-007** — Process-shutdown grace period of 30 seconds for in-flight
  background writes. Inferred; not specified in any input document. Should
  be validated during Phase 1 demo testing and may need to become a
  configurable env var rather than a hardcoded value. See
  `graphiti-student-model_assumptions.yaml` for full notes.

## Cross-repo discrepancies surfaced

- **Group identifier for fleet scope** — `phase-1-scope.md` specifies
  `fleet:appmilla`; the existing specialist-agent code uses
  `appmilla-fleet`. study-tutor follows the scope doc. ASSUM-008 records
  the divergence.

## Architectural anchors honoured

- **ADR-ARCH-019** (every-write-point async): every `@write-path` scenario
  is also `@async`; handler-return budget asserted at 2 seconds.
- **DDR-002** (Coach AsyncSubAgent owns its own writes): scenarios about
  misconception writes describe ownership at the producer boundary, not at
  a session-end batch.
- **DDR-003** (events emit on state transition): scenario "A session
  abandoned before any tutor turn produces no persisted session episode"
  reflects the I-T6 invariant.
- **CC-13** (every Graphiti write site fire-and-forget): scenario "A
  failed background persistence write does not surface to the caller"
  asserts log-only failure.
- **LES1 §3** (graceful module load): scenario "The student-model module
  loads successfully when the Graphiti library is not installed" reflects
  the lazy-import shape from `graphiti_client.py`.

## Anti-patterns avoided

- No HTTP status codes, no `add_episode` direct invocation in step text, no
  FalkorDB-specific terminology in domain steps.
- No implementation file references in scenario comments.
- No always-retrieve-first pattern (the feature's persistence model is
  separate from the Phase 1 RAG retrieval decision in FEAT-PH1-004).

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Graphiti Student Model" \
      --context features/graphiti-student-model/graphiti-student-model_summary.md \
      --context docs/research/ideas/phase-1-scope.md \
      --context docs/research/ideas/phase-1-build-plan.md \
      --context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md \
      --context docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md \
      --context docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md

`/feature-plan` Step 11 (bdd-linker subagent) will tag scenarios with
`@task:<TASK-ID>` after task creation. Recommended task slicing under the
build-plan dependency chain:

- Schema definition (Student / Subject / Text / Topic / AO / Misconception /
  TopicConfidence + 6 relationships) — covers Group A scenarios 1, 6.
- Episode types (`session_completed`, `topic_confidence_updated`,
  `misconception_observed`) — covers Group A scenarios 2, 4, 5.
- Graphiti client wrapper with lazy import and graceful degradation —
  covers Group D module-load scenario, Group C unreachable / timeout
  scenarios, and the Group D seeding-defers scenario.
- Query helpers (`get_student_state`, `get_topic_recommendations`,
  `record_session_completion`) — covers Group A scenarios 1, 3, 7, 8 and
  all Group B recommendation-count / cooldown / band-mapping scenarios.
- Async write-back helper (single fire-and-forget shared helper per
  DDR-002) — covers Group B latency / failed-write scenarios, Group D
  concurrency / crash / shutdown / read-your-writes scenarios, and Group
  E integration-boundary scenarios.
- Seeding script — covers Group C idempotency and Group D
  seeding-defers-on-unreachable scenarios.
