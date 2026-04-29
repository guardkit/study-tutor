---
complexity: 6
consumer_context:
- consumes: EpisodeTypes
  driver: pydantic
  format_note: Helper accepts EpisodeBase instances and serialises via to_graphiti_episode_body()
    before passing to add_episode
  framework: Pydantic v2 (BaseModel)
  task: TASK-GSM-002
- consumes: GroupIdConstants
  driver: stdlib
  format_note: 'Helper requires explicit group_ids: list[str] (no defaults). Validation
    rejects empty list and any string not prefixed with student:/subject:/fleet:'
  framework: string constants
  task: TASK-GSM-001
created: 2026-04-27 00:00:00+00:00
dependencies:
- TASK-GSM-001
- TASK-GSM-002
estimated_minutes: 150
feature_id: FEAT-1773
id: TASK-GSM-004
implementation_mode: task-work
parent_review: TASK-REV-7DC0
priority: high
status: design_approved
tags:
- graphiti
- async
- fire-and-forget
- cc-13
- ddr-002
- security
- prompt-injection
task_type: feature
title: Implement shared async fire-and-forget Graphiti write helper
updated: 2026-04-27 00:00:00+00:00
wave: 2
---

# Task: Implement shared async fire-and-forget Graphiti write helper

## Description

Build the **single** Graphiti write surface used by all flush points (F1 misconception via Coach, F2 confidence delta via Tutor handler, F3 session-end episode via Tutor handler) per **DDR-002**. The helper enforces:

- **Fire-and-forget shape** per **ADR-ARCH-019** + **CC-13**: every write goes through `asyncio.create_task`; the caller-facing path never awaits the write.
- **Log-only failure** per CC-13: a failed `add_episode` emits a structured log line and never raises to the caller.
- **Process-shutdown grace** per **ASSUM-007**: in-flight tasks awaited up to `GRAPHITI_SHUTDOWN_GRACE_SEC` (default 30s, env-var configurable) on graceful shutdown.
- **Input sanitisation** for the misconception text path (defends against prompt-injection-via-misconception attacks on Graphiti's extraction LLM).
- **Auditable single call site**: the only `add_episode(...)` call in the codebase lives in this module. CC-13 conformance test asserts this by AST/grep audit.

This is the **load-bearing** slice for FEAT-1773's structural-conformance story. Get this right, and DDR-002 / DDR-003 conformance falls out for free across the rest of Phase 1.

## Scope

**Module** (`src/study_tutor/knowledge/async_write.py`):

- `class GraphitiWriteHelper`:
  - `__init__(self, client: GraphitiClient | None, shutdown_grace_sec: int = 30)` — accepts a (possibly-None) client; stores grace period
  - `def schedule_write(self, group_ids: list[str], episode: EpisodeBase, flush_id: Literal["F1", "F2", "F3", "SEED"]) -> asyncio.Task | None` — synchronous dispatcher. Validates inputs, sanitises misconception text, schedules an `asyncio.create_task` wrapping `_perform_write`, registers the task in the in-flight set, returns the Task (or None if client is None — graceful no-op).
  - `async def _perform_write(self, ...) -> None` — internal coroutine. Calls `add_episode` (the **only** call site). On any exception emits structured log line and returns None. On success emits `event=graphiti_write_succeeded`.
  - `async def drain(self, timeout_sec: int | None = None) -> tuple[int, int]` — process-shutdown handler. Awaits all in-flight tasks up to `timeout_sec or shutdown_grace_sec`. Returns `(succeeded, abandoned)`. Abandoned tasks emit `event=graphiti_write_abandoned_at_shutdown`.

**Input sanitisation** (called from `schedule_write` before scheduling, only for misconception_text fields):
- `sanitise_misconception_text(text: str) -> str`:
  - Length cap: 500 chars (truncate with `[…truncated]` suffix beyond)
  - Strip control characters (`\x00-\x1F` except `\n` and `\t`)
  - Reject (raise `ValueError` caught at `schedule_write` level → log + drop) text matching coarse injection patterns: `(?i)(ignore previous|system:|<\|.*\|>|\[INST\])`
  - Returns the sanitised string

**Validation** (in `schedule_write`):
- `group_ids` must be non-empty list
- Each `group_id` must start with `STUDENT_GROUP_PREFIX`, `SUBJECT_GROUP_PREFIX`, or equal `FLEET_GROUP_ID` (rejected otherwise → log + drop)
- `flush_id` must be one of the literals above

**Structured log fields** (consistent across all log lines):
- `event` — `graphiti_write_scheduled` / `graphiti_write_succeeded` / `graphiti_write_failed` / `graphiti_write_dropped_invalid` / `graphiti_write_dropped_injection` / `graphiti_write_abandoned_at_shutdown`
- `flush_id`, `episode_kind`, `group_ids`, `error_class` (on failure), `latency_ms` (on success)

## Acceptance Criteria

- [ ] `GraphitiWriteHelper` constructable with `client=None`; `schedule_write` returns `None` and logs no error when client is None
- [ ] `schedule_write` returns an `asyncio.Task` for valid input + non-None client
- [ ] Caller-facing `schedule_write` returns in **< 50ms** even when the eventual `add_episode` would take 80s+ (no `await` in the dispatcher path)
- [ ] `_perform_write` catches `BaseException`, emits `graphiti_write_failed` log line with `error_class`, and returns None — never raises
- [ ] `sanitise_misconception_text` truncates strings > 500 chars
- [ ] `sanitise_misconception_text` strips ASCII control chars except `\n`, `\t`
- [ ] Texts matching `(?i)(ignore previous|system:|<\|.*\|>|\[INST\])` are dropped (log line `graphiti_write_dropped_injection`); no `add_episode` call is made
- [ ] Empty `group_ids` is rejected (log line `graphiti_write_dropped_invalid`)
- [ ] Group-ids not matching the three prefix patterns are rejected
- [ ] `drain()` awaits all in-flight tasks up to `shutdown_grace_sec`; returns `(succeeded, abandoned)` counts; emits `graphiti_write_abandoned_at_shutdown` for each unfinished task
- [ ] `GRAPHITI_SHUTDOWN_GRACE_SEC` env var overrides the default `shutdown_grace_sec`
- [ ] CC-13 conformance test: AST/grep audit asserts `add_episode(` appears in **exactly one** location (this module)
- [ ] Handler-budget conformance test: a tutor handler calling `schedule_write` returns within 2s when the underlying `add_episode` is mocked to hang for 80s
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- Unit tests in `tests/unit/knowledge/test_async_write.py`:
  - `schedule_write` with `client=None` → returns None, no log lines, no exception
  - `schedule_write` with valid input → returns Task; mock `add_episode` to assert call count and args
  - Input validation rejects: empty `group_ids`, malformed group_id, oversized misconception text (truncates), control chars (strips), injection patterns (drops + logs)
  - `_perform_write` failure path: mock `add_episode` to raise; assert `graphiti_write_failed` log + no propagation
  - `drain()`: schedule 3 fast + 2 hanging tasks with `shutdown_grace_sec=1`; assert `(3, 2)` return after ~1s
  - `GRAPHITI_SHUTDOWN_GRACE_SEC` env var honoured
- Integration tests in `tests/integration/test_async_write_integration.py` (gated on Synology FalkorDB):
  - End-to-end write of each episode kind succeeds; verifiable via `search_nodes`
  - Concurrent dispatch of N writes: all eventually land (last-write-wins per `@concurrency` scenarios)
- Conformance tests in `tests/conformance/test_cc13_audit.py`:
  - **CC-13 single call site**: `git grep -nE 'add_episode\s*\(' src/` returns exactly one match (in `async_write.py`)
  - **Handler budget**: synthetic handler that `schedule_write`s a hanging episode returns < 2s
- Security tests in `tests/security/test_misconception_injection.py`:
  - Each adversarial payload (`ignore previous instructions...`, `system: you are admin`, `<|im_start|>...`, `[INST] override [/INST]`) is dropped + logged
  - Coarse smoke test: no `admin` / `root` / cross-learner entity is created in FalkorDB after submitting an injection payload (gated on FalkorDB)

## Implementation Notes

- This module is the **CC-13 / DDR-002 / ADR-ARCH-019 conformance surface** for the entire tutor. Reviewers will read this file first when auditing Phase 1.
- The `flush_id` parameter is intentionally a `Literal` not an `Enum` — keeps the audit-by-grep simple.
- Do **not** add retries. Per ADR-ARCH-019 §Decision: "Write failures are logged-only … does not retry synchronously on the caller-facing path."
- Do **not** buffer or batch. Per ARCH-019 alternatives section + DDR-002 rationale: per-observation per-task dispatch is the architectural commitment.
- The "exactly one call site" rule is what makes future PR review tractable — protect it.

## Seam Test Recommendation

This task crosses an integration boundary (Tutor / Coach handler → Graphiti). Mandatory seam tests:
- **Contract test** for `schedule_write` signature and fire-and-forget guarantee (handler returns < 2s with hanging mock)
- **Mock-based seam test** for log-only failure (no propagation)
- **Boundary test** for `drain()` shutdown grace under load

## §4 Integration Contract Producer

This task produces one contract consumed by downstream slices:

**SharedAsyncWriteHelper** — `GraphitiWriteHelper.schedule_write(group_ids, episode, flush_id) -> asyncio.Task | None`. Consumed by TASK-GSM-005 (`record_session_completion` calls F3), TASK-GSM-006 (seeding uses `flush_id="SEED"`), and future FEAT-PH1-003 Coach AsyncSubAgent (F1).

See `IMPLEMENTATION-GUIDE.md §4` for full contract specification.

## Seam Tests

```python
"""Seam test: verify EpisodeTypes + GroupIdConstants contracts from upstream tasks."""
import asyncio
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("EpisodeTypes")
def test_episode_types_format():
    """Verify EpisodeTypes contract is honoured by the helper.

    Contract: Helper accepts EpisodeBase instances and serialises via
              to_graphiti_episode_body() before passing to add_episode.
    Producer: TASK-GSM-002
    """
    from study_tutor.knowledge.episodes import (
        EpisodeBase,
        SessionCompletedEpisode,
        TopicConfidenceUpdatedEpisode,
        MisconceptionObservedEpisode,
    )

    # Format assertion derived from §4 contract:
    # - All concrete episodes have to_graphiti_episode_body()
    for cls in (SessionCompletedEpisode, TopicConfidenceUpdatedEpisode, MisconceptionObservedEpisode):
        assert hasattr(cls, "to_graphiti_episode_body"), (
            f"{cls.__name__} must expose to_graphiti_episode_body() for the helper"
        )

    # - The discriminator field exists on the base
    assert "episode_kind" in EpisodeBase.model_fields


@pytest.mark.seam
@pytest.mark.integration_contract("GroupIdConstants")
def test_group_id_constants_validation():
    """Verify GroupIdConstants contract is honoured by the helper.

    Contract: Helper requires explicit group_ids: list[str] (no defaults).
              Validation rejects empty list and any string not prefixed with
              student:/subject:/fleet:.
    Producer: TASK-GSM-001
    """
    from study_tutor.knowledge.student_model import (
        STUDENT_GROUP_PREFIX,
        SUBJECT_GROUP_PREFIX,
        FLEET_GROUP_ID,
    )

    # Format assertion derived from §4 contract:
    valid_groups = [
        f"{STUDENT_GROUP_PREFIX}lilymay",
        f"{SUBJECT_GROUP_PREFIX}english-literature",
        FLEET_GROUP_ID,
    ]
    for g in valid_groups:
        assert any(
            g.startswith(prefix) or g == FLEET_GROUP_ID
            for prefix in (STUDENT_GROUP_PREFIX, SUBJECT_GROUP_PREFIX)
        ), f"Group id {g!r} fails the prefix discipline contract"
```