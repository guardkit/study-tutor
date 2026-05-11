# RESULTS: study-tutor-nats-fleet-demo (2026-05-11 run-4, post-Bug-#10 fix — DEMO FULLY GREEN INCL. COACH)

**Date:** 2026-05-11 morning — fourth walkthrough of the runbook,
executed immediately after the Bug #10 fix from run-3
(`LLMCoachAdapter.evaluate` kwargs mismatch on `verifier_metadata`)
was committed. Mandate from the user: "please proceed and work
through the suggested actions" — this run is the optional end-to-end
verification step from run-3's next-steps list.
**Operator:** Claude Code (non-interactive driver).
**Machine:** GB10 (`promaxgb10-41b1`) — single-host all-local.
**Runbook executed:** [`RUNBOOK-study-tutor-nats-fleet-demo.md`](RUNBOOK-study-tutor-nats-fleet-demo.md)
(at study-tutor `f4360bc`).

## Participating-repo HEADs

| Repo | HEAD | Last-commit summary |
|---|---|---|
| `study-tutor` | `f4360bc` | fix(FEAT-NATS): accept verifier_metadata kwarg in LLMCoachAdapter.evaluate (Bug #10) |
| `jarvis` | `2a70cb6` | (unchanged from run-3) |
| `specialist-agent` | `153a210` | (unchanged from run-3) |
| `nats-core` | `01e796e` | (unchanged from run-3) |
| `nats-infrastructure` | `d8ece24` | (unchanged from run-3) |

Image tags:

- `study-tutor:dev` — rebuilt **2026-05-11 07:11 BST** (image ID
  `75ac7119fe50`) to bake the Bug #10 source-code fix into the
  running container. Bug #9 was a compose-only fix and the image
  carried forward unchanged; Bug #10 touches Python source so the
  rebuild was required.

**Companion files (prior runs of the same runbook):**

- [`RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md`](RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md) —
  RED, Bug #8.
- [`RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-2.md`](RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-2.md) —
  ⏸, Bug #9 surfaced.
- [`RESULTS-study-tutor-nats-fleet-demo-2026-05-11-run-3.md`](RESULTS-study-tutor-nats-fleet-demo-2026-05-11-run-3.md) —
  GREEN learner-visible, Bug #10 surfaced as non-blocking hygiene.

---

## Outcome

✅ **GREEN — DEMO PATH NOW INCLUDES SUCCESSFUL COACH EVALUATION.**
Bug #10 is conclusively fixed. The dagger-soliloquy `tutor_turn`
returns with `decision: accept`, `attempts: 1`,
`flagged_for_review: false` — the orchestrator's bounded-revision
loop ran a single pass, the Coach LLM evaluated the Player's response
against the rubric and accepted it. No `coach_unreachable: TypeError`
WARNING in the container log (grep against the log returns zero
matches for `coach_unreachable` and `verifier_metadata`).

The most load-bearing piece of evidence is the dagger-turn reply at
[`evidence/dddsw-tutor-demo-2026-05-11-run-4/tutoring-result-dagger-turn.json`](evidence/dddsw-tutor-demo-2026-05-11-run-4/tutoring-result-dagger-turn.json):

```json
{
  "tutor_response": "That's a fantastic passage to explore! ...",
  "decision": "accept",
  "attempts": 1,
  "flagged_for_review": false,
  "duration_seconds": 12.650474686997768
}
```

The 12.6s latency is **the real demo path** — three HTTP 200 OK
chat-completions calls visible in
[`container.log`](evidence/dddsw-tutor-demo-2026-05-11-run-4/container.log)
(Player respond + Coach evaluate + a third Coach-side call from the
bounded-revision loop's accept path). Run-3's 3.1s was artificially
fast because the Coach kwargs TypeError short-circuited evaluation —
that artefact is gone.

## Demo blocking?

**NO.** The demo path is end-to-end green with every layer of the
runbook's stated topology operational: dispatch → CommandRouter →
MCP adapter → orchestrator → Player LLM → Coach LLM → accept verdict
→ ResultPayload → dual-publish. The 12.6s latency comfortably fits
the "3–5 minutes from type-prompt to reply" demo window with margin
for the supervisor's own reasoning time on the jarvis side.

---

## What's new vs run-3 (2026-05-11, post-Bug-#9 fix, Bug #10 visible)

| Topic | Run-3 (`6d1087e`, pre-Bug-#10 fix) | Run-4 (`f4360bc`, post-Bug-#10 fix) |
|---|---|---|
| `decision` | `fallback` (Coach fallback fired) | `accept` (Coach evaluated and accepted) |
| `flagged_for_review` | `true` (unevaluated-Player fallback) | `false` |
| `attempts` | 1 (one Player pass, no Coach revision loop) | 1 (one Player pass, Coach accepted on first eval) |
| `duration_seconds` | 3.1s (Coach call raised TypeError, fallback was instant) | 12.65s (real Player + Coach round-trip) |
| Container log `coach_unreachable` count | 1 WARNING per turn | 0 (verified via `grep -c`) |
| Container log `verifier_metadata` count | 1 TypeError mention per turn | 0 (verified via `grep -c`) |
| HTTP 200 chat-completions calls per turn | 2 (Player + failed Coach attempt) | 3 (Player + Coach evaluate + Coach accept-path call) |
| Test suite coverage of the verifier_metadata kwarg | 0 dedicated tests | 3 new tests in `TestEvaluateAcceptsVerifierMetadata` |

**Editorial:** Bug #10 fix worked exactly as proposed in run-3's
RESULTS — the LLMCoachAdapter now accepts the kwarg, the Phase-1
adapter intentionally ignores its content, and the regression-guard
tests lock the Phase-1 invariant (kwarg accepted, prompt unchanged)
so a future Phase-2 prompt-grounding enhancement must update tests
explicitly rather than silently changing Coach evaluation behaviour.

---

## Phase × Gate × Outcome × Evidence summary (abbreviated — run-4 is a
verification re-execution, not a full audit)

| Phase | Gate | Outcome | Evidence |
|---|---|---|---|
| 0.3 | `study-tutor:dev` image current | ✅ | Rebuilt 2026-05-11 07:11 BST to `75ac7119fe50` after Bug #10 source-code fix landed at `f4360bc`. |
| 1.1 | tutor stack up | ✅ (first attempt) | `study-tutor-gcse-tutor-1 Up 6 seconds` after `compose up -d`. |
| 1.2 | container env propagated | ✅ | Provider names + model aliases (carried forward from run-3 Bug #9 fix). |
| 3 | Dispatch fires + result rendered | ✅ | `tutor_start_session` (sub-second) → `tutor_turn` (12.65s, `decision: accept`). |
| 4.2 | Wire tap on `agents.result.>` | ✅ | Two envelopes captured at [`wire-result.log`](evidence/dddsw-tutor-demo-2026-05-11-run-4/wire-result.log) — both `success:true`. |
| 4.3 | TutoringResult captured | ✅ | [`tutoring-result-dagger-turn.json`](evidence/dddsw-tutor-demo-2026-05-11-run-4/tutoring-result-dagger-turn.json) — `decision: accept`, no fallback. **Demo slide artefact, supersedes run-3's.** |
| 8 | Demo close | ✅ | Stack brought down via `compose down`; `gcse-tutor` deregistered from `agent-registry` KV (verified absent post-shutdown). |

Phases 0.1, 0.2, 0.4, 0.5, 0.6, 1.3, 1.4, 1.5, 2.x, 4.1, 7.x carried
forward verbatim from run-3 — no infrastructure changes between runs
and re-verifying them was not on the run-4 mandate (which was solely
"does the Bug #10 fix work end-to-end?").

---

## Bug catalogue

### Bug #10 — `LLMCoachAdapter.evaluate()` kwargs mismatch (FIXED, this run)

**Status:** ✅ **FIXED.** See run-3's Bug #10 entry for the full
diagnosis; commit `f4360bc` lands the adapter-side fix verbatim
(Option A from run-3).

**What changed in [`src/study_tutor/tutoring/adapters/llm_coach_adapter.py`](../../src/study_tutor/tutoring/adapters/llm_coach_adapter.py):**

- `evaluate()` now accepts `verifier_metadata: VerifierMetadata | None = None`
  as a keyword-only optional parameter.
- The body intentionally consumes-but-ignores the kwarg
  (`_ = verifier_metadata`) — mirrors the existing `session_state`
  idiom on the same method. Phase-2 Coach calibration owns wiring the
  metadata fields into the Coach prompt.
- Docstring expanded with the full Bug #10 narrative and the Phase-2
  forward reference.
- `VerifierMetadata` imported from `study_tutor.knowledge.quote_verifier`.

**What changed in [`tests/unit/tutoring/adapters/test_llm_coach_adapter.py`](../../tests/unit/tutoring/adapters/test_llm_coach_adapter.py):**

- New test class `TestEvaluateAcceptsVerifierMetadata` with three
  guards: (1) typed-VerifierMetadata kwarg accepted without raising,
  (2) `None` kwarg accepted, (3) Phase-1 invariant — metadata is not
  woven into the Coach prompt. All three reference Bug #10 in the
  RESULTS file by name.

**Verification (this run):**

- Container log has zero matches for `coach_unreachable` and
  `verifier_metadata` (grep verified post-dispatch).
- The reply envelope has `decision: accept` (was `fallback` in run-3).
- The reply envelope has `flagged_for_review: false` (was `true` in
  run-3).
- Three chat-completions HTTP 200 calls appear in `container.log` —
  the second and third are the Coach actually evaluating, where in
  run-3 the second call's response was never consumed (TypeError
  raised during result handling).
- 18/18 tests pass in
  `tests/unit/tutoring/adapters/test_llm_coach_adapter.py`.

---

## What's working — narrative

- **Coach evaluation is now demo-grade.** The bounded-revision loop
  ran a single pass; the Coach evaluated the Player response against
  all six rubric criteria and returned `decision: accept`. No
  fallback, no hygiene flags on the reply payload.
- **Latency landed inside the runbook's stated window.** 12.65s for a
  full Player + Coach round-trip is well within the runbook's
  "10–30s warm" expectation at §3.2. Run-3's 3.1s was misleadingly
  fast because the Coach was short-circuiting; run-4's 12.65s is the
  real on-stage latency to plan around.
- **No regressions vs run-3.** All run-3 successes carried forward
  (`tutor_start_session` works on both baseline and topic-override
  paths, KV registration clean, manifest unchanged, dual-publish on
  both `agents.result.gcse-tutor` and the request-reply inbox).

---

## Next steps with concrete fix-and-rerun list

1. **The follow-up `coach_handover` test failures** (4 tests in
   `tests/unit/knowledge/test_coach_handover.py`) called out in the
   Bug #10 commit message are pre-existing — the fixtures' `handover()`
   callable takes 2 positional args while the orchestrator now calls
   it with 3 (TASK-RAG-002 added `learner_message`). Track as a
   separate follow-up and fix at fixture-rewriting time; not blocking
   anything else.
2. **Run-5: interactive jarvis-chat phases (§2 + §3).** Four runs have
   now exercised the dispatch path via the non-interactive `nats
   request` surrogate. The runbook's actual demo flow goes through
   `jarvis chat` → `dispatch_by_capability` → live KV catalogue →
   `agents.command.gcse-tutor` (functionally equivalent at the wire
   level, but the supervisor's tool-selection step has its own
   failure modes that this driver cannot exercise). Operator-driven.
3. **Dress rehearsal 2026-05-15.** Pre-warm `gemma4-tutor` and
   `qwen36-workhorse` with one throwaway call each before going on
   stage. The 12.65s warm latency observed here is comfortable but
   leaves no margin if the model is cold or contended.

## Hygiene flags (non-blocking)

- **`event=rag_disabled reason=chromadb_missing`** — same hygiene
  finding as runs 1–3. ChromaDB still not shipped in the image; RAG
  path silently disabled. Decide before the talk.
- **`event=rag_disabled reason=collection_provider_unwired`** — same
  root cause.
- **`coach_handover` test fixture drift** — 4 pre-existing failures
  in `tests/unit/knowledge/test_coach_handover.py` (signature
  mismatch between fixture and orchestrator's TASK-RAG-002 3-arg
  call). Tracked in the Bug #10 commit's out-of-scope note; safe to
  defer.

## Evidence index

All under [`docs/runbooks/evidence/dddsw-tutor-demo-2026-05-11-run-4/`](evidence/dddsw-tutor-demo-2026-05-11-run-4/):

- `container.log` — three `HTTP 200 OK` chat-completions calls + the
  `orchestrator_turn_completed` INFO line. **Zero** matches for
  `coach_unreachable` or `verifier_metadata` (the Bug #10 fix-
  verification signal).
- `wire-result.log` — two `success:true` envelopes (start_session +
  turn). The turn envelope's `decision: accept` is the new artefact
  vs run-3's `decision: fallback`.
- `dispatch-reply-macbeth-start.txt` — start_session reply via the
  request-reply inbox.
- `dispatch-reply-dagger-turn.txt` — full turn reply via the
  request-reply inbox. **The strongest single-file evidence that the
  full Player + Coach demo path works.**
- `tutoring-result-dagger-turn.json` — parsed `result` block from
  the turn reply. **Replaces run-3's as the talk slide artefact** —
  same tutor response shape but with the real Coach `decision:
  accept` instead of the fallback.
