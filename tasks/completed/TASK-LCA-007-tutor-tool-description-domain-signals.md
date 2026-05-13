---
id: TASK-LCA-007
title: "Add domain signals to gcse-tutor ToolCapability descriptions so the jarvis supervisor reliably dispatches GCSE tutoring prompts"
task_type: bugfix
feature_id: FEAT-6CC5
feature_slug: mcp-llm-player-coach-adapters
implementation_mode: task-work
complexity: 2
estimated_minutes: 30
status: completed
priority: high
created: 2026-05-13T10:30:00Z
updated: 2026-05-13T10:30:00Z
completed: 2026-05-13T11:10:00Z
related:
  - TASK-LCA-006
  - src/study_tutor/adapters/manifest.py
tags:
  - routing
  - capability-description
  - feat-lca
  - demo-blocker
  - dddsw-2026-05-16
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: gcse-tutor ToolCapability descriptions lack the domain signals jarvis's supervisor needs for reliable routing

## Provenance

Surfaced during the multi-specialist OpenWebUI demo verification **run-2**
on 2026-05-13 (~10:25 UTC), after the systemd-managed
[`jarvis-serve-nats.service`](https://github.com/guardkit/jarvis) was put
in place. Same Turn 2 prompt as the morning's run-1
([RESULTS-2026-05-13](https://github.com/guardkit/jarvis/blob/main/docs/runbooks/RESULTS-jarvis-multi-specialist-openwebui-dddsw-demo-2026-05-13.md)):

> "*Now please start a GCSE English Literature tutoring session on
>  Macbeth, focused on AO1 and AO2…*"

**Run-1:** supervisor dispatched five envelopes on
`agents.command.gcse-tutor` (`tutor_start_session` + 3× `tutor_turn` +
`tutor_session_end`), all preserving a single tutor `session_id`.

**Run-2:** **zero** envelopes on `agents.command.gcse-tutor`. The
supervisor self-handled the prompt with its own reasoning model
(`qwen36-workhorse`) and produced a Jarvis-rendered "📚 Tutoring
Framework" reply. The recap turn correctly attributed the tutor as
"*Tutor (general-purpose subagent)*" — i.e. there was no specialist
dispatch.

The TASK-LCA-006 coach-pydantic fix (study-tutor@3ad9abd) is **not
exercised** in this regression because gcse-tutor never receives a
request to begin with.

## Root cause

The four `ToolCapability` entries in
[`src/study_tutor/adapters/manifest.py:28-128`](../../src/study_tutor/adapters/manifest.py)
have descriptions that focus on **technical contract** (sync vs async,
session_id minting, parameter list) and contain **zero domain signals**
about what the tutor teaches:

```
"Start a new tutoring session for the given student. Sync; returns
 session_id immediately; LLM model is warmed up in the background as
 fire-and-forget. Topic and player_model are optional overrides."
```

Compare to architect-agent's tool descriptions (which the supervisor
dispatched to **reliably both runs**):

```
"Provide architectural judgment on a proposal or question (Mode 2)…"
"…detect drift, undocumented components, ADR contradictions…"
"…assess technical feasibility of a product idea…"
```

Architect tool descriptions are saturated with **domain-specific terms**
(ADR, C4, drift, feasibility, alignment). The supervisor's reasoning
model pattern-matches "user wants architecture review" → these
descriptions → high-confidence dispatch.

For tutor, the supervisor sees a generic "tutoring session" tool, a
GCSE Macbeth prompt, and the reasoning is genuinely ambiguous: *"is
this a job for the dedicated tool, or can I tutor English Lit myself
with general knowledge?"* The answer is non-deterministic — exactly
what run-2 demonstrated.

**Note on the existing `_TUTOR_INTENTS` block at
[manifest.py:132-153](../../src/study_tutor/adapters/manifest.py#L132-L153):**
the intent capability *does* advertise GCSE + subject signals
(`signals=["GCSE", "english", "maths", ...]`). Whether jarvis surfaces
`IntentCapability` into the supervisor's tool-selection prompt is a
**separate question** that has not been answered. Even if it does, the
tool descriptions still need strengthening so that the routing signal
comes from multiple reinforcing layers.

## Why this matters

Demo 2026-05-16 DDD South West is **three days away**. The Turn 2
beat — "*supervisor routes a GCSE Macbeth prompt to a different
specialist on a different model, demonstrating routing-by-meaning*" —
is the talk's strongest evidence for cross-specialist gateway value.
If the supervisor self-handles Turn 2 on stage, the talk loses its
central narrative arc.

## Acceptance criteria

- **AC-LCA-07-01** ▸ Each of the four entries in `_TUTOR_TOOLS`
  (`tutor_start_session`, `tutor_turn`, `tutor_session_status`,
  `tutor_session_end`) has a description that explicitly mentions at
  least one of: GCSE-level, A-Level, English Literature, English
  Language, AO1, AO2, AO3, AO4, secondary-school, GCSE subjects, or
  Socratic tutoring.
- **AC-LCA-07-02** ▸ A focused tutor smoke (CLI
  `nats request agents.command.jarvis` with a GCSE Macbeth prompt
  matching the demo's Turn 2 wording) dispatches to gcse-tutor on
  **at least 3 out of 3 consecutive trials**, evidenced by envelopes
  on `agents.command.gcse-tutor` for each trial.
- **AC-LCA-07-03** ▸ Existing tool semantics preserved: each
  description still names the sync/async mode, return shape signal
  (session_id / reply text / status / confirmation), and any
  required parameters. The change is **additive** — domain signals
  added in front of or after the contract semantics, not replacing
  them.
- **AC-LCA-07-04** ▸ gcse-tutor container boots cleanly with the new
  manifest — no `pydantic.ValidationError`, no fleet.register failure,
  the agent record appears in `agent-registry` KV within 5s of
  container start.
- **AC-LCA-07-05** ▸ Unit tests covering the manifest factory's tool
  descriptions assert at least one domain-keyword presence per
  description; future drift back to domain-blind descriptions is
  caught by `pytest tests/unit/adapters/test_manifest.py` (or
  wherever the existing manifest tests live).

## Suggested implementation

Edit
[`src/study_tutor/adapters/manifest.py`](../../src/study_tutor/adapters/manifest.py)
and rewrite the four `description=` fields. Example for
`tutor_start_session`:

```python
description=(
    "Start an interactive GCSE-level tutoring session. Covers "
    "English Literature, English Language, Maths, Sciences, "
    "History, and other GCSE subjects with Socratic dialogue "
    "scaffolded against AO1/AO2/AO3/AO4 assessment objectives. "
    "Use for any learner preparing for GCSE examinations or "
    "revising specific topics. Sync; returns session_id "
    "immediately; LLM model is warmed up in the background as "
    "fire-and-forget. Topic and player_model are optional "
    "overrides."
),
```

Same pattern for the other three tools (each gains at least one
domain phrase that names what gcse-tutor *teaches*).

Then:

```bash
cd ~/Projects/appmilla_github/study-tutor
docker compose -f docker-compose.study-tutor.yml build
docker compose -f docker-compose.study-tutor.yml up -d --force-recreate
# Verify the new descriptions are in KV
nats kv get agent-registry gcse-tutor --raw | jq '.tools[]|{name,description}'
# Then fire the demo Turn 2 prompt via CLI smoke 3×
```

## Out of scope

- Adding an agent-level `description` field to `AgentManifest` — that
  would require nats-core changes and is a separate task. Both
  architect-agent and gcse-tutor currently have empty agent-level
  descriptions, and architect-agent routes fine without one. The
  routing signal lives in tool descriptions.
- Investigating whether jarvis surfaces `IntentCapability` into the
  supervisor's prompt. File as a separate jarvis-side task
  (TASK-J-ROUTE-001 or similar) if it turns out IntentCapability isn't
  being used.
- Tuning the supervisor model temperature in jarvis. That's a
  jarvis-side knob and may have wider regressions.

## Verification

After implementation:

1. **Three CLI smoke trials** with the GCSE Macbeth Turn 2 prompt
   exactly as worded in the demo runbook. Capture `nats sub
   agents.command.>` envelopes for each trial; expect 1+
   `tutor_start_session` and 1+ `tutor_turn` envelope on
   `agents.command.gcse-tutor` for each.
2. **End-to-end re-run** of the demo runbook's Phase 4 from
   OpenWebUI to confirm the supervisor still dispatches the tutor
   path through the gateway leg (not just the CLI smoke leg).
3. **Recap turn (Turn 4)** must attribute the tutor as "gcse-tutor"
   or equivalent, not as "general-purpose subagent".

---

## Outcome (2026-05-13 — closure note)

**Implementation:** descriptions rewritten as proposed (see `src/study_tutor/adapters/manifest.py`); container rebuilt + KV manifest re-published with the new descriptions; 22 manifest tests pass; descriptions are richer + more semantically loaded than before.

**Misdiagnosis acknowledged:** these description changes did **NOT** resolve the routing regression on their own. After implementation, 6 consecutive CLI smoke trials (`lca-007-verify-*` + `lca-007-fresh-*`) still produced 0 tutor dispatches. Further investigation traced the actual root cause to jarvis's `stub_capabilities.yaml`, which lacked a `gcse-tutor` block entirely — fixed in [`jarvis@TASK-DSR-005`](https://github.com/guardkit/jarvis/blob/main/tasks/completed/feat-dsr-dispatch-stub-resolver-fix/TASK-DSR-005-stub-yaml-patch-gcse-tutor.md). After TASK-DSR-005 landed, the same Turn 2 prompt dispatches reliably (3/3 trials, 5 cumulative envelopes).

**Why keep TASK-LCA-007 changes anyway:**
- Richer tool descriptions live in the KV manifest; they reach any downstream consumer that reads from live KV (e.g. the dispatch resolver post TASK-DSR-003 W2, future tools that surface live capabilities)
- They mirror the language used in the jarvis stub block per TASK-DSR-005, so the live and stub paths stay descriptively consistent
- AC-LCA-07-01, AC-LCA-07-03, AC-LCA-07-04, AC-LCA-07-05 all pass on the implementation as-written; only AC-LCA-07-02 (dispatch verification) required TASK-DSR-005 to satisfy

**Status:** completed (closed with misdiagnosis note for the historical record).
