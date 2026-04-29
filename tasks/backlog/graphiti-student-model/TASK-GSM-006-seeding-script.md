---
id: TASK-GSM-006
title: Write Lilymay baseline seeding script
task_type: scaffolding
parent_review: TASK-REV-7DC0
feature_id: FEAT-1773
wave: 4
implementation_mode: direct
complexity: 3
estimated_minutes: 60
status: in_review
priority: high
created: 2026-04-27 00:00:00+00:00
updated: 2026-04-27 00:00:00+00:00
dependencies:
- TASK-GSM-005
tags:
- graphiti
- seeding
- scaffolding
- lilymay
- idempotent
consumer_context:
- task: TASK-GSM-003
  consumes: GraphitiClient
  framework: graphiti-core async client
  driver: graphiti-core
  format_note: "Script obtains a real client via get_client(config) and exits non-zero\
    \ if client is None (seeding is not a degradation path \u2014 it must run against\
    \ a real Synology FalkorDB)"
- task: TASK-GSM-004
  consumes: SharedAsyncWriteHelper
  framework: asyncio fire-and-forget
  driver: asyncio
  format_note: Seed writes use helper.schedule_write(..., flush_id='SEED'); script
    awaits helper.drain() before exit to ensure all seed writes land before the script
    returns
- task: TASK-GSM-005
  consumes: StudentModelQueries
  framework: knowledge.queries
  driver: study_tutor
  format_note: After seeding, script calls get_student_state(client, 'lilymay') as
    a verification gate; non-empty StudentState confirms the seed landed
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-1773
  base_branch: main
  started_at: '2026-04-29T17:13:17.284417'
  last_updated: '2026-04-29T17:24:44.042888'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-29T17:13:17.284417'
    player_summary: "Built scripts/seed_student_model.py as the one-off Lilymay baseline\
      \ seeding script. Key design decisions:\n\n1. CC-13 single-call-site: every\
      \ write \u2014 Student, Subject, Text, AO, Topic, and TopicConfidence \u2014\
      \ is dispatched through GraphitiWriteHelper.schedule_write with flush_id='SEED'.\
      \ The script never touches add_episode directly. To route entity baselines through\
      \ the existing helper, I added a new SeedBaselineEpisode class (and extended\
      \ the EpisodeKind Literal to include 'seed_baseline') in src/s"
    player_success: true
    coach_success: true
---

# Task: Write Lilymay baseline seeding script

## Description

Create the one-off seeding script that populates Lilymay's baseline learner profile in the Synology FalkorDB. This is the integration gate for the whole feature — once seeding runs end-to-end and `get_student_state` returns the seeded baseline, FEAT-1773 is functionally complete.

Per build plan (Saturday evening, steps 9–11) and `phase-1-scope.md §FEAT-PH1-001` seeding script.

## Scope

**Script** (`scripts/seed_student_model.py`):

The script seeds:

1. **Student entity** — Lilymay (year_group=10, target_grade=7, group_id=`student:lilymay`)
2. **Subject entities** — English Literature (AQA 8702), English Language (AQA 8700)
3. **Text entities** — Macbeth (primary), A Christmas Carol (primary), Power & Conflict poetry cluster (primary), at least one study guide (secondary)
4. **AssessmentObjective entities** — AO1 through AO6 with their AQA descriptions
5. **Topic entities** — at least 6 topics across the seeded texts (e.g. "Macbeth's witches", "metaphor identification", "Scrooge's redemption arc")
6. **Initial TopicConfidence entries** — human-estimated bands for each topic (mix of struggling / developing / secure to give the planner real shape on day 1)
7. **`TopicConfidenceUpdatedEpisode` per initial confidence** — fire-and-forget via `GraphitiWriteHelper.schedule_write(..., flush_id="SEED")`

**Idempotency** (per `@seeding @idempotency` scenario in feature file):
- Re-running the script after Lilymay already exists must not create duplicate Student / Subject / Text / Topic entities
- Pre-flight: `await get_student_state(client, "lilymay")` — if non-empty, log `event=seeding_skipped, reason=already_seeded` and exit 0
- Episodes for confidence baselines are append-only (re-running creates new episodes; this is acceptable per `@seeding` scenario)

**Failure handling** (per `@seeding @store_unreachable` scenario):
- If `get_client(config)` returns `None` → log error and exit 2 (not 0 — seeding REQUIRES a working store)

**Verification gate** (per build-plan step 10):
- After seeding, call `get_student_state(client, "lilymay")` — assert non-empty, log a one-line summary of what was seeded
- If `helper.drain()` reports any abandoned writes → exit 3 with the abandoned count

## Acceptance Criteria

- [ ] Script entry point: `python scripts/seed_student_model.py [--config-path PATH]`
- [ ] Successful run against Synology FalkorDB: exit code 0, Lilymay's baseline visible via `get_student_state`
- [ ] Re-running the script: exit code 0, log line `event=seeding_skipped, reason=already_seeded`, no duplicate entities created
- [ ] Store-unreachable: exit code 2, log line `event=seeding_failed, reason=client_unavailable`
- [ ] Pending-writes-abandoned: exit code 3 with abandoned count if any
- [ ] At least one topic in each band (struggling / developing / secure) so the planner has shape on day 1
- [ ] Initial confidence values committed via the shared async write helper with `flush_id="SEED"` (not raw `add_episode` calls)
- [ ] All AOs (AO1–AO6) seeded with AQA-canonical descriptions

## Test Requirements

- Integration tests in `tests/integration/test_seeding.py` (gated on Synology FalkorDB):
  - Fresh seed: post-run, `get_student_state("lilymay")` returns non-empty with all 6 AOs and ≥ 6 topics
  - Idempotent seed: run twice, count of Student entities for `student:lilymay` is exactly 1
  - Store-unreachable: point at a non-routable host, run script, assert exit code 2
- Manual verification step (documented in script docstring): after seeding, run a Graphiti MCP query in Claude Desktop: `search_nodes(query="Lilymay", group_ids=["student:lilymay"])` and confirm the Student entity is returned with expected attributes

## Implementation Notes

- This is a **scaffolding** task — one-off setup, runs once per environment. No quality gates around architectural review.
- Keep the script readable as a sequence of writes — this is the canonical reference for "what does Lilymay's profile look like?".
- Do NOT commit the script's runtime output. Seeding happens once per environment.
- Use the shared async helper (`flush_id="SEED"`) to honour CC-13 even at seed time. The CC-13 single-call-site audit in TASK-GSM-004 would otherwise flag a bare `add_episode` here.
- After all writes are scheduled, call `await helper.drain()` to wait for the actual `add_episode` calls to land before the script exits — seeding is one of the few sites where awaiting is appropriate (not on a caller-facing path; we want the writes to be durable before the script returns).

## Seam Tests

```python
"""Seam tests for the seeding script — validate contracts from upstream tasks."""
import asyncio
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiClient")
def test_graphiti_client_required_at_seed_time():
    """Verify GraphitiClient contract is honoured by the seeding script.

    Contract: Script obtains a real client via get_client(config) and exits
              non-zero if client is None (seeding is NOT a degradation path).
    Producer: TASK-GSM-003
    """
    # Format assertion: a script-level helper that branches on client=None and
    # raises SystemExit(2) is the contract. Verify by importing the helper.
    from scripts.seed_student_model import require_client_or_exit
    import sys

    with pytest.raises(SystemExit) as exc_info:
        require_client_or_exit(client=None)
    assert exc_info.value.code == 2  # store unreachable per @seeding scenario


@pytest.mark.seam
@pytest.mark.integration_contract("SharedAsyncWriteHelper")
def test_seed_writes_use_seed_flush_id():
    """Verify SharedAsyncWriteHelper contract is honoured by the seeding script.

    Contract: Seed writes use helper.schedule_write(..., flush_id='SEED');
              script awaits helper.drain() before exit.
    Producer: TASK-GSM-004
    """
    # Format assertion: every helper.schedule_write call inside the seed script
    # passes flush_id="SEED". Verify by AST scan.
    import ast
    import pathlib

    src = pathlib.Path("scripts/seed_student_model.py").read_text()
    tree = ast.parse(src)

    seen_flush_ids = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "schedule_write"
        ):
            for kw in node.keywords:
                if kw.arg == "flush_id" and isinstance(kw.value, ast.Constant):
                    seen_flush_ids.append(kw.value.value)

    assert len(seen_flush_ids) > 0, "seeding script must call helper.schedule_write at least once"
    assert all(fid == "SEED" for fid in seen_flush_ids), (
        f"All seed writes must use flush_id='SEED', got: {seen_flush_ids}"
    )


@pytest.mark.seam
@pytest.mark.integration_contract("StudentModelQueries")
def test_post_seed_verification_gate():
    """Verify StudentModelQueries contract is honoured as the post-seed gate.

    Contract: After seeding, script calls get_student_state(client, 'lilymay')
              as a verification gate; non-empty StudentState confirms seed landed.
    Producer: TASK-GSM-005
    """
    # Format assertion: the script imports get_student_state and uses it as a gate
    import ast
    import pathlib

    src = pathlib.Path("scripts/seed_student_model.py").read_text()
    tree = ast.parse(src)

    found_query_import = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", "") or ""
            names = [n.name for n in node.names]
            if "queries" in module and "get_student_state" in names:
                found_query_import = True
                break

    assert found_query_import, (
        "Seeding script must import get_student_state from study_tutor.knowledge.queries "
        "to act as the post-seed verification gate"
    )
```
