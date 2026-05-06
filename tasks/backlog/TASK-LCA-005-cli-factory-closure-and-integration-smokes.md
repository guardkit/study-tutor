---
id: TASK-LCA-005
title: Wire CLI orchestrator_factory closure and integration smokes (per-turn isolation, Phase-1 metadata, live Lilymay)
task_type: feature
parent_review: TASK-REV-LCA1
feature_id: FEAT-6CC5
feature_slug: mcp-llm-player-coach-adapters
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
  - TASK-LCA-001
  - TASK-LCA-002
  - TASK-LCA-003
  - TASK-LCA-004
status: backlog
priority: high
created: 2026-05-06T01:00:00+00:00
updated: 2026-05-06T01:00:00+00:00
tags:
  - feat-lca
  - integration
  - cli
  - smoke-test
  - phase-1
related:
  - TASK-REV-LCA1
  - TASK-LCA-001
  - TASK-LCA-002
  - TASK-LCA-003
  - TASK-LCA-004
  - TASK-GR-WIRE
  - TASK-GR-PMT
context_files:
  - features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md
  - docs/research/ideas/llm-player-coach-adapters-brief.md
  - src/study_tutor/cli/main.py
  - src/study_tutor/mcp/adapter.py
  - src/study_tutor/tutoring/orchestrator.py
test_results:
  status: pending
---

# Task: CLI factory closure + integration smokes

## Description

The Wave-2 integrator. Pulls together the four Wave-1 deliverables
(`LLMPlayerAdapter`, `LLMCoachAdapter` + Coach prompt, `SessionState`,
`_default_coach_model()` + boot smoke check) into:

1. An `orchestrator_factory` closure constructed in
   `src/study_tutor/cli/main.py:serve` that, on each invocation, builds a
   fresh `PlayerCoachOrchestrator` with a freshly-constructed Player and
   Coach adapter — enforcing the per-turn factory isolation invariant.
2. The `MCPAdapter(orchestrator_factory=...)` wiring at the construction
   site in `serve` (existing kwarg already accepted; this task supplies
   the closure).
3. The integration smoke tests covering AC-LCA-01 (per-turn isolation),
   AC-LCA-09 (Phase-1 metadata shape), and AC-LCA-10 (live Lilymay
   session — operator-conducted, with calibration-fallback wording per
   Context A Q5).

This task is sequential after Wave 1 because the closure imports all
four Wave-1 surfaces.

## Acceptance Criteria

- [ ] `cli/main.py:serve` constructs `orchestrator_factory` as a no-arg closure that on each call builds a fresh `LLMPlayerAdapter`, fresh `LLMCoachAdapter`, fresh `PlayerCoachOrchestrator(player=..., coach=..., quote_verifier=None, coach_handover=None, on_flag=<logger callback>)`
- [ ] `quote_verifier=None` and `coach_handover=None` in the first-cut closure (per ASSUM-LCA-015 — both stay None on first cut; wiring is deferred to a follow-up subtask)
- [ ] `on_flag` callback emits a structured log line `event="orchestrator_turn_flagged"` to stderr (per D-COACH-07 — logger-only, no DB write, no metric backend)
- [ ] `MCPAdapter(orchestrator_factory=orchestrator_factory, ...)` is wired at the construction site in `serve`
- [ ] **AC-LCA-01** (per-turn factory isolation, smoke): two concurrent `tutor_turn` invocations for two different sessions receive distinct `PlayerCoachOrchestrator` instances. Asserted via integration test using a tracking factory that records each invocation
- [ ] **AC-LCA-09** (Phase-1 metadata shape, integration): live `tutor_turn` returns a dict with keys `tutor_response`, `decision`, `attempts`, `flagged_for_review`, `duration_seconds`; `decision ∈ {"accept", "exhausted", "fallback"}`
- [ ] **AC-LCA-10** (live session, smoke — operator-conducted, with calibration fallback per Context A Q5): a 2-turn Lilymay session against the seeded state demonstrates EITHER `attempts > 1` on at least one turn (Coach revision occurred — calibration is working) OR documents in the session log that the Coach never disagreed and records this as a known Phase-2 calibration follow-up rather than a test failure
- [ ] AC-LCA-10 outcome (revise-occurred or calibration-gap) is captured in `docs/research/ideas/phase-1-validation.md` (or equivalent operator log) for traceability
- [ ] Integration test scenario class is marked `@pytest.mark.feat_lca and @pytest.mark.smoke` so the smoke gate `pytest -m "feat_lca and smoke"` covers this layer
- [ ] Same-provider rejection is asserted at boot in this layer too (AC-LCA-08): construct `MCPAdapter(orchestrator_factory=closure)` with both env vars set to the same provider; assert `CoachConfigurationError`
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- Integration tests in `tests/integration/test_mcp_lca_smoke.py`:
  - per-turn isolation (AC-LCA-01) — use a tracking factory wrapper that increments a counter; assert counter == N after N concurrent calls
  - Phase-1 metadata shape (AC-LCA-09) — assert dict-key set and `decision` value membership
  - Same-provider rejection at boot (AC-LCA-08) — uses the closure, not just `validate_coach_config` directly
- Live Lilymay smoke (AC-LCA-10):
  - Marked `@pytest.mark.live` (excluded from default CI; operator-conducted)
  - Asserts the calibration-fallback wording: either `attempts > 1` on at least one turn OR a logged `calibration_gap=True` annotation
- All scenarios in this task are tagged `@pytest.mark.feat_lca` AND `@pytest.mark.smoke`

## Implementation Notes

**Closure structure** (in `cli/main.py:serve`):

```python
from study_tutor.tutoring.orchestrator import PlayerCoachOrchestrator
from study_tutor.tutoring.adapters.llm_player_adapter import LLMPlayerAdapter
from study_tutor.tutoring.adapters.llm_coach_adapter import LLMCoachAdapter

role_config = RoleConfig.load("tutor")

def _on_flag(turn_record: Any) -> None:
    """Logger-only callback per D-COACH-07."""
    logger.warning(
        "event=orchestrator_turn_flagged session=%s reason=%s",
        getattr(turn_record, "session_id", "?"),
        getattr(turn_record, "flag_reason", "?"),
    )

def orchestrator_factory() -> PlayerCoachOrchestrator:
    """Build a fresh orchestrator per turn (per-turn isolation invariant)."""
    return PlayerCoachOrchestrator(
        player=LLMPlayerAdapter(role_config),
        coach=LLMCoachAdapter(role_config),
        quote_verifier=None,           # ASSUM-LCA-015 — follow-up
        coach_handover=None,           # ASSUM-LCA-015 — follow-up
        on_flag=_on_flag,
    )

adapter = MCPAdapter(
    role_config=role_config,
    orchestrator_factory=orchestrator_factory,
    # other kwargs (write_helper, event_bus, graphiti_client) per TASK-GR-WIRE
)
```

**Coordination with TASK-GR-WIRE**: that task already wires
`write_helper` / `event_bus` / `graphiti_client` into the `serve` function.
This task adds `orchestrator_factory` to the same call. Do not regress the
TASK-GR-WIRE wiring.

**AC-LCA-10 calibration-fallback rationale**: per Context A Q5 of the
review, zero-revision turns during the demo are NOT a test failure when
the Coach prompt is minimal (Phase-1 plumbing only; calibration is
Phase-2). The integration test must explicitly document either a
revision-occurred result OR a calibration gap — but NOT fail on the
absence of revision alone.

**Smoke gate command**: `pytest -m "feat_lca and smoke"` — this is the
gate that runs after Wave 2 lands.
