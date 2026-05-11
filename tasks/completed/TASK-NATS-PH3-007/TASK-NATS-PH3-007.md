---
id: TASK-NATS-PH3-007
title: "Bug #6: add AGENT_MODELS__COACH_MODEL env vars to docker-compose.study-tutor.yml"
task_type: bug_fix
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 12
implementation_mode: task-work
complexity: 3
estimated_minutes: 45
status: completed
priority: critical
created: 2026-05-10 00:00:00+00:00
updated: 2026-05-10T00:00:00+00:00
completed: 2026-05-10T00:00:00+00:00
completed_location: tasks/completed/TASK-NATS-PH3-007/
dependencies:
  - TASK-NATS-PH3-002
tags:
  - nats
  - docker
  - compose
  - coach-model
  - phase-3
  - bug-6
  - demo-blocker
  - feat-nats
  - feat-6cc5
demo_deadline: 2026-05-16
source_runbook: docs/runbooks/RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md
---

# Task: Bug #6 — add AGENT_MODELS__COACH_MODEL env vars to docker-compose.study-tutor.yml

## Background

Surfaced during the first runbook verification pass on 2026-05-10 (run-1).
After Bug #5 (Dockerfile missing runtime assets) was patched, the container
immediately crash-looped on the next boot with:

```
study_tutor.llm.client.LLMProviderError: AGENT_MODELS__COACH_MODEL is not set.
Phase-1 requires the Coach provider to be explicitly configured and to differ
from AGENT_MODELS__REASONING_MODEL (the D3 two-provider invariant ...).
```

Raised at `src/study_tutor/llm/client.py:85` via the call chain
`_build_nats_runtime` → `MCPAdapter.__init__` → `orchestrator_factory()`
→ `_default_coach_model()`.

The constraint is deliberate (D-COACH-05 / FEAT-6CC5): there is **no
fallback** — the Coach model must be explicitly set and must differ from
the Reasoning model alias. `docker-compose.study-tutor.yml` set
`AGENT_MODELS__REASONING_MODEL` (Player) but never set the Coach
counterpart.

This task is the **follow-up to TASK-NATS-PH3-002** (the original compose
task). The in-tree patch (uncommitted at run-end) already demonstrates the
correct fix — this task's job is to formalise it with a comment, a
`TUTOR_COACH_MODEL` override knob, and regression coverage.

## Scope

File affected: `study-tutor/docker-compose.study-tutor.yml`

1. **Formalise the in-tree patch.** The working-tree patch (applied during
   the 2026-05-10 run) added:

   ```yaml
   # Coach provider — must differ from REASONING_MODEL (D3 two-provider
   # invariant, D-COACH-05 / FEAT-6CC5; no fallback is permitted).
   # Override with TUTOR_COACH_MODEL / TUTOR_COACH_ENDPOINT.
   AGENT_MODELS__COACH_MODEL: ${TUTOR_COACH_MODEL:-qwen36-workhorse}
   AGENT_MODELS__COACH_ENDPOINT: ${TUTOR_COACH_ENDPOINT:-http://host.docker.internal:9000/v1}
   ```

   Verify the comment and both lines are present and correctly placed
   alongside the existing `AGENT_MODELS__REASONING_MODEL` block.

2. **Decide on the default Coach model alias.** `qwen36-workhorse` was
   operator-confirmed during the run (satisfies the D3 two-provider
   invariant against `gemma4-tutor` / Reasoning). However this is **not
   just a plumbing choice** — see the "Real call" section below.

3. **Add a regression test** to `tests/unit/test_compose_structure.py` (or
   a sibling file in the same module) verifying:
   - `AGENT_MODELS__COACH_MODEL` is present in the compose env block.
   - `AGENT_MODELS__COACH_MODEL` default value differs from the
     `AGENT_MODELS__REASONING_MODEL` default value (the D3 invariant cannot
     be satisfied if both default to the same alias).
   - The `TUTOR_COACH_MODEL` override knob wires through correctly (i.e.
     the compose YAML references `${TUTOR_COACH_MODEL:-...}`, not a
     hard-coded value).

## Real call: default Coach model alias

The `qwen36-workhorse` alias was the quickest available fix during the run
because it was already loaded on the llama-swap host and is unambiguously
different from `gemma4-tutor`. However:

- `qwen36-workhorse` is **also the supervisor's model on the jarvis side**.
  On demo day (2026-05-16) a live jarvis-to-tutor dispatch will be running
  concurrently with the tutor's internal Coach calls. Both compete for the
  same llama-swap slot. GPU contention on the GB10 llama-swap at demo time
  is a real risk, not a theoretical one.
- Available alternatives on the same host (from `llama-swap /v1/models`
  captured at Gate 0.4):
  - `qwen-graphiti` — in use for Graphiti extraction (same contention
    concern for any session that writes an episode).
  - `architect-agent` — on-host but tuned for architecture analysis; using
    it as a tutor Coach would be semantically odd and may produce
    lower-quality pedagogical scaffolding.
  - `gemma4-tutor` is ruled out — same alias as the Reasoning model,
    violates D3.

**Decision required by the rehearsal day (2026-05-15):** either accept the
contention risk and document it in the runbook, or nominate a quieter alias
and verify it holds the D3 invariant. Profiling a `tutor_start_session` +
`tutor_turn` round-trip with `qwen36-workhorse` as Coach alongside a
concurrent jarvis dispatch would settle this concretely.

## Acceptance criteria

- [ ] **AC-PH3-007-1** — `docker compose up -d` reaches
  `NATSAdapter ready for agent 'gcse-tutor'` without an
  `LLMProviderError`. No container crash-loop. (Regression against Bug #6.)
- [ ] **AC-PH3-007-2** — The D3 two-provider invariant holds: the Coach
  model alias in the compose env block differs from the Reasoning model
  alias. (`AGENT_MODELS__COACH_MODEL` default ≠ `AGENT_MODELS__REASONING_MODEL`
  default.)
- [ ] **AC-PH3-007-3** — `TUTOR_COACH_MODEL` override path works:
  `TUTOR_COACH_MODEL=some-other-alias docker compose config` surfaces
  `AGENT_MODELS__COACH_MODEL: some-other-alias`. Verified by the regression
  test added to `tests/unit/test_compose_structure.py` (or sibling).
- [ ] **AC-PH3-007-4** — The compose env block includes an inline comment
  explaining why Coach must differ from Reasoning, with a reference to
  D-COACH-05 / FEAT-6CC5. Future operators must not silently set both to
  the same alias.
- [ ] **AC-PH3-007-5** — Gate 1.2 in the runbook passes: `docker exec`
  (or equivalent `compose config` check) confirms both
  `AGENT_MODELS__COACH_MODEL` and `AGENT_MODELS__REASONING_MODEL` are
  propagated into the container env with distinct values.
- [ ] **AC-PH3-007-6** — All modified files pass project lint/format checks
  with zero errors.

## Implementation notes

- The in-tree patch in `docker-compose.study-tutor.yml` (from the 2026-05-10
  run) is the correct shape — this task's job is to review it for
  correctness, land it with appropriate comment and test coverage, then
  commit.
- Mirror the existing `TUTOR_LOCAL_MODEL` pattern for the override knob:
  `AGENT_MODELS__REASONING_MODEL: ${TUTOR_LOCAL_MODEL:-gemma4-tutor}`.
  The Coach knob should follow the same idiom:
  `AGENT_MODELS__COACH_MODEL: ${TUTOR_COACH_MODEL:-<chosen-alias>}`.
- Source of truth for the no-fallback constraint: `src/study_tutor/llm/client.py:85`.
  The comment in the compose file should not attempt to replicate the full
  decision rationale — link to D-COACH-05 / FEAT-6CC5 and let the code be
  authoritative.
- The regression test should load the compose YAML via `yaml.safe_load` (as
  the existing `test_compose_structure.py` likely does) and assert on the
  env mapping — no need to invoke Docker or a live NATS for this gate.

## Evidence

- Runbook results file: `docs/runbooks/RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md`
  — Bug #6 section.
- Container traceback:
  `docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log`
  (the second crash-loop layer, post Bug #5 fix).
- Gate 1.2 passing evidence in the same results file confirms that once the
  patch was applied, `AGENT_MODELS__COACH_MODEL=qwen36-workhorse` appeared
  correctly in `docker exec env`.

## Coach validation

```bash
# Verify compose file validates
docker compose -f docker-compose.study-tutor.yml config | \
  grep -E 'AGENT_MODELS__(COACH|REASONING)_MODEL'

# Verify two-provider invariant visible in rendered config
docker compose -f docker-compose.study-tutor.yml config | \
  python3 -c "
import sys, re
lines = sys.stdin.read()
coach   = re.search(r'AGENT_MODELS__COACH_MODEL:\s*(\S+)', lines)
reason  = re.search(r'AGENT_MODELS__REASONING_MODEL:\s*(\S+)', lines)
assert coach and reason, 'Missing env vars'
assert coach.group(1) != reason.group(1), 'D3 invariant violated: same alias'
print('D3 invariant OK:', reason.group(1), '!=', coach.group(1))
"

# Run regression test
python -m pytest tests/unit/test_compose_structure.py -v -k coach
```
