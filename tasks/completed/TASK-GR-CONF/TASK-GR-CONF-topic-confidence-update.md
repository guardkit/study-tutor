---
id: TASK-GR-CONF
title: "Wave 5 — BLOCK-3b: TopicConfidence node update on session end (typed-entity write + pluggable policy)"
task_type: feature
parent_review: TASK-REV-GRD5
parent_task: TASK-GR-DEMO
feature_id: FEAT-FD32
wave: 5
implementation_mode: task-work
complexity: 5
estimated_minutes: 240
dependencies:
  - TASK-GR-WIRE
status: completed
priority: critical
created: 2026-05-05T22:30:00+00:00
updated: 2026-05-06T01:00:00+00:00
completed: 2026-05-06T01:00:00+00:00
completed_location: tasks/completed/TASK-GR-CONF/
previous_state: in_review
tags:
  - graphiti
  - mcp
  - phase-1-gate-closure
  - typed-entity
  - async-writeback
  - wave-5
related:
  - TASK-GR-DEMO
  - TASK-REV-GRD5
  - TASK-GR-WIRE
  - TASK-GSM-009
  - FEAT-PH2-001
consumer_context:
  - task: TASK-GR-WIRE
    consumes: WriteHelperInjection
    framework: MCPAdapter constructor
    driver: tutor_session_end calls record_topic_confidence_update with the same write_helper instance
    format_note: This task assumes TASK-GR-WIRE has already added write_helper / event_bus / graphiti_client params to MCPAdapter.__init__.
conductor_workspace: wave5-mcp-blockers-wave2-1
test_results:
  status: passed
  coverage: "80% (knowledge.queries + knowledge.episodes + mcp.adapter combined)"
  unit_tests_passed: 783
  unit_tests_skipped: 1
  unit_tests_deselected: 2  # pre-existing unrelated: mypy env + cross-encoder sentinel
  last_run: 2026-05-06T00:30:00+00:00
---

# Wave 5 — BLOCK-3b: TopicConfidence node update on session end (typed-entity write + pluggable policy)

## Why this exists

After TASK-GR-WIRE lands, `tutor_session_end` writes a `session_completed` episode to Graphiti
(satisfying AC-DEMO-02). It does NOT update the `TopicConfidence` node attributes that the planner
reads via `get_student_state`. AC-DEMO-03 explicitly requires:

> *"`mcp__graphiti__search_nodes(query="<topic from session>", group_ids=["student-lilymay"])` returns
> updated `topic_confidences` reflecting the in-session learning. (Confirms Graphiti round-trip:
> write → entity update → read.)"*

This task implements that entity update.

**Two design decisions of the deep dive in [TASK-REV-GRD5 review §R1.3](../../../.claude/reviews/TASK-REV-GRD5-review-report.md)
are load-bearing:**

1. **The Coach scores the Player, not the student.** `CoachVerdict.weighted_total` and
   `criterion_scores` measure tutor quality, not student understanding. Mapping them directly to
   confidence delta is a category error.
2. **Phase-1 must not lock in a wrong confidence-update model.** FEAT-PH2-001 explicitly owns the
   confidence-update *policy*; the Phase-2 build plan §"Coach signal quality" lists the policy choice
   (direct mapping vs smoothed aggregate) as an open design question.

The implementation therefore separates **infrastructure** (entity uuid derivation, EntityNode
load+mutate+save, `last_revised_at` flip, episode wiring, fire-and-forget bookkeeping) from **policy**
(how to compute the percentage delta from session signals). Phase 1 ships the infrastructure plus a
deliberately weak `Phase1MinimalDeltaPolicy` stub. FEAT-PH2-001 replaces the policy via Protocol
substitution.

## Acceptance Criteria

- [ ] **AC-CONF-01** — A new helper `record_topic_confidence_update(...)` is added — preferred location
  `src/study_tutor/knowledge/queries.py` alongside `record_session_completion`, or a new
  `src/study_tutor/knowledge/student_writes.py` if `queries.py` is getting too large. Signature:

  ```python
  async def record_topic_confidence_update(
      *,
      client: Any | None,                      # GraphitiClient wrapper or None
      write_helper: GraphitiWriteHelper,
      student_id: str,
      topic_ref: str,                          # the topic_override or planner-selected topic name
      session_summary: dict[str, Any],         # carries misconceptions_per_topic, student_turn_count, ended_at, triggering_session_id, ...
      policy: ConfidenceDeltaPolicyLike,
      create_task_fn: Callable[[Awaitable[Any]], asyncio.Task[Any]] = asyncio.create_task,
  ) -> None: ...
  ```

  No-op (returns immediately) when `client is None`.

- [ ] **AC-CONF-02** — A `ConfidenceDeltaPolicyLike` `Protocol` is defined alongside the helper:

  ```python
  class ConfidenceDeltaPolicyLike(Protocol):
      """Computes a TopicConfidence percentage delta for a completed session.

      Phase-1 ships Phase1MinimalDeltaPolicy; FEAT-PH2-001 supplies the real one.
      """
      def compute(
          self,
          *,
          student_id: str,
          topic_ref: str,
          session_summary: dict[str, Any],
      ) -> int: ...
  ```

  And a stub implementation:

  ```python
  class Phase1MinimalDeltaPolicy:
      """Phase-1 expedient. NOT a real model of confidence change.

      Owned by FEAT-PH2-001 for replacement. See TASK-REV-GRD5 §R1.3 for the
      Coach-signal taxonomy and category-error analysis that drives this stub design.
      """
      def compute(self, *, student_id, topic_ref, session_summary):
          misc = session_summary.get("misconceptions_per_topic", {}).get(topic_ref, 0)
          turns = session_summary.get("student_turn_count", 0)
          delta = -3 * misc
          if turns >= 5 and misc == 0:
              delta += 1
          return max(-10, min(10, delta))
  ```

  The stub MUST carry a docstring explicitly flagging it as a Phase-1 expedient and naming
  FEAT-PH2-001 as the replacement owner.

- [ ] **AC-CONF-03** — The helper:
  1. Derives the `TopicConfidence` node UUID via
     `seed_uuids.topic_confidence_uuid(student_ref=student_id, topic_ref=topic_ref, group_id=...)`
     — same UUID the seed uses (confirms MERGE-by-uuid, not duplicate creation).
  2. Loads the existing node (graphiti-core `EntityNode.get_by_uuid` or driver query — see
     `tests/integration/test_typed_entity_writes.py` for the pattern).
  3. Computes `new_percentage = clamp(0, current_percentage + policy.compute(...), 100)`.
  4. Recomputes `band = confidence_band_for(new_percentage)`.
  5. Sets `last_revised_at = session_summary["ended_at"]`.
  6. Calls `EntityNode.save(...)` (typed-entity write per ADR-ARCH-021 — bypasses LLM extraction).

- [ ] **AC-CONF-04** — Delta-handling rules:
  - When `delta != 0`: entity update happens (per AC-CONF-03) **and** a
    `TopicConfidenceUpdatedEpisode` is scheduled via
    `write_helper.schedule_write(group_ids, episode, flush_id="F2")`.
  - When `delta == 0`: entity update **still happens** but only flips `last_revised_at` (percentage
    and band unchanged). The F2 episode write is **skipped** — no temporal change worth recording.
    Rationale: AC-DEMO-03 only requires "the round-trip works" — `last_revised_at` flipping is
    structural change visible to `search_nodes`. The episode is for downstream temporal analytics,
    which has nothing to record when the percentage didn't move.

- [ ] **AC-CONF-05** — All writes are **fire-and-forget** per ADR-ARCH-019:
  - The `EntityNode.save` call is wrapped in `create_task_fn(...)` (default `asyncio.create_task`).
  - The episode write goes through `GraphitiWriteHelper.schedule_write`, which is itself
    fire-and-forget (returns within ~50ms).
  - Neither blocks `tutor_session_end` from returning within `< 2s`.

- [ ] **AC-CONF-06** — Failure modes are logged but do NOT raise. Specifically:
  - **Node not found** (e.g. `topic_ref` is a topic that wasn't seeded): emit
    `event=topic_confidence_update_skipped reason=node_not_found student_id=... topic_ref=...`.
    The `session_completed` episode write proceeds independently. AC-DEMO-03 evidence is degraded
    (no entity to update) but not broken (operator picks a seeded topic for the demo).
  - **Save failure** (e.g. R-WAVE5-04 `Connection closed by server`, or R-WAVE5-03 dash-as-NOT
    re-surfacing): emit `event=topic_confidence_update_failed reason=... error_type=...`. Continue
    without raising.
  - **Episode write failure**: handled by `GraphitiWriteHelper`'s existing fire-and-forget posture.

- [ ] **AC-CONF-07** — `TopicConfidenceUpdatedEpisode` schema is extended with one new field:

  ```python
  confidence_source: str = Field(
      ...,
      min_length=1,
      description=(
          "Identifier of the policy that produced the delta. Phase-1 stub sets "
          "'phase1_minimal_policy'; FEAT-PH2-001 sets a different value. "
          "Lets future analytics distinguish heuristic-era data from real-signal data."
      ),
  )
  ```

  This is a deliberate Pydantic schema extension (`extra="forbid"` is set on the model so adding the
  field is a contract change). The PR description must call this out as a schema bump and reference
  TASK-REV-GRD5 §R1.3.4 / AC-CONF-07 for rationale. The stub policy passes
  `confidence_source="phase1_minimal_policy"`.

- [ ] **AC-CONF-08** — `MCPAdapter.tutor_session_end` (already modified by TASK-GR-WIRE to delegate to
  `perform_session_end`) is extended to call `record_topic_confidence_update(...)` after
  `perform_session_end` returns. The new call site:
  - Resolves `topic_ref` from `session.topic` (the topic_override or planner-selected topic from
    `tutor_start_session`).
  - Builds `session_summary` with `misconceptions_per_topic` (aggregate from `session.turns`'
    Coach-emitted `MisconceptionObservation` payloads if available; empty dict otherwise),
    `student_turn_count` (count of `role == "user"` turns in `session.turns`), `ended_at` (from
    `perform_session_end`'s session-end timestamp), and `triggering_session_id` (the session id).
  - Passes `policy=Phase1MinimalDeltaPolicy()`. Future TASK-PH2-CONF or FEAT-PH2-001 swaps in the
    real policy.

  Per ADR-ARCH-019, the call does NOT block the caller-facing return; if the call is awaited at all,
  it must be only for the fire-and-forget kickoff (`schedule_write` returns synchronously; the
  `create_task` for `EntityNode.save` is non-blocking).

- [ ] **AC-CONF-09** — Live MCP session against Lilymay's "Lady Macbeth's ambition" topic (seeded
  baseline 55%, "developing" band, `last_revised_at = EPOCH_NEVER_REVISED`) shows post-session:
  - `mcp__graphiti__search_nodes(query="Lady Macbeth's ambition", group_ids=["student-lilymay"])`
    returns the TopicConfidence node with `last_revised_at` flipped from epoch sentinel to the
    actual session end time.
  - `percentage` and `band` either moved (delta != 0 case) or remained at 55%/"developing" (delta
    == 0 case) — both satisfy AC-DEMO-03 because `last_revised_at` is the structural change.
  - Paste the search_nodes JSON into the PR.

- [ ] **AC-CONF-10** — Unit tests cover:
  - Delta clamping (delta < -10 → -10; delta > +10 → +10).
  - Delta == 0 case: `last_revised_at` flips, no F2 episode scheduled.
  - Delta != 0 case: percentage / band update + F2 episode scheduled.
  - `node_not_found` logging path.
  - Protocol surface: a fake `ConfidenceDeltaPolicyLike` returning a fixed delta wires through
    correctly.

- [ ] **AC-CONF-11** — Integration smoke test
  `tests/integration/test_topic_confidence_update_smoke.py` (skipif `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE`)
  performs: load the seeded TopicConfidence node, run `record_topic_confidence_update` with a fake
  policy returning `+2`, drain the helper, re-load the node, assert `percentage` moved by +2 and
  `last_revised_at` flipped. Mirrors the `test_typed_entity_writes.py` pattern.

- [ ] **AC-CONF-12** — TASK-GR-CONF's task description (this file) explicitly:
  - Names FEAT-PH2-001 as the owner of the `Phase1MinimalDeltaPolicy` replacement.
  - References [TASK-REV-GRD5 §R1.3](../../../.claude/reviews/TASK-REV-GRD5-review-report.md) as the
    design rationale.
  - Documents in the PR description that `confidence_source != "phase1_minimal_policy"` is the
    Phase-2 dashboard filter for real-signal data.

## Test Requirements

- **Unit**: AC-CONF-10 (six test cases minimum: clamp lower, clamp upper, delta zero, delta non-zero
  with band change, delta non-zero without band change, node_not_found logging).
- **Integration smoke**: AC-CONF-11 (`STUDY_TUTOR_LIVE_GRAPHITI_SMOKE` guarded).
- **Manual**: AC-CONF-09 live-session evidence pasted into PR.
- **Existing**: `pytest` baseline holds (695/696 with the pre-existing mypy env failure unchanged).

## Implementation Notes

### File-by-file

| File | Change |
|---|---|
| `src/study_tutor/knowledge/queries.py` (or new `student_writes.py`) | Add `ConfidenceDeltaPolicyLike` Protocol, `Phase1MinimalDeltaPolicy` stub, `record_topic_confidence_update` helper. |
| `src/study_tutor/knowledge/episodes.py` | Add `confidence_source: str` field to `TopicConfidenceUpdatedEpisode`. Schema extension; tests of episode shape need matching update. |
| `src/study_tutor/mcp/adapter.py` | `tutor_session_end` calls `record_topic_confidence_update` after `perform_session_end` returns (or interleaved). |
| `src/study_tutor/knowledge/seed_uuids.py` | No change expected — existing `topic_confidence_uuid(...)` is the consumer surface. Verify the helper signature matches. |
| `tests/unit/knowledge/test_queries.py` (or new test file) | AC-CONF-10 unit tests. |
| `tests/integration/test_topic_confidence_update_smoke.py` | New file (AC-CONF-11). |

### Coach-signal taxonomy and the misconception aggregation

The stub policy reads `misconceptions_per_topic` from `session_summary`. The session summary is built
in TASK-GR-CONF's caller (the adapter's `tutor_session_end`), which sees the session's turn list. Per
the Coach contract (CoachVerdict.misconceptions: list[MisconceptionObservation]), each turn carrying a
Coach verdict potentially carries zero-or-more misconceptions, each with a `topic_name` field. The
adapter aggregates:

```python
misc_count = sum(
    sum(1 for m in turn_record.coach_verdict.misconceptions if m.topic_name == topic_ref)
    for turn_record in session.turns_with_verdicts
    if turn_record.coach_verdict is not None
)
session_summary["misconceptions_per_topic"] = {topic_ref: misc_count}
```

If `session.turns` does not currently track per-turn `CoachVerdict` objects (the adapter today
doesn't store them in the SessionStore), the simplest fix is to extend the in-memory `TutorSession`
to capture them on the orchestrator-routed path. **Confirm this during implementation**; if the
extension would push complexity past 6, fall back to `misc_count = 0` for Phase 1 (the stub then
produces a +1 upward signal on 5+ turn sessions, which still satisfies AC-DEMO-03).

### Why typed-entity writes (and what they bypass)

The seed (TASK-GSM-009 / ADR-ARCH-021) uses `EntityNode.save` directly to bypass graphiti-core's
LLM-driven `add_episode` extraction path. The same approach applies here:

- `EntityNode.save` operates against FalkorDB's Cypher/Redis protocol directly. Latency: ms.
- `add_episode` (via `schedule_write`) goes through Gemini extraction. Latency: 78.98s median.

The two paths have different reliability characteristics. The R-WAVE5-03 RediSearch dash-as-NOT bug
surfaces only inside `add_episode`'s entity-resolution step; typed-entity writes don't trigger it.
This is why the entity update (AC-CONF-03) reliably satisfies AC-DEMO-03 even if the F2 episode
write (AC-CONF-04) fails.

### What this task does NOT do

- Does NOT implement a "real" Coach-driven confidence-update policy. That is FEAT-PH2-001's job.
- Does NOT add a UI / CLI surface for student self-report of confidence. Out of scope; never on the
  Phase-1 path.
- Does NOT touch multi-topic sessions. Phase-1 sessions are single-topic by design (per the planner
  contract); BLOCK-3b updates exactly one TopicConfidence node per session.
- Does NOT add transactional semantics across the entity-update and episode writes. Per
  ADR-ARCH-014 / ARCH-019, fail-soft single-write per flush point is the architectural commitment.

### Risk register

Per [TASK-REV-GRD5 review §AC-REV-05 BLOCK-3 + §R1.4](../../../.claude/reviews/TASK-REV-GRD5-review-report.md):

- **Category-error trap reappears in FEAT-PH2-001** — Protocol seam in this task forces FEAT-PH2-001
  to design the policy contract explicitly.
- **Heuristic-era data poisons Phase-2 analytics** — `confidence_source` field (AC-CONF-07)
  filterable.
- **R-WAVE5-03 surfaces on F2 episode** — entity update (load-bearing for AC-DEMO-03) is on the
  unaffected typed-entity path; episode failure is logged-only.
- **Node not found** — operator must pick a seeded topic (Lilymay has 6 seeded TopicConfidence nodes
  per TASK-GSM-009 evidence; "Lady Macbeth's ambition" is one).
- **Heuristic delta drives band boundary unexpectedly** — if percentage was at 64% (top of
  "developing"), a +1 shift to 65% may flip band to "secure". Acceptable: the band recomputation is
  a faithful reflection of the threshold rule. If FEAT-PH2-001 wants band stability, that's a
  policy-layer concern, not infrastructure.

## Cross-references

- [TASK-REV-GRD5 review report §R1.3 (BLOCK-3b deep dive)](../../../.claude/reviews/TASK-REV-GRD5-review-report.md) — design rationale (Coach-signal taxonomy, category-error analysis, Protocol-seam decision)
- [TASK-REV-GRD5 review report §R1.3.4](../../../.claude/reviews/TASK-REV-GRD5-review-report.md) — AC-CONF originating spec
- [docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md](../../../docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md) — typed-entity write pattern (the seed's pattern this task mirrors)
- [docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md](../../../docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) — fire-and-forget posture
- [src/study_tutor/knowledge/episodes.py:101-130](../../../src/study_tutor/knowledge/episodes.py#L101) — `TopicConfidenceUpdatedEpisode` (extended by AC-CONF-07)
- [src/study_tutor/knowledge/seed_uuids.py:81-90](../../../src/study_tutor/knowledge/seed_uuids.py#L81) — `topic_confidence_uuid` (consumed by AC-CONF-03)
- [src/study_tutor/knowledge/student_model.py:307-333](../../../src/study_tutor/knowledge/student_model.py#L307) — `TopicConfidence` typed-entity schema
- [tests/integration/test_typed_entity_writes.py](../../../tests/integration/test_typed_entity_writes.py) — pattern for AC-CONF-11 integration test
- [TASK-GR-WIRE](./TASK-GR-WIRE-orchestrator-and-session-end.md) — supplies the `write_helper` injection
- [TASK-GR-DEMO](../TASK-GR-DEMO-end-to-end-mcp-tutor-session.md) — parent task whose AC-DEMO-03 this closes
- FEAT-PH2-001 (gamification) — owner of the `Phase1MinimalDeltaPolicy` replacement
