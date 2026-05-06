# TASK-RVP-001 — Revise decision path: trace report

**Status:** No architectural gap. The revise path is reachable end-to-end and is now covered by an explicit unit test (`tests/unit/tutoring/test_revise_path_reachable.py`) in addition to the pre-existing AC-002 / AC-003 tests in `tests/unit/tutoring/test_orchestrator.py`.

**Scope:** Plumbing-only verification per the task description. No Coach quality, rubric, or RAG work.

## TL;DR

The user's reproduction note expected to see `decision="revise"` returned to the MCP caller and observed only `accept` (×9) and `fallback` (×1). The reason is **terminology**, not a code gap:

- `CoachVerdict.decision` is `Literal["accept", "revise"]` (factory.py:259) — the **Coach** decides whether the response is good enough.
- `TurnResult.decision` is `Literal["accept", "exhausted", "fallback"]` (orchestrator.py:73) — the **orchestrator** never returns `"revise"`. A `revise` verdict drives the revision loop, and the loop's outcome is one of:
  - `accept` (a subsequent attempt was good enough)
  - `exhausted` (the cap of `MAX_REVISION_ATTEMPTS` (3) was hit without acceptance)
  - `fallback` (the Coach raised mid-revision)

So the expected production fingerprint of "the revise path was exercised" is **not** `decision == "revise"`; it is **`attempts > 1`** on a `TurnResult` with any of the three terminal decisions. Across the 10 demo turns, `attempts > 1` was indeed never observed — but that means the qwen36-workhorse Coach (without ChromaDB RAG) never returned a `revise` verdict (or the parser couldn't extract one), not that the orchestrator was broken.

## Required traces (acceptance criteria 1–3)

### 1. `run_turn` in `src/study_tutor/tutoring/orchestrator.py`

- The orchestrator's `TurnDecision` Literal is **only** `("accept", "exhausted", "fallback")`. There is no `"revise"` value to return (orchestrator.py:73).
- After the first Player turn (orchestrator.py:467–476), the Coach is called via `_evaluate_with_metadata` (orchestrator.py:493–506). If the Coach raises, the helper `_fallback_coach_unreachable` returns `decision="fallback"` with `attempts=1` (orchestrator.py:682–716). This is the only path to `fallback` on the first turn — it is **not** triggered by `verdict.decision == "revise"`.
- If the Coach returns a verdict and `verdict.decision == "accept"` (orchestrator.py:511), the orchestrator returns immediately with `decision="accept"`, `attempts=1`.
- If the Coach returns a verdict whose `decision` is anything other than `"accept"` (i.e. `"revise"` — the only other admissible value per the schema), control falls through into the bounded revision loop at orchestrator.py:533: `for attempt_index in range(2, self._max_revision_attempts + 1)`. This is the **revise branch**.
- Inside the loop the orchestrator calls `self._player.revise(...)` (orchestrator.py:535–540) with the **previous response** and the **structured `RubricFeedback`** from the previous verdict — never the Coach's free-text `reasoning` (ASSUM-008). This is what the task means by "the orchestrator's `LLMPlayerAdapter.revise()` call".
- The revised response is re-evaluated by the Coach (orchestrator.py:565–581). On `accept` the orchestrator returns with `decision="accept"`, `attempts=attempt_index` (so `attempts == 2` on the first successful revision).
- If the loop exits without an `accept`, the orchestrator picks the lowest-scoring attempt and returns `decision="exhausted"` with `attempts=len(attempts)` (orchestrator.py:610–624).

**Conclusion:** the revise branch is reachable iff the Coach returns a `CoachVerdict` whose `.decision == "revise"`. Nothing in `run_turn` short-circuits a `revise` verdict to `fallback`.

### 2. `parse_coach_output` (lives in `src/study_tutor/tutoring/coach/rubric.py:642`, **not** `factory.py`)

The task description references `parse_coach_output` in `factory.py`; the function actually lives in `coach/rubric.py:642` and is re-exported via `from study_tutor.tutoring.coach import parse_coach_output`. The schema it produces is defined in `factory.py:237`–`304`. Behaviour:

- It accepts three input shapes: a pre-built `CoachVerdict` (pass-through), a `dict`, or a JSON `str`.
- For the `dict` and `str` branches, it calls `CoachVerdict.model_validate(...)` (rubric.py:673 / 694), which enforces:
  - `weighted_total: float ∈ [0.0, 1.0]`
  - `decision: Literal["accept", "revise"]` — these are the only two strings the schema accepts; any other value (`"fallback"`, `"flag"`, `"REVISE"` mis-cased, etc.) raises `ValidationError`, which the parser wraps into `MalformedCoachOutputError` (rubric.py:675–698).
  - `criterion_scores`, `rubric_feedback`, `misconceptions`, `reasoning`, `reasoning_long` (the last one is derived; setting it explicitly is overridden by the post-validator).
- `_drop_unknown_criteria` (rubric.py:603) silently drops criterion scores whose `criterion_id` isn't in the canonical six. **The `decision` field is not touched by this filter** — it survives unchanged from the LLM payload.

**Conclusion:** the structured shape that triggers `decision="revise"` in `parse_coach_output` is precisely a JSON object (or dict) with the literal field `"decision": "revise"`. There is no other route. If the qwen36-workhorse Coach never emits that literal substring inside a JSON object, no amount of orchestrator wiring will produce a revise outcome.

### 3. `LLMCoachAdapter.evaluate()` return type in `src/study_tutor/tutoring/adapters/llm_coach_adapter.py`

- `evaluate(...)` calls `parse_coach_output(raw)` (line 120) and returns the resulting `CoachVerdict` directly. There is no intermediate string or "raw decision tag" step.
- `MalformedCoachOutputError` is **deliberately not caught** (lines 117–120 of the adapter) — it propagates so the orchestrator's `_fallback_coach_unreachable` branch routes the turn to `fallback`. This is the intended design per AC-LCA-06 / ASSUM-007: a malformed Coach output is treated as Coach-unreachable.

**Conclusion:** the boundary between adapter parsing and orchestrator routing is clean — the adapter returns a structured `CoachVerdict`, the orchestrator branches off `verdict.decision`. There is no per-string interpretation in the orchestrator.

## Why the demo sessions never showed the revise path

Given the trace above, the production fingerprint that the loop was entered is `result.attempts > 1`. The 2026-05-06 demo showed `attempts == 1` on every turn. Two non-mutually-exclusive root causes:

1. **The Coach (`qwen36-workhorse` without RAG) did not emit `decision="revise"`** for any of the 10 turns. Without curriculum ground truth via ChromaDB, the Coach has nothing to score `quote_fidelity` / `curriculum_accuracy` against, so it falls back to "looks coherent → accept".
2. **The Coach LLM emitted text that didn't parse into `decision="revise"`** — e.g. emitted prose instead of JSON, used an unsupported decision string, or wrapped the JSON in markdown fences. In that case `parse_coach_output` raises `MalformedCoachOutputError`, which the orchestrator routes to `fallback` (the 1 `fallback` turn observed is consistent with this).

Both root causes are **out of scope** for this task per the task spec ("plumbing only, not Coach quality"). They are the right targets for follow-up work once ChromaDB retrieval lands.

## Deliverables

- **`tests/unit/tutoring/test_revise_path_reachable.py`** — a focused unit test that mocks the `CoachLike` adapter to return a `CoachVerdict(decision="revise", ...)` followed by `decision="accept"`, then asserts each of the three named criteria from the task spec:
  - (a) `Player.revise()` was awaited once with the structured `RubricFeedback` from the first verdict;
  - (b) `Coach.evaluate()` was awaited a second time on the revised response;
  - (c) `TurnResult.attempts == 2` and `TurnResult.decision in ("accept", "exhausted", "fallback")` (in this seeded sequence: `"accept"`).
- A second property test in the same file (`test_turn_decision_literal_does_not_include_revise`) pins the Literal so a future refactor that adds `"revise"` to `TurnDecision` fails loudly and forces an audit of every downstream consumer.
- This report.

## Test results

```
$ pytest tests/unit/tutoring/test_revise_path_reachable.py -v
2 passed in 0.06s

$ pytest tests/unit/tutoring/ -x -q
236 passed in 1.28s

$ pytest -m "feat_lca and smoke" tests/unit tests/integration -x -q
5 passed, 1 skipped, 844 deselected
```

Both AC-required gates green. No code change was made to `orchestrator.py`, `factory.py`, `llm_coach_adapter.py`, `rubric.py`, the Coach prompt, or the rubric weights.
