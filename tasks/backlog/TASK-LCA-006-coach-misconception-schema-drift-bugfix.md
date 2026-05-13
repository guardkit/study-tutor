---
id: TASK-LCA-006
title: "Coach misconception schema drift — CoachVerdict.misconceptions[0] arrives as str, fails pydantic model_type validation"
task_type: bugfix
feature_id: FEAT-6CC5
feature_slug: mcp-llm-player-coach-adapters
implementation_mode: task-work
complexity: 4
estimated_minutes: 120
status: backlog
priority: medium
created: 2026-05-13T00:00:00Z
updated: 2026-05-13T00:00:00Z
related:
  - TASK-LCA-002
  - TASK-LCA-004
  - src/study_tutor/tutoring/coach/factory.py
  - src/study_tutor/tutoring/coach/rubric.py
  - src/study_tutor/tutoring/adapters/llm_coach_adapter.py
  - src/study_tutor/tutoring/orchestrator.py
tags:
  - coach
  - pydantic-v2
  - schema-drift
  - degraded-quality
  - feat-lca
  - phase-1
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Coach misconception schema drift — degraded coach verdict path

## Provenance

Surfaced during the multi-specialist OpenWebUI demo verification on
2026-05-13 (DDD South West dress-rehearsal target). The tutor turn
returned coherent content but the Coach verdict path silently degraded
to the `coach_unreachable` fallback throughout the session — see
`jarvis` repo commit `ef31345` and its [`RESULTS file`](../../../jarvis/docs/runbooks/RESULTS-jarvis-multi-specialist-openwebui-dddsw-demo-2026-05-13.md)
§Known issues (1). Captured in container logs from
`study-tutor-gcse-tutor-1` on 2026-05-12 at 19:22:47 and 19:23:17:

```
WARNING study_tutor.tutoring.orchestrator: Coach unreachable —
  falling back to unevaluated Player response
WARNING study_tutor.cli.main: event=orchestrator_turn_flagged
  reason=coach_unreachable: MalformedCoachOutputError:
  Coach output JSON failed CoachVerdict schema validation:
  1 validation error for CoachVerdict
misconceptions.0
  Input should be a valid dictionary or instance of
  MisconceptionObservation [type=model_type,
  input_value='The tutor treats the top...or quadratic equations.',
  input_type=str]
  For further information visit
  https://errors.pydantic.dev/2.13/v/model_type
```

## Root cause hypothesis

The coach LLM is returning `misconceptions` as `list[str]` (free-text
descriptions like `"The tutor treats the top…"`), but
[`factory.py:268`](../../src/study_tutor/tutoring/coach/factory.py#L268)
declares:

```python
class CoachVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ...
    misconceptions: list[MisconceptionObservation] = Field(default_factory=list)
```

and `MisconceptionObservation`
([`factory.py:189`](../../src/study_tutor/tutoring/coach/factory.py#L189))
requires `topic_name: str` (non-empty) + `misconception_text: str`
(non-empty) plus two defaulted fields. Pydantic v2 rejects a bare
string as `type=model_type` (it cannot coerce `str` into a `BaseModel`
without a validator).

The rejection is wrapped in `MalformedCoachOutputError` by
[`rubric.py:593`](../../src/study_tutor/tutoring/coach/rubric.py#L593),
re-raised through
[`llm_coach_adapter.py:113`](../../src/study_tutor/tutoring/adapters/llm_coach_adapter.py#L113),
caught in
[`orchestrator.py`](../../src/study_tutor/tutoring/orchestrator.py)
at `_fallback_coach_unreachable` (line 696), which logs the warning
and returns the Player's unevaluated response. The session **continues
to function** — the learner sees a tutor reply — but every turn is
silently flagged `coach_unreachable`, the revision loop never runs, and
coach-scored quality + misconception persistence are entirely bypassed.

## Why this matters

Two distinct regressions:

1. **Misconceptions never reach Graphiti.** The dispatch path at
   [`rubric.py:846`](../../src/study_tutor/tutoring/coach/rubric.py#L846)
   (`for observation in verdict.misconceptions: ...`) is unreachable
   because verdict construction fails before dispatch. Per the
   misconceptions design (TASK-GSM-002), every turn-end observation is
   supposed to land in the knowledge store; right now zero
   observations are landing.
2. **Revision loop disabled.** The `decision: Literal["accept","revise"]`
   verdict field is never produced, so the orchestrator can't gate on
   `revise` — every Player response goes out unrevised.

The downstream effect is invisible to the learner in a single turn,
but **session quality degrades to "Player-only" mode**, which defeats
the LLM-Player-Coach adapter design from FEAT-6CC5.

## Acceptance criteria

- **AC-LCA-06-01** ▸ When the LLM coach emits `misconceptions` as a
  list of strings, the verdict still validates (string → coerced to
  `MisconceptionObservation` with `misconception_text=<string>` and
  `topic_name` set from session context or a sentinel like
  `"unspecified"`). The turn must NOT fall back to
  `coach_unreachable` purely because of this drift.
- **AC-LCA-06-02** ▸ When the LLM coach emits `misconceptions` correctly
  (as a list of objects with `topic_name` + `misconception_text`), the
  existing happy-path validation continues to work — no regression on
  the canonical schema.
- **AC-LCA-06-03** ▸ When the LLM coach emits invalid misconceptions
  (e.g. `[{"foo": "bar"}]` — neither a string nor a recognisable
  observation), the orchestrator **still** falls back to
  `coach_unreachable` — preserve the safety semantics for genuine
  malformed output. Don't relax `extra="forbid"` on `CoachVerdict`.
- **AC-LCA-06-04** ▸ Coach prompt is tightened (in
  `src/study_tutor/tutoring/coach/...` prompt assets) to emit the
  canonical object shape. Belt-and-braces: the prompt change reduces
  the *rate* of drift; the validator coercion catches what slips
  through.
- **AC-LCA-06-05** ▸ Unit tests cover (a) the string-coercion path,
  (b) the canonical-object happy path, (c) the genuinely-malformed
  rejection path, and (d) a regression test using a captured live
  payload from the 2026-05-12 logs.

## Suggested fix shape

Three layers, in order of priority:

1. **Tighten the coach prompt** (FEAT-6CC5 prompt asset). Move
   `misconceptions` from a free-form bullet list into an explicit
   JSON template:
   ```json
   "misconceptions": [
     {"topic_name": "<topic>", "misconception_text": "<observation>"}
   ]
   ```
   This is the primary fix — drift should not be the steady state.

2. **Add a pydantic `model_validator(mode="before")` on
   `CoachVerdict`** that walks `misconceptions` and coerces bare
   strings into `MisconceptionObservation(topic_name="unspecified",
   misconception_text=<string>)`. This is the safety net for prompt
   drift. Use `mode="before"` (not a `field_validator`) so the
   coercion happens before per-field validation runs.

3. **Telemetry** — emit a structured `coach_misconception_coerced`
   event whenever the validator coerces a string. This lets us track
   prompt drift over time without it silently degrading the coaching
   loop.

Do **not** loosen `CoachVerdict.extra="forbid"` — that constraint is
load-bearing per [`factory.py:247-249`](../../src/study_tutor/tutoring/coach/factory.py#L247)
(prompt-injection surface management).

## Out of scope

- Reviewing or revising the Coach scoring rubric / weighted_total
  logic.
- Changing `MisconceptionObservation` shape (the canonical surface
  from TASK-GSM-002 is stable).
- The downstream Graphiti `write_misconception(...)` helper — this
  task only restores the verdict-validation path; the downstream
  dispatch is already correct.

## Verification

After fix lands, re-run the multi-specialist OpenWebUI demo runbook
(`jarvis/docs/runbooks/RUNBOOK-jarvis-multi-specialist-openwebui-dddsw-demo.md`)
or the local CLI `tutor-cli` smoke. `docker logs
study-tutor-gcse-tutor-1` should show **zero** `coach_unreachable`
warnings across a multi-turn tutoring session on a topic where
misconceptions are likely (e.g. Macbeth language-analysis with a
deliberately-weak Player turn). Optionally, `coach_misconception_coerced`
events may appear — that's the telemetry path proving the safety net
caught a drift.
