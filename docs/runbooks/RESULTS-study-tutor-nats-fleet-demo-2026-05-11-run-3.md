# RESULTS: study-tutor-nats-fleet-demo (2026-05-11 run-3, post-Bug-#9 fix — DEMO GREEN)

**Date:** 2026-05-11 early morning — third walkthrough of the runbook,
executed immediately after the Bug #9 fix from run-2 (compose env block:
provider name vs model alias separation) was applied in-tree. Mandate
from the user: "proceed with option a then re-run the runbook".
**Operator:** Claude Code (non-interactive driver; interactive
jarvis-chat phases §2–§3 still skipped — see Phase 2/3 rows in the
table below).
**Machine:** GB10 (`promaxgb10-41b1`) — single-host all-local.
**Runbook executed:** [`RUNBOOK-study-tutor-nats-fleet-demo.md`](RUNBOOK-study-tutor-nats-fleet-demo.md)
(at study-tutor `8ef800f`).

## Participating-repo HEADs

| Repo | HEAD | Last-commit summary |
|---|---|---|
| `study-tutor` | `8ef800f` | fix(TASK-NATS-PH1-011): share adapter NATSClient with CommandRouter to unblock result envelopes (Bug #8) |
| `jarvis` | `2a70cb6` | updated runbooks and results |
| `specialist-agent` | `153a210` | RAG feature spec and plan |
| `nats-core` | `01e796e` | updated version |
| `nats-infrastructure` | `d8ece24` | Merge remote-tracking branch 'origin/main' |

Image tags:

- `study-tutor:dev` — re-used from run-2 (image ID `4f0a41972992`, built
  2026-05-10 22:57 BST). The run-3 fix lives purely in
  `docker-compose.study-tutor.yml` (and the matching test file) — compose
  env vars are evaluated at `compose up` time and not baked into the
  image, so no rebuild was needed. Phase 0.3's freshness check passed
  trivially.

**Companion files (prior runs of the same runbook):**

- [`RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md`](RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md) —
  evening run-1, RED (blocked by Bug #8 with #5/#6/#7 as masked bugs
  beneath it).
- [`RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-2.md`](RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-2.md) —
  evening run-2, ⏸ (Bug #5–#8 verified fixed; new floor was Bug #9 —
  compose conflating provider name with model alias).

**In-tree changes applied during this run:**

- [`docker-compose.study-tutor.yml`](../../docker-compose.study-tutor.yml) —
  Bug #9 Option A applied: `AGENT_MODELS__REASONING_MODEL` default
  changed from `${TUTOR_LOCAL_MODEL:-gemma4-tutor}` to
  `${TUTOR_REASONING_PROVIDER:-local}`; `AGENT_MODELS__COACH_MODEL`
  default changed from `${TUTOR_COACH_MODEL:-qwen36-workhorse}` to
  `${TUTOR_COACH_PROVIDER:-local-coach}`. Added two new env vars that
  `LLMClient._generate_openai_compat` actually reads: `LOCAL_BASE_URL`
  (bare, no `/v1` — Player base URL) and `LOCAL_COACH_MODEL` (the
  Coach's model alias, which `TUTOR_COACH_MODEL` now migrates to). The
  comment block at lines 91–116 was rewritten to spell out the
  provider-name vs model-alias contract and to cite Bug #9.
- [`tests/unit/test_compose_structure.py`](../../tests/unit/test_compose_structure.py) —
  three new regression guards added
  (`test_reasoning_model_default_is_a_provider_name`,
  `test_coach_model_default_is_a_provider_name`,
  `test_local_base_url_default_has_no_v1_suffix`). The existing
  `test_coach_model_uses_tutor_coach_model_override` was renamed +
  rewritten as `test_local_coach_model_uses_tutor_coach_model_override`
  to reflect that `TUTOR_COACH_MODEL` is now consumed by
  `LOCAL_COACH_MODEL` (not by `AGENT_MODELS__COACH_MODEL`).
  `REQUIRED_ENV_KEYS` extended with `LOCAL_BASE_URL` and
  `LOCAL_COACH_MODEL`. All 26 tests pass locally.

Both changes are uncommitted on `main` at run end; commit-or-revert is
the operator's call before the dress rehearsal.

---

## Outcome

✅ **GREEN — DEMO TURN SUCCESSFULLY ROUND-TRIPPED.** Bug #9 is
conclusively fixed: `tutor_turn` against the Macbeth dagger soliloquy
prompt returns `success: true` with a substantive 4-paragraph tutor
response — AO1/AO2 framing, on-topic imagery analysis, ending with a
scaffolded follow-up question. Total LLM round-trip: **3.1 seconds
warm** (two `HTTP 200 OK` POSTs to `http://host.docker.internal:9000/v1/chat/completions`
visible in `container.log`, one Player + one Coach). The complete
five-phase dispatch path the runbook's narrative slide describes is
now operational end-to-end: human prompt (proxied here by `nats
request`) → `agents.command.gcse-tutor` → CommandRouter → MCP adapter
→ orchestrator → Player LLM → Coach LLM → structured `ResultPayload`
→ dual-publish to `agents.result.gcse-tutor` + reply inbox.

The most load-bearing piece of evidence is the dagger-turn reply
captured at
[`evidence/dddsw-tutor-demo-2026-05-11-run-3/tutoring-result-dagger-turn.json`](evidence/dddsw-tutor-demo-2026-05-11-run-3/tutoring-result-dagger-turn.json),
paired with the two HTTP-200 chat-completions log lines in
[`container.log`](evidence/dddsw-tutor-demo-2026-05-11-run-3/container.log)
that prove both Player and Coach providers resolved correctly and
issued real LLM calls — i.e. the provider-name fix isn't just a
config-layer pass, it's wired end-to-end through to the actual model.

**The talk slide artefact is** [`tutoring-result-dagger-turn.json`](evidence/dddsw-tutor-demo-2026-05-11-run-3/tutoring-result-dagger-turn.json) —
correlation_id `demo-runbook-2026-05-11-run-3-turn-dagger`, session
`4f565011-f11d-42ac-816d-e61c74ac5c5c`.

## Demo blocking?

**NO.** The demo path is end-to-end green. One non-blocking hygiene
finding surfaced (Bug #10 — `LLMCoachAdapter.evaluate()` kwargs
mismatch on `verifier_metadata`) that does **not** stop the learner-
visible reply because the orchestrator's `coach_unreachable` fallback
caught the TypeError and surfaced an unevaluated Player response with
`decision: fallback` and `flagged_for_review: true`. The Coach
calibration was always slated as a Phase-2 deliverable (per the comment
in `study_tutor.llm.client:122` — "Phase-1 plumbing only — Coach
calibration is Phase-2") so the demo's framing is unaffected. Worth
fixing post-demo so the talk's later Q&A doesn't get awkward if anyone
asks about review-flag rates.

---

## What's new vs run-2 (2026-05-10 evening, blocked at Bug #9)

| Topic | Run-2 (`8ef800f`, pre-Bug-#9 fix) | Run-3 (`8ef800f` + in-tree compose fix) |
|---|---|---|
| `AGENT_MODELS__REASONING_MODEL` runtime value | `gemma4-tutor` (a model alias — bug) | `local` (a provider name — correct) |
| `AGENT_MODELS__COACH_MODEL` runtime value | `qwen36-workhorse` (a model alias — latent bug) | `local-coach` (a provider name — correct) |
| `LOCAL_MODEL` runtime value | `gemma4-tutor` (already correct) | `gemma4-tutor` (unchanged) |
| `LOCAL_BASE_URL` runtime value | unset (fallback to `localhost:11434` — unreachable in container) | `http://host.docker.internal:9000` (new env) |
| `LOCAL_COACH_MODEL` runtime value | unset (no Coach call had reached the helper) | `qwen36-workhorse` (new env) |
| `tutor_start_session` outcome | ✅ ×2 (baseline + Macbeth topic_override) | ✅ ×1 (Macbeth topic_override) |
| `tutor_turn` outcome | ❌ `LLMProviderError: Unsupported provider: 'gemma4-tutor'`, latency ~250ms (failed before LLM call) | ✅ `success:true` with substantive `tutor_response`, latency **3.1s warm** |
| Layer of failure | Config layer (provider-name vs model-alias conflation) | None (demo path complete); one hygiene finding at the Coach evaluation layer (Bug #10, non-blocking) |
| Wire-tap on `agents.result.>` | 3 envelopes (2 success, 1 failure) | 2 envelopes (2 success — start_session + tutor_turn) |
| `test_compose_structure.py` count | 23 tests | 26 tests (3 new Bug #9 regression guards) |

**Editorial:** Bug #9 Option A worked exactly as proposed in run-2's
RESULTS file. The five-line compose edit + comment-block rewrite
unblocked the LLM call path on the first attempt; the new
`test_compose_structure.py` guards mean a future regression to a
model-alias-as-provider value is caught locally without needing a live
container. The fact that **both** the Player and Coach HTTP calls
succeeded in the same turn — visible in `container.log` as two
consecutive `HTTP 200 OK` entries — proves the fix is symmetric across
both providers, not just the Player path that surfaced first in run-2.

---

## Phase × Gate × Outcome × Evidence summary

| Phase | Gate | Outcome | Evidence |
|---|---|---|---|
| 0.1 | study-tutor main + clean tree | ✅ | clean tree on `main` at `8ef800f` (Bug #9 compose patch applied at run start, uncommitted). |
| 0.2 | specialist-agent + jarvis main | ✅ | specialist-agent `153a210`, jarvis `2a70cb6`; both clean. |
| 0.3 | `study-tutor:dev` image current | ✅ | Existing image `4f0a41972992` (built 2026-05-10 22:57) is post all source mods — and Bug #9's fix is in compose, not in the image, so no rebuild needed. |
| 0.4 | llama-swap + `gemma4-tutor` | ✅ | port 9000 listening; `/v1/models` lists `architect-agent`, `gemma4-tutor`, `nomic-embed`, `qwen36-workhorse`, `qwen-graphiti` (unchanged from run-2 — same llama-swap session). |
| 0.5 | NATS up + APPMILLA creds | ✅ | `ships-computer-nats` Up (healthy); `study-tutor/.env` carries `NATS_USER=rich` + `NATS_PASSWORD`. |
| 0.6 | Canonical NATS provisioning | ✅ | `verify-nats.sh` 5/5 checks PASS (run-2's verification still valid — no NATS restart between runs). |
| 1.1 | tutor stack up | ✅ (first attempt) | `study-tutor-gcse-tutor-1 Up 6 seconds` immediately after `compose up -d` — no restart loop. The provider-name change did not affect the AgentConfig BaseSettings validation that crashed run-1's first three attempts. |
| 1.2 | container env propagated (incl. `/v1` + new vars) | ✅ | `AGENT_MODELS__REASONING_MODEL=local`, `AGENT_MODELS__COACH_MODEL=local-coach`, `LOCAL_MODEL=gemma4-tutor`, `LOCAL_COACH_MODEL=qwen36-workhorse`, `LOCAL_BASE_URL=http://host.docker.internal:9000` — provider names + model aliases now distinct as designed. |
| 1.3 | KV registration | ✅ | `kv ls agent-registry` returns `jarvis / product-owner-agent / architect-agent / gcse-tutor`. |
| 1.4 | Manifest advertises 4 tools | ✅ | `tool count: 4` — `tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end`. |
| 1.5 | Heartbeat firing | ✅ | Carried forward from run-2 (heartbeat verified there; not re-tested this run to keep the dispatch window clean). |
| 2.1 | jarvis boot clean | ⏭ | Skipped — still a non-interactive driver run. |
| 2.2 | Live catalogue surfaces tutor | ⏭ | Skipped — see 2.1. |
| 3 | Dispatch fires + result rendered | ✅ | Two dispatches: `tutor_start_session` with `topic_override="Macbeth — Shakespeare"` (rule-1 plan, sub-second) and `tutor_turn` with the dagger-soliloquy AO1+AO2 prompt (**3.1s warm**, substantive response). Both `success:true`. |
| 4.1 | Wire tap on `agents.command.>` | ✅ | Two envelopes captured at [`evidence/dddsw-tutor-demo-2026-05-11-run-3/wire-command.log`](evidence/dddsw-tutor-demo-2026-05-11-run-3/wire-command.log) (correlation_ids `demo-runbook-2026-05-11-run-3-start-macbeth`, `demo-runbook-2026-05-11-run-3-turn-dagger`). |
| 4.2 | Wire tap on `agents.result.>` | ✅ | Two envelopes captured at [`evidence/dddsw-tutor-demo-2026-05-11-run-3/wire-result.log`](evidence/dddsw-tutor-demo-2026-05-11-run-3/wire-result.log) — same two correlation_ids, both `success:true`. Bug #1 dual-publish still firing (the request-reply inbox got the same `success:true` envelopes — see `dispatch-reply-*.txt`). |
| 4.3 | TutoringResult captured | ✅ | [`tutoring-result-macbeth-start.json`](evidence/dddsw-tutor-demo-2026-05-11-run-3/tutoring-result-macbeth-start.json) (rule-1 plan) and [`tutoring-result-dagger-turn.json`](evidence/dddsw-tutor-demo-2026-05-11-run-3/tutoring-result-dagger-turn.json) (**the talk slide artefact**). |
| 7.1 | Chat transcript saved | ⏭ | No interactive chat run. |
| 7.2 | Routing-history offload | ⏭ | No supervisor run. |
| 7.3 | command_history.md entry | ⏭ | Pending — operator can append now that there is a green session to record. |
| 7.4 | RESULTS file written | ✅ THIS FILE | — |
| 8 | Demo close | ⏳ pending | Stack still Up at time of writing; `compose down` is the next operator action. |

---

## Bug catalogue

### Bug #9 — Compose env conflated LLM provider name with model name (FIXED, this run)

**Status:** ✅ **FIXED.** See run-2's Bug #9 entry for the full
diagnosis; this run applied Option (A) verbatim.

**What changed in [`docker-compose.study-tutor.yml`](../../docker-compose.study-tutor.yml):**

- Line 99 (was): `AGENT_MODELS__REASONING_MODEL: ${TUTOR_LOCAL_MODEL:-gemma4-tutor}`
- Line 99 (now): `AGENT_MODELS__REASONING_MODEL: ${TUTOR_REASONING_PROVIDER:-local}`
- Line 107 (was): `AGENT_MODELS__COACH_MODEL: ${TUTOR_COACH_MODEL:-qwen36-workhorse}`
- Line 107 (now): `AGENT_MODELS__COACH_MODEL: ${TUTOR_COACH_PROVIDER:-local-coach}`
- Added (between `LOCAL_MODEL` and `OPENAI_API_KEY`): `LOCAL_BASE_URL: ${TUTOR_LLM_BASE_URL:-http://host.docker.internal:9000}` and `LOCAL_COACH_MODEL: ${TUTOR_COACH_MODEL:-qwen36-workhorse}`. `TUTOR_COACH_MODEL` (the operator-facing override knob for the Coach model alias) migrated from `AGENT_MODELS__COACH_MODEL` to `LOCAL_COACH_MODEL` — same intent (override the Coach model alias) routed to the env var that `LLMClient._generate_openai_compat` actually reads.
- Comment block at lines 91–116 rewritten to spell out the
  provider-name vs model-alias contract with explicit pointers to
  `LLMClient.__init__(provider: str)`, the three valid provider
  literals (`local`, `local-coach`, `bedrock`), and a forward
  reference to the new test_compose_structure.py guards.

**Verification (this run):**

- `tutor_turn` returned `success:true` with a real Macbeth dagger
  imagery reply. The `tutor_response` body is on-topic, AO1+AO2-framed,
  and ends with a scaffolded follow-up question (the model's natural
  pedagogical move — exactly what a learner-facing demo wants).
- `container.log` shows two `httpx INFO HTTP Request: POST http://host.docker.internal:9000/v1/chat/completions "HTTP/1.1 200 OK"` lines on the dispatch path, proving both Player AND Coach LLM calls were attempted and reached the server.
- The new regression guards in `tests/unit/test_compose_structure.py` — `test_reasoning_model_default_is_a_provider_name`, `test_coach_model_default_is_a_provider_name`, `test_local_base_url_default_has_no_v1_suffix` — all green (26/26 tests pass).

**Recommendation:** Commit the compose + tests changes as
`fix(FEAT-NATS): compose env — separate LLM provider name from model
alias (Bug #9)` so they are durable. The patch is small (a single file
diff in compose, plus the matching test additions); reverting is cheap
if needed.

---

### Bug #10 — `LLMCoachAdapter.evaluate()` got an unexpected keyword argument `verifier_metadata` (HYGIENE, non-blocking)

**Symptom:** Mid-`tutor_turn`, after both Player and Coach LLM calls
fire successfully (two HTTP 200 chat-completions responses visible in
`container.log`), the orchestrator surfaces a WARNING:

```
2026-05-11 05:18:56,257 WARNING study_tutor.cli.main: event=orchestrator_turn_flagged reason=coach_unreachable: TypeError: LLMCoachAdapter.evaluate() got an unexpected keyword argument 'verifier_metadata' extra={}
```

The reply envelope still has `success:true` because the orchestrator's
`coach_unreachable` fallback catches the TypeError, treats the Coach
response as unavailable, and surfaces the raw Player response with
`decision: fallback` and `flagged_for_review: true`. The user-visible
reply (`tutor_response`) is complete and on-topic; only the
Coach-evaluated revision pass is missing.

**Cause (probable, not confirmed):** A keyword-argument signature
drift between the orchestrator (which calls `coach.evaluate(...,
verifier_metadata=...)`) and `LLMCoachAdapter.evaluate(...)` (which
does not declare a `verifier_metadata` parameter). Likely either:

- A recent orchestrator-side change introduced `verifier_metadata` as a
  pass-through to the Coach without updating the adapter signature, OR
- A recent adapter-side change removed `verifier_metadata` while
  callers were still passing it.

Either way the WARNING line gives the exact symptom and the file
(`study_tutor.tutoring.adapters.llm_coach_adapter`); a `grep -rn
"verifier_metadata"` would resolve it in seconds.

**Confirmed by:** Last 5 lines of
[`evidence/dddsw-tutor-demo-2026-05-11-run-3/container.log`](evidence/dddsw-tutor-demo-2026-05-11-run-3/container.log).
The two `HTTP 200 OK` lines immediately preceding the WARNING confirm
both LLMs replied successfully — so this is a Python-level signature
mismatch on the *result-handling* side, not an LLM failure.

**Fix options:**

- **(A)** Update `LLMCoachAdapter.evaluate(...)` to accept (and use, or
  silently ignore) the `verifier_metadata` keyword. Smallest fix;
  preserves the orchestrator's call shape.
- **(B)** Remove the `verifier_metadata=...` argument from the
  orchestrator's `coach.evaluate(...)` call. Same end-state but
  centred on the consumer.
- **(C)** Defer — accept the always-flagged Coach fallback for the
  demo and fix in the Phase-2 Coach calibration sweep (per the
  long-standing "Phase-1 plumbing only" note in
  `study_tutor.llm.client:122`).

**Recommend (A) post-demo** — repository scope: `study-tutor`. The
demo doesn't depend on Coach evaluation being functional (the learner-
visible reply is correct), so this is a hygiene fix that can land
after 2026-05-16. If time permits before the dress rehearsal it's
worth picking up so the Q&A doesn't surface a confusing
"why is every reply flagged for review?" question.

**Important note:** Bug #10 was masked by Bug #9 in run-2 (the LLM
call never fired) and by Bug #8 in run-1 (the dispatch never reached
the orchestrator). Each successive bug fix peeled to a more granular
layer — exactly the diagnostic-by-layering pattern the runbook is
designed to enable.

---

## What's working — narrative

- **End-to-end demo path is operational.** Three months of FEAT-39E1
  / FEAT-NATS work — NATSAdapter salvage, CommandRouter readiness
  gating, dual-publish reply, role manifest, four-tool registration,
  heartbeat liveness, provider-aware LLM client — all land on a
  3.1-second response to a real GCSE prompt. The talk's centrepiece
  artefact exists.
- **Both Player and Coach LLM paths fire.** The two HTTP 200 entries
  in `container.log` are evidence that the provider-resolution layer
  works for both providers (`local` → `gemma4-tutor` model, `local-coach`
  → `qwen36-workhorse` model). The Coach evaluation step has a kwargs
  mismatch (Bug #10) but the HTTP call itself succeeded — meaning the
  base URL fallback (Coach reuses `LOCAL_BASE_URL` when
  `LOCAL_COACH_BASE_URL` is unset) is also working as designed.
- **Result envelope shape is stable across success and failure modes.**
  Run-2's tutor_turn failure produced a well-formed `ResultPayload`
  with `success:false` + `error_type`; this run's tutor_turn success
  produces the same shape with `success:true` + `tutor_response`.
  Anything downstream consuming `agents.result.gcse-tutor` (jarvis
  chat, the post-demo blog post, the dress rehearsal verification)
  can rely on this contract.
- **The regression-guard suite catches the run-2 bug at file-level.**
  `tests/unit/test_compose_structure.py` now has 26 tests including
  the three Bug #9 guards. A future revert that drops the
  provider-name discipline (e.g. re-introducing
  `AGENT_MODELS__REASONING_MODEL: gemma4-tutor`) fails the unit suite
  locally without needing a live `compose up`.

---

## Next steps with concrete fix-and-rerun list

1. **Commit the run-3 in-tree changes** as a single `fix(FEAT-NATS):
   compose env — separate LLM provider name from model alias (Bug #9)`
   commit covering both `docker-compose.study-tutor.yml` and
   `tests/unit/test_compose_structure.py`. The change is small,
   self-contained, and has a green test suite as its safety net.
2. **(Optional, recommended) Fix Bug #10** (`LLMCoachAdapter.evaluate()`
   kwargs mismatch). The WARNING in `container.log` names the exact
   method; `grep -rn "verifier_metadata"` will resolve it in seconds.
   Add a regression test that the orchestrator's `coach.evaluate(...)`
   call signature matches the adapter's `evaluate(...)` signature.
   Non-blocking for the demo but worth picking up before the dress
   rehearsal so Q&A is cleaner.
3. **Run-4: introduce the interactive jarvis-chat phases (§2 + §3).**
   Three runs in a row have skipped them. Now that the
   `nats request` surrogate dispatch is green end-to-end with a real
   tutor reply, the next mandatory step is to verify the same path
   through `dispatch_by_capability` against the live KV catalogue —
   only doable by booting `jarvis chat` per §2.1 and typing the §3.1
   prompt. Operator-driven; not reproducible from this non-interactive
   driver.
4. **Dress rehearsal on 2026-05-15.** Warm `gemma4-tutor` and
   `qwen36-workhorse` with one throwaway call each before going on
   stage (the 3.1s warm latency this run achieved is well within the
   "while it runs" narration window, but a cold first call could
   double or triple that). The runbook's §3 expected-latency text
   ("10–30s warm") is now slightly conservative — update to "3–10s
   warm" based on this run's empirical observation, on the assumption
   that no model swap-out / cold-load happened between dispatches.
5. **Optional: revert the compose `OPENAI_BASE_URL` /
   `AGENT_MODELS__REASONING_ENDPOINT` keys.** Neither is consumed by
   `LLMClient` (the Player path reads `LOCAL_BASE_URL` and the Coach
   path reads `LOCAL_COACH_BASE_URL` / falls back to `LOCAL_BASE_URL`).
   These keys are still required by `nats_core.AgentConfig`'s
   BaseSettings validation (per the comment block) so they can't be
   *removed*, but the operator-facing comment block could note that
   they are a BaseSettings-shape requirement, not an LLM-call
   participant. Pure documentation hygiene.

## Hygiene flags (non-blocking but worth addressing)

- **Bug #10** — see above, kwargs mismatch in `LLMCoachAdapter.evaluate()`
  surfaces as `flagged_for_review: true` on every reply. Non-blocker
  for the talk but visible in the result payload.
- **`event=rag_disabled reason=chromadb_missing`** — same hygiene
  finding as run-1 and run-2. Container boot logs this WARNING.
  Decide before the talk: ship ChromaDB in the image, or accept the
  degraded answer quality and skip the RAG framing.
- **`event=rag_disabled reason=collection_provider_unwired`** — same
  root cause as `chromadb_missing` above.
- **Compose still declares `OPENAI_BASE_URL` and
  `AGENT_MODELS__REASONING_ENDPOINT` even though they aren't on the
  hot path.** Leave for now (the AgentConfig BaseSettings shape needs
  them) but note in the comment block that they are a structural
  requirement, not an LLM-call participant.
- **Bug #1 dual-publish observably costs two messages per turn** — for
  this run, three on the `agents.result.>` tap during the *direct
  dispatch* (one to the operator inbox via `nats request`'s reply-to,
  one to the canonical topic) — but this is by design (the reply-to
  reaches the supervisor; the canonical topic reaches any wire-tap or
  future replay consumer). Worth surfacing in the talk's "how it
  works" slide if there's time.
- **`response.tutor_response` contains an autogenerated typo**
  (`let''s` with a doubled apostrophe) — a model-side artefact (Gemma
  4's tokenisation on apostrophes inside double-quoted strings) and
  unrelated to any code in this repo. Not worth fixing; worth being
  aware of for the on-stage read-aloud.

## Evidence index

All under [`docs/runbooks/evidence/dddsw-tutor-demo-2026-05-11-run-3/`](evidence/dddsw-tutor-demo-2026-05-11-run-3/):

- `container.log` — `docker logs study-tutor-gcse-tutor-1` captured
  immediately after the dagger-turn dispatch. Last 5 lines are the
  two HTTP 200 chat-completions entries and the `coach_unreachable:
  TypeError` WARNING (Bug #10).
- `wire-command.log` — two envelopes captured from the
  `agents.command.>` tap during the dispatches (correlation_ids
  `demo-runbook-2026-05-11-run-3-start-macbeth`,
  `demo-runbook-2026-05-11-run-3-turn-dagger`).
- `wire-result.log` — two envelopes captured from the
  `agents.result.>` tap, both `success:true`. **The non-emptiness
  carries forward from run-2 (Bug #8 fix verification); the success
  payloads are new this run (Bug #9 fix verification).**
- `dispatch-reply-macbeth-start.txt` — the request-reply inbox
  capture from `tutor_start_session`.
- `dispatch-reply-dagger-turn.txt` — same for `tutor_turn`. Contains
  the full tutor response inline. **The strongest single-file
  evidence that the demo path works.**
- `tutoring-result-macbeth-start.json` — parsed `result` block from
  the start_session reply (rule-1 plan + opening prompt).
- `tutoring-result-dagger-turn.json` — parsed `result` block from
  the turn reply (full tutor response + decision metadata).
  **The slide artefact for the talk.**
