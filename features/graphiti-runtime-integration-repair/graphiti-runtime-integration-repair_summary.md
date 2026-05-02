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
