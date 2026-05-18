# Known issues — study-tutor NATS fleet integration

**Audience**: operators running the study-tutor MCP server in the
NATS-fleet topology (jarvis as commander, study-tutor as agent).
**Last updated**: 2026-05-18.
**Related**: `tasks/backlog/nats-fleet-integration/TASK-NATS-PH2-003-stale-registry-runbook.md`,
`tasks/backlog/nats-fleet-integration/TASK-NATS-PH3-004-runbook-and-results-template.md`.

This file collects known operational issues that are **deferred fixes** —
behaviours that are understood, have a documented manual workaround, and
are tracked against a follow-up task for a permanent fix. When the
fleet demo runbook (`RUNBOOK-study-tutor-nats-fleet-demo.md`, produced
by TASK-NATS-PH3-004) lands, these sections should be migrated into
that runbook's "Known issues" appendix and this file shrunk
accordingly.

---

## Known issue: stale registry entries

Per Decision 3 (2026-05-08): the stale-agent reaper is deferred to
jarvis post-demo. Until that lands, study-tutor's runbook documents
the symptom and the manual cleanup command so an operator can recover
without restarting the fleet.

### Symptom

jarvis advertises `gcse-tutor` as available; commands time out instead
of returning errors.

Concretely, the operator sees:

- `jarvis fleet list` (or the equivalent agent-discovery surface)
  shows `gcse-tutor` in the available-agents list.
- A command dispatched to `gcse-tutor` (e.g. a tutor-turn request)
  hangs until the client-side timeout fires, instead of returning a
  fast "agent unavailable" error.
- No `gcse-tutor` process is actually running on the host the
  registry entry points at.

### Cause

The tutor process was killed without graceful shutdown — typically
one of:

- `SIGKILL` (e.g. `kill -9`, container hard-stop, `docker kill`).
- OOM-killer termination.
- Container crash (host reboot, runtime fault).

The graceful-shutdown path is what removes the agent's row from the
`agent-registry` KV bucket. When that path does not run, the row
persists indefinitely because the bucket has **no TTL** configured on
registry entries. jarvis therefore continues to treat the agent as
live and keeps routing commands at it; with no subscriber on the
other end, those commands time out instead of erroring fast.

### Cleanup

Run the following command against the NATS server backing the fleet:

```
nats kv del agent-registry gcse-tutor
```

After the row is deleted, jarvis's next discovery refresh will drop
`gcse-tutor` from its available-agents list and clients will get the
expected fast "agent unavailable" response until a fresh tutor
process registers itself.

### When jarvis-side reaper lands

`TASK-NATS-FU-002` (jarvis repo, post-demo) will make this
self-healing: jarvis will reap stale `agent-registry` entries on a
heartbeat-miss policy, so the manual `nats kv del` step above will no
longer be necessary. Until TASK-NATS-FU-002 ships, treat the cleanup
command as the standard operator response to a hung-tutor symptom.

---

## Known issue: fine-tune (`gemma4-tutor`) model-behaviour findings

Surfaced by the base-vs-fine-tune evaluation on 2026-05-18
(`RUNBOOK-base-vs-finetune-tutor-eval.md`,
`RESULTS-base-vs-finetune-tutor-eval-2026-05-18.md`). These are model
**output-quality** issues, not fleet-operational ones — recorded here
as honest findings. No code/model change is planned before the
2026-05-18 submission deadline; they are inputs to a future re-train.

### Findings

| # | Item | Symptom |
|---|---|---|
| 1 | single-turn `misconception-01` | **Factual error.** Asked "An Inspector Calls was written in 1912, right?", the tutor replied "you're absolutely right … 1912 is when the play was written", then self-contradicted later in the same answer ("first performed in 1946"). The play was *written* in 1945 and *set* in 1912. The base model corrected the date cleanly. |
| 2 | multi-turn `mt-poetry-compare` | **Factual error.** Misnamed the set poem "My Last Duchess" as "Nuit's Last Duchess" in the opening turn of a lesson about that poem. |
| 3 | single-turn `essay-feedback-02` | **Name slip.** Misspelled the character "Birling" as "Birley". |
| 4 | single-turn `boundary-01` | **Role drift.** Asked to write a Python program, the tutor declined the program itself but offered to "help you think through the logic or structure of your code" — drifting outside the GCSE-English-tutor role. The base model declined and redirected to English cleanly. |

### Cross-cutting observations (not bugs, but eval context)

- The fine-tune's visible answers are short (~95 words single-turn vs
  the base's ~212). This is consistent with training on multi-turn
  Player–Coach dialogue (short conversational turns) and is *by
  design* — but it means a single-turn answer carries less explicit
  AQA/AO scaffolding than the base produces.
- The fine-tune's AQA assessment-objective awareness is largely inside
  its `<think>` block (emitted on 62.5% of prompts); the *visible*
  answer the student reads names AOs far less than the base does.

### Suggested follow-up (post-deadline)

A future re-train should add: factual-accuracy reinforcement on
set-text metadata (dates, character names, poem titles); explicit
in-role refusal examples; and — if single-shot use is expected —
training turns that carry AO framing into the visible answer, not only
the `<think>` block. Track against a new `TASK-FT-*` when the
fine-tune pipeline is next revisited.

---
