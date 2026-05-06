---
id: TASK-GR-WIRE
title: "Wave 5 — BLOCK-3a: wire perform_session_end into MCP adapter"
task_type: feature
parent_review: TASK-REV-GRD5
parent_task: TASK-GR-DEMO
feature_id: FEAT-FD32
wave: 5
implementation_mode: task-work
complexity: 4
estimated_minutes: 90
dependencies: []
soft_dependency: TASK-GR-PMT
status: completed
priority: critical
created: 2026-05-05T22:30:00+00:00
updated: 2026-05-06T01:00:00+00:00
completed: 2026-05-06T01:00:00+00:00
completed_location: tasks/completed/TASK-GR-WIRE-orchestrator-and-session-end.md
tags:
  - graphiti
  - mcp
  - phase-1-gate-closure
  - async-writeback
  - wave-5
related:
  - TASK-GR-DEMO
  - TASK-REV-GRD5
  - TASK-GR-PMT
  - TASK-GR-CONF
  - TASK-DTL-005
consumer_context:
  - task: TASK-GR-CONF
    consumes: WriteHelperInjection
    framework: MCPAdapter constructor
    driver: tutor_session_end calls record_topic_confidence_update with the same write_helper
    format_note: TASK-GR-CONF needs the write_helper to be available on the adapter; this task adds it.
descope_carve_out:
  - block: BLOCK-1
    descoped_at: 2026-05-05T23:30:00+00:00
    rationale: orchestrator_factory wiring depends on undesigned LLMPlayerAdapter / LLMCoachAdapter / Coach prompt / session_state schema. Carved out to a Propose-Review feature spec.
    new_brief: docs/research/ideas/llm-player-coach-adapters-brief.md
    suggested_feature_slug: mcp-llm-player-coach-adapters
conductor_workspace: wave5-mcp-blockers-wave1-2
test_results:
  status: passing
  coverage: null
  last_run: 2026-05-06T00:30:00+00:00
  summary: |
    Adapter + adjacent suites: 228 passed, 1 skipped (live Graphiti integration smoke).
    Full unit run: 768 passed, 2 pre-existing baseline failures (unrelated to this task —
    reproduce on clean tree: mypy env failure per phase-1-validation.md, and
    cross-encoder sentinel test in tests/unit/knowledge/test_graphiti_client_wiring.py).
  acs_satisfied:
    - AC-WIRE-05: MCPAdapter constructor accepts write_helper, event_bus, graphiti_client (all default None)
    - AC-WIRE-06: tutor_session_end delegates to perform_session_end with topics_covered/aos_exercised from cached SessionPlan and a transition_state closure
    - AC-WIRE-07: tutor_session_end never awaits Graphiti operations (perform_session_end's F3 dispatch is fire-and-forget)
    - AC-WIRE-08: cli/main.py:serve constructs GraphitiClient via load_graphiti_config_from_yaml + get_client, wires GraphitiWriteHelper + EventBus, installs runtime_shutdown drain hook in try/finally
    - AC-WIRE-10: existing tests/unit/mcp/test_adapter*.py + tests/unit/tutoring/test_session_end.py all pass (additive constructor params preserve backwards compat)
    - AC-WIRE-11: tests/integration/test_mcp_session_end_smoke.py created with STUDY_TUTOR_LIVE_GRAPHITI_SMOKE skipif gate; mirrors test_typed_entity_writes.py pattern
  acs_pending_operator:
    - AC-WIRE-09: live MCP session evidence (operator-conducted post-merge)
  acs_descoped:
    - AC-WIRE-01 through AC-WIRE-04: BLOCK-1 carve-out — see docs/research/ideas/llm-player-coach-adapters-brief.md
---

# Wave 5 — BLOCK-3a: wire perform_session_end into MCP adapter

> **Scope-narrowed 2026-05-05.** This task originally bundled BLOCK-1 (orchestrator_factory injection)
> and BLOCK-3a (perform_session_end wiring). Investigation during /task-work surfaced that BLOCK-1
> depends on substantial undesigned surfaces (`LLMPlayerAdapter`, `LLMCoachAdapter`, Coach system
> prompt, `session_state` schema, scorer-vs-LLM strategy decision). BLOCK-1 has been carved out into
> a separate Propose-Review feature spec (see `descope_carve_out` in frontmatter and the brief at
> [docs/research/ideas/llm-player-coach-adapters-brief.md](../../../docs/research/ideas/llm-player-coach-adapters-brief.md)).
> The user will run `/feature-spec` and `/feature-plan` against that brief to spawn the BLOCK-1 work.
>
> **This task now ships BLOCK-3a only** — narrow, additive, and unblocks AC-DEMO-02 standalone.

## Why this exists

The 2026-05-05 MCP tutor session attempt (TASK-GR-DEMO) found that `tutor_session_end` contains a
literal `# TODO(phase-1): add async Graphiti write per DEC-02`
([adapter.py:308](../../../src/study_tutor/mcp/adapter.py#L308)). Meanwhile, the full session-end
machinery is already implemented and unit-tested at
[src/study_tutor/tutoring/session_end.py:334](../../../src/study_tutor/tutoring/session_end.py#L334)
(`perform_session_end`) — handles the F4 in-flight resolution, I-T6 zero-turn guard, DDR-003 ordering
(bus emit → schedule_write), F3 fire-and-forget dispatch, and `< 2s` caller-facing return per
ADR-ARCH-019. This task wires `tutor_session_end` to delegate to `perform_session_end`. AC-DEMO-02
(`session_completed` episode visible in Graphiti) flips on this.

See [TASK-REV-GRD5 review report §AC-REV-05 BLOCK-3](../../../.claude/reviews/TASK-REV-GRD5-review-report.md)
for the design rationale and §R1.2 for the C4 / sequence diagram trace.

The constructor signature changes here are deliberately additive (new optional params default to
`None`) so the future BLOCK-1 work — which adds `orchestrator_factory` injection from the CLI — can
land without touching this PR's surface area.

## Acceptance Criteria

### BLOCK-1 — DESCOPED (carved out to feature spec)

> **AC-WIRE-01 through AC-WIRE-04 have been descoped from this task.** They depend on undesigned
> `LLMPlayerAdapter` / `LLMCoachAdapter` / Coach prompt / `session_state` schema work that warrants
> a Propose-Review BDD spec rather than under-task-work-pressure design.
>
> Brief for the carved-out feature: [docs/research/ideas/llm-player-coach-adapters-brief.md](../../../docs/research/ideas/llm-player-coach-adapters-brief.md)
> Suggested feature slug: `mcp-llm-player-coach-adapters`
> Workflow: user runs `/feature-spec` then `/feature-plan` against the brief.

### BLOCK-3a — IN SCOPE (perform_session_end wiring)

- [ ] **AC-WIRE-05** — `MCPAdapter.__init__` accepts new optional parameters:

  ```python
  def __init__(
      self,
      role_config: RoleConfig,
      store: SessionStore | None = None,
      orchestrator_factory: Any = None,
      write_helper: GraphitiWriteHelper | None = None,
      event_bus: Any | None = None,         # in-process EventBus per DDR-003
      graphiti_client: Any | None = None,   # for read-back in tutor_session_end
  ) -> None:
  ```

  All new params default to `None` so existing tests (which construct adapters without these) continue
  to pass.

- [ ] **AC-WIRE-06** — `tutor_session_end` delegates to `perform_session_end(...)` from
  `study_tutor.tutoring.session_end`. The adapter:
  1. Resolves `session = self._store.get(session_id)` (returns `_session_not_found(...)` on miss).
  2. Pulls `topics_covered` and `aos_exercised` from the cached `SessionPlan` at
     `self._plan_sessions[session_id]` — `topics_covered = [plan.topic_name]`,
     `aos_exercised = list(plan.focus_aos)`.
  3. Threads a `transition_state` closure that calls `self._store.end(session_id)`.
  4. Awaits `perform_session_end(session=session, student_id=session.subject, write_helper=self._write_helper, event_bus=self._event_bus, topics_covered=..., aos_exercised=..., transition_state=...)`.
  5. Returns `perform_session_end`'s return value verbatim.

- [ ] **AC-WIRE-07** — `tutor_session_end` returns within **< 2s** wall-clock regardless of Graphiti
  latency (ADR-ARCH-019 binding constraint). Verified by:
  - Inspection: no `await` on Graphiti operations on the caller-facing code path.
  - Optional integration smoke test: `time` a `tutor_session_end` call against live FalkorDB and
    assert `< 2s` (skipif `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE`).

- [ ] **AC-WIRE-08** — `cli/main.py:serve` constructs and injects:
  - `GraphitiWriteHelper` instance (single-flight per process; same one consumed by the
    orchestrator's Coach for misconception writes).
  - `EventBus` instance (in-process; same one used by `perform_session_end` for DDR-003 ordering).
  - `Graphiti` client wrapper from `load_graphiti_config_from_yaml` + `get_client` (same path used
    by the seed and the integration smoke test).

  The runtime shutdown hook calls `runtime_shutdown(write_helper)` from
  `study_tutor.tutoring.session_end` so in-flight F3 writes drain before process exit.

- [ ] **AC-WIRE-09** — A live MCP session (operator-conducted) shows:
  1. `tutor_session_end` returns within `< 2s`.
  2. Within ~80s (`add_episode` median), `mcp__graphiti__get_episodes(group_ids=["student-lilymay"])`
     returns the new `session_completed` episode. Paste the JSON into the PR.

  Operator-conducted; this PR ships the plumbing and leaves AC-WIRE-09 unchecked for the operator to
  run after merge. Note that the live session can be conducted *without* TASK-GR-PMT or the BLOCK-1
  carve-out — `tutor_session_end` is independent of the `tutor_turn` Coach loop.

- [ ] **AC-WIRE-10** — All existing tests in `tests/unit/mcp/test_adapter*.py` and
  `tests/unit/tutoring/test_session_end.py` continue to pass. Signature changes are additive (new
  params default `None`).

- [ ] **AC-WIRE-11** — New integration smoke test
  `tests/integration/test_mcp_session_end_smoke.py` (skipif `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE`) boots
  the adapter end-to-end with a real Graphiti client, runs a 2-turn session, calls `tutor_session_end`,
  drains the write helper, and asserts the F3 episode is queryable. Mirrors the pattern of
  `tests/integration/test_typed_entity_writes.py`.

## Test Requirements

- **Unit**: `tutor_session_end` delegation test (mock `perform_session_end`, verify it's called with
  the expected args including `topics_covered` / `aos_exercised` from the cached `SessionPlan`).
- **Integration smoke**: `tests/integration/test_mcp_session_end_smoke.py` (AC-WIRE-11) — guarded by
  `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE` env var.
- **Existing**: full `pytest` run; no regression. The 695/696 baseline (pre-existing mypy env failure
  per phase-1-validation.md) stays.
- **Manual**: AC-WIRE-09 live session (operator-conducted post-merge).

## Implementation Notes

### File-by-file

| File | Change |
|---|---|
| `src/study_tutor/mcp/adapter.py` | Constructor signature: add `write_helper`, `event_bus`, `graphiti_client` optional params (default `None`); `tutor_session_end` delegates to `perform_session_end` instead of just `self._store.end`. The existing `orchestrator_factory` param stays untouched (will be wired by the carve-out feature). |
| `src/study_tutor/cli/main.py:serve` | Build `GraphitiClient` (via `load_graphiti_config_from_yaml` + `get_client`), `GraphitiWriteHelper`, `EventBus`; pass to `MCPAdapter`; install `runtime_shutdown(write_helper)` hook on shutdown. |
| `tests/unit/mcp/test_adapter.py` | Add `tutor_session_end` delegation test. Existing tests' adapter constructors remain unchanged (optional params default `None`). |
| `tests/integration/test_mcp_session_end_smoke.py` | New file (AC-WIRE-11). Mirrors `tests/integration/test_typed_entity_writes.py` pattern. |

### What this task does NOT do

- Does NOT wire `orchestrator_factory` (BLOCK-1 — carved out to feature spec; see frontmatter
  `descope_carve_out` and the brief at `docs/research/ideas/llm-player-coach-adapters-brief.md`).
  The constructor param stays as-is; the Phase-0 single-LLM `tutor_turn` path remains live until the
  carve-out feature lands.
- Does NOT implement `LLMPlayerAdapter` / `LLMCoachAdapter` / Coach prompt / `session_state` schema
  (all in the carve-out brief).
- Does NOT introduce `AGENT_MODELS__COACH_MODEL` or `_default_coach_model()` (carve-out brief D-COACH-05).
- Does NOT implement the `record_topic_confidence_update` helper (AC-DEMO-03 carve-out — that is
  TASK-GR-CONF). After this task lands, `tutor_session_end` writes the `session_completed` episode
  but does NOT update the TopicConfidence node attributes.
- Does NOT modify `roles/tutor/prompts/player.md`. That's TASK-GR-PMT.
- Does NOT extend the `SessionCompletedEpisode` schema. The current schema is sufficient for AC-DEMO-02;
  turn count is recoverable from `narrative_summary` per the review's R1.3.4 / AC-REV-04 analysis.

### Backwards-compat with FEAT-PH1-003 callers

`tests/unit/tutoring/test_session_end.py` exercises `perform_session_end` with explicit args. Those
tests stay green — this task adds a *consumer* of `perform_session_end`, not a *modification* of it.
If the consumer uncovers a needed contract change in `perform_session_end`, raise it as a separate
follow-up; do not bundle.

Existing `tests/unit/mcp/test_adapter*.py` tests construct `MCPAdapter` without the new params; the
optional defaults preserve their behaviour.

### Risk register

Per [TASK-REV-GRD5 review §AC-REV-05 BLOCK-3](../../../.claude/reviews/TASK-REV-GRD5-review-report.md):

- **Partial-failure** — the F3 write is fire-and-forget per ADR-ARCH-019; failure is logged-only by
  `_f3_write_coroutine` already.
- **Drain on shutdown** — `runtime_shutdown(write_helper)` lets in-flight F3 writes finish within the
  `GRAPHITI_DRAIN_WINDOW` (5s default per ASSUM-011) before process exit.
- **Stale `_plan_sessions` lookup** — if a `tutor_session_end` is called for a `session_id` that
  was never `tutor_start_session`-ed in this process (e.g. server restart between session lifecycle
  endpoints), `self._plan_sessions[session_id]` raises `KeyError`. Mitigation: fall back to empty
  `topics_covered=[]` / `aos_exercised=[]` when the plan is missing — `perform_session_end` derives
  topics from `session.topic` if `topics_covered` is empty.

## Cross-references

- [docs/research/ideas/llm-player-coach-adapters-brief.md](../../../docs/research/ideas/llm-player-coach-adapters-brief.md) — brief for the carved-out BLOCK-1 feature (run `/feature-spec` + `/feature-plan` against this)
- [TASK-REV-GRD5 review report §AC-REV-05 + §R1.2](../../../.claude/reviews/TASK-REV-GRD5-review-report.md) — design rationale and sequence diagrams
- [src/study_tutor/mcp/adapter.py:113-314](../../../src/study_tutor/mcp/adapter.py#L113) — file under modification
- [src/study_tutor/cli/main.py:47-65](../../../src/study_tutor/cli/main.py#L47) — entry point under modification
- [src/study_tutor/tutoring/session_end.py:334](../../../src/study_tutor/tutoring/session_end.py#L334) — `perform_session_end` consumed in BLOCK-3a
- [src/study_tutor/knowledge/graphiti_client.py](../../../src/study_tutor/knowledge/graphiti_client.py) — `load_graphiti_config_from_yaml` + `get_client` for the GraphitiClient construction
- [src/study_tutor/knowledge/async_write.py](../../../src/study_tutor/knowledge/async_write.py) — `GraphitiWriteHelper` constructor
- [docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md](../../../docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) — async fire-and-forget mandate
- [TASK-GR-DEMO](../TASK-GR-DEMO-end-to-end-mcp-tutor-session.md) — parent task being partially unblocked (AC-DEMO-02 only)
- [TASK-GR-CONF](./TASK-GR-CONF-topic-confidence-update.md) — depends on the `write_helper` injection point added by this task
