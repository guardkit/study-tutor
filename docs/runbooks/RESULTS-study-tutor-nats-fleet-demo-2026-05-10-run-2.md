# RESULTS: study-tutor-nats-fleet-demo (2026-05-10 run-2, post-Bug-#5..#8 fix)

**Date:** 2026-05-10 evening — second walkthrough of the runbook, executed
immediately after the Bug #5–#8 fixes from run-1 were committed (commits
`e92827c`, `23e4f5c`, `d8d43d8`, `2b15adb`, `8ef800f`). Mandate from the
user: "execute the runbook following bug fixes from the previous run".
**Operator:** Claude Code (non-interactive driver; interactive jarvis-chat
phases §2–§3 skipped — see Phase 2/3 rows in the table below).
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

- `study-tutor:dev` — built **2026-05-10 22:57 BST** during this run
  (image ID `4f0a41972992`). The pre-existing image (20:28 from run-1)
  was stale relative to `src/study_tutor/adapters/nats_adapter.py` (22:50),
  `docker-compose.study-tutor.yml` (22:50), and `Dockerfile` (21:54);
  Phase 0.3's freshness check caught this and triggered a clean rebuild
  via `TAG=dev ./scripts/docker-build.sh`.

**Companion files (prior runs of the same runbook):**

- [`RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md`](RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md) —
  evening run-1 (RED — blocked by Bug #8 with three masked configuration
  bugs #5–#7 patched in-tree but uncommitted at that run's halt).

**In-tree changes applied during this run:** none. The five bug fixes
from run-1 were committed by the operator between runs; this run started
from a clean working tree and ended with a clean working tree (plus the
new `evidence/dddsw-tutor-demo-2026-05-10-run-2/` directory and this file
as untracked artefacts).

---

## Outcome

⏸ **STILL BLOCKED, but one layer deeper.** Bug #8 is conclusively fixed —
`tutor_start_session` round-trips through `agents.command.gcse-tutor` →
`CommandRouter` → `agents.result.gcse-tutor` cleanly **twice in a row**
with `success: true`, the canonical Bug #1 dual-publish path (reply inbox
+ canonical result topic) also confirmed working. Phase 1 fully green
without retries. The new floor is **Bug #9** (this run's discovery):
`tutor_turn` raises `LLMProviderError: Unsupported provider: 'gemma4-tutor'`
because the compose env block sets `AGENT_MODELS__REASONING_MODEL` to a
**model name** (`gemma4-tutor`), but `LLMClient.__init__(provider: str)`
expects a **provider name** (`local`/`local-coach`/`bedrock`). The
provider-name vs model-name conflation was previously masked by Bug #8 —
the dispatch path never reached the orchestrator's `_player.respond()`
call in run-1.

The most load-bearing piece of evidence is the container traceback at
[`evidence/dddsw-tutor-demo-2026-05-10-run-2/container.log`](evidence/dddsw-tutor-demo-2026-05-10-run-2/container.log)
showing the full unwind from `command_router.py:216` → `mcp/adapter.py:357`
→ `orchestrator.py:475` → `llm_player_adapter.py:162` → `client.py:141`,
paired with the `success: true` envelopes captured at
[`evidence/dddsw-tutor-demo-2026-05-10-run-2/wire-result.log`](evidence/dddsw-tutor-demo-2026-05-10-run-2/wire-result.log)
showing the two preceding start-session round-trips landed cleanly.

## Demo blocking?

**YES.** The demo turn (§3.1 — dagger soliloquy `tutor_turn`) cannot
complete until Bug #9 is fixed. `tutor_start_session` works (so the topology
slide is half-demonstrable: the supervisor *could* establish a session
on stage), but no learner-facing reply ever materialises.

The next walkthrough's prerequisite is a corrected env block in
`docker-compose.study-tutor.yml` so `AGENT_MODELS__REASONING_MODEL=local`
(the provider name) and the existing `LOCAL_MODEL=gemma4-tutor` continues
to drive model selection inside `LLMClient._generate_openai_compat`.
Same fix shape applies to the Coach side: `AGENT_MODELS__COACH_MODEL`
should be `local-coach`, with the actual model name moved to
`LOCAL_COACH_MODEL` (and `LOCAL_COACH_BASE_URL` if it differs from
`LOCAL_BASE_URL`). See Bug #9 below for the full disposition.

---

## What's new vs run-1 (2026-05-10 evening, blocked at Bug #8)

| Topic | Run-1 (`82f2aba`, pre-fix) | Run-2 (`8ef800f`, post-fix) |
|---|---|---|
| `study-tutor:dev` image | Built 13:45, stale vs 20:02 `src/`; rebuilt mid-run to 20:28 | Built 22:57, fresh against all source mods including the Bug #8 fix at 22:50 |
| `Dockerfile` carrying `roles/`/`data/`/`.guardkit/graphiti.yaml` | In-tree, uncommitted | Committed (`e92827c`, `23e4f5c`) |
| Compose `AGENT_MODELS__COACH_MODEL` block | In-tree, uncommitted (`qwen36-workhorse`) | Committed (`d8d43d8`); value carried forward verbatim (NB: same provider-name-vs-model-name confusion as Player — see Bug #9) |
| Compose `NATS_USER` default | In-tree, uncommitted (`appmilla` → `rich`) | Committed (`2b15adb`); container env shows `NATS_USER=rich` |
| `CommandRouter._client` connectedness | `RuntimeError: client is not connected` on `_publish_result` | ✅ Connected — `agents.result.gcse-tutor` envelope landed twice |
| Wire-tap on `agents.command.>` during a dispatch | 1 envelope (start_session) | 3 envelopes (2 starts + 1 turn) |
| Wire-tap on `agents.result.>` during a dispatch | 0 envelopes (empty file — the failure signal) | 3 envelopes (2 `success:true`, 1 `success:false` w/ Bug #9 error_type) |
| `tutor_start_session` outcome | Never reached `_publish_result` cleanly — agent raised mid-result | ✅ ×2 (baseline + Macbeth topic_override) |
| `tutor_turn` outcome | Not attempted (Bug #8 would have killed it the same way) | ❌ Bug #9 — `LLMProviderError: Unsupported provider: 'gemma4-tutor'` |
| Layer of failure | Adapter wiring (CommandRouter client unconnected) | LLM provider resolution (config-layer model/provider conflation) |

**Editorial:** The run-1 fix-set did exactly what it claimed. Bug #8 is
gone, Bug #1 (dual-publish) is observably correct, Bug #2 (tool-to-command
mapping) is implicitly fine (the agent dispatched `tutor_start_session`
and `tutor_turn` from the supervisor-facing tool names through to the
internal handlers). The hot path now reaches the orchestrator and only
breaks on a configuration-layer artefact in the compose file's env block.
Bug #9 is a *smaller* fix than any of #5–#8 (two-line compose edit) but
it's the one the runbook exists to surface for this demo's centerpiece —
the dagger-soliloquy answer.

---

## Phase × Gate × Outcome × Evidence summary

| Phase | Gate | Outcome | Evidence |
|---|---|---|---|
| 0.1 | study-tutor main + clean tree | ✅ | clean tree on `main` at `8ef800f`; top-of-log shows the five run-1 fix commits in order |
| 0.2 | specialist-agent + jarvis main | ✅ | specialist-agent `153a210`, jarvis `2a70cb6`; both clean |
| 0.3 | `study-tutor:dev` image current | ⚠️ → ✅ | Pre-existing image (20:28) was stale vs `nats_adapter.py` (22:50). Rebuilt via `TAG=dev ./scripts/docker-build.sh` to `4f0a41972992` at 22:57. |
| 0.4 | llama-swap + `gemma4-tutor` | ✅ | port 9000 listening; `/v1/models` lists `architect-agent`, `gemma4-tutor`, `nomic-embed`, `qwen36-workhorse`, `qwen-graphiti` |
| 0.5 | NATS up + APPMILLA creds | ✅ | `ships-computer-nats` Up (healthy, 8h); `study-tutor/.env` carries `NATS_USER=rich` + `NATS_PASSWORD` (set) |
| 0.6 | Canonical NATS provisioning | ✅ | `verify-nats.sh` 5/5 checks PASS; 7/7 streams present (PIPELINE/AGENTS/JARVIS/NOTIFICATIONS/SYSTEM/FLEET/FINPROXY) |
| 1.1 | tutor stack up | ✅ (first attempt) | `study-tutor-gcse-tutor-1 Up 8 seconds` immediately after `compose up -d`; no restart loop, no Bug-#5/#6/#7 regression. |
| 1.2 | container env propagated (incl. `/v1`) | ✅ | `AGENT_ID=gcse-tutor`, `LOCAL_MODEL=gemma4-tutor`, `OPENAI_BASE_URL=http://host.docker.internal:9000/v1` (suffix preserved), `LLM_BASE_URL=http://host.docker.internal:9000`, `NATS_URL=nats://host.docker.internal:4222`, `NATS_USER=rich`, `NATS_PASSWORD=***set***` |
| 1.3 | KV registration | ✅ | `kv ls agent-registry` returns `jarvis / product-owner-agent / architect-agent / gcse-tutor` |
| 1.4 | Manifest advertises 4 tools | ✅ | `tool count: 4` — `tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end` |
| 1.5 | Heartbeat firing | ✅ | First envelope on `fleet.heartbeat.gcse-tutor` arrived in <30s with `status:ready`, `uptime_seconds:30`, `event_type:agent_heartbeat` |
| 2.1 | jarvis boot clean | ⏭ | Skipped — Phase 2/3 are interactive-REPL phases this non-interactive driver could not execute. Dispatch path independently exercised via `nats request` (see §3 below). |
| 2.2 | Live catalogue surfaces tutor | ⏭ | Skipped — see 2.1. KV row + manifest are present per 1.3/1.4; jarvis's live KV watch should pick it up. Will be verified at dress rehearsal. |
| 3 | Dispatch fires + result rendered | ⚠️ partial | **Two** direct dispatches of `tutor_start_session` (one baseline, one with `topic_override="Macbeth — Shakespeare"`) round-tripped cleanly with `success:true`. **One** subsequent `tutor_turn` (dagger soliloquy on the Macbeth session) returned `success:false` with `error_type:LLMProviderError` — see **Bug #9** below. |
| 4.1 | Wire tap on `agents.command.>` | ✅ | Three envelopes captured at [`evidence/dddsw-tutor-demo-2026-05-10-run-2/wire-command.log`](evidence/dddsw-tutor-demo-2026-05-10-run-2/wire-command.log) (correlation_ids `demo-runbook-2026-05-10-run-2-start`, `demo-runbook-2026-05-10-run-2-start-macbeth`, `demo-runbook-2026-05-10-run-2-turn-dagger`). Two preceding `nil body` lines were the operator's earlier failed `echo | nats request` dispatch attempts (the parser surfaced `Failed to parse NATS message as MessageEnvelope`-style errors cleanly without crashing the router; useful proof of the PH2-001 readiness gating doing its job). |
| 4.2 | Wire tap on `agents.result.>` | ✅ | Three envelopes captured at [`evidence/dddsw-tutor-demo-2026-05-10-run-2/wire-result.log`](evidence/dddsw-tutor-demo-2026-05-10-run-2/wire-result.log) — same three correlation_ids. **This is the run-1 → run-2 fix verification: run-1's `wire-result.log` was 0 bytes (Bug #8); this run's is 2356 bytes with two `success:true` and one `success:false` envelope.** |
| 4.3 | TutoringResult captured | ✅ | Two start_session results saved as JSON: [`tutoring-result-baseline-start.json`](evidence/dddsw-tutor-demo-2026-05-10-run-2/tutoring-result-baseline-start.json) (baseline plan) and [`tutoring-result-macbeth-start.json`](evidence/dddsw-tutor-demo-2026-05-10-run-2/tutoring-result-macbeth-start.json) (rule-1 plan with topic_override). No `tutor_turn` artefact (Bug #9). |
| 7.1 | Chat transcript saved | ⏭ | No interactive chat run. |
| 7.2 | Routing-history offload | ⏭ | No supervisor run. |
| 7.3 | command_history.md entry | ⏭ | Operator choice: halt and document via this RESULTS file. No green session to record. |
| 7.4 | RESULTS file written | ✅ THIS FILE | — |
| 8 | Demo close | ⏳ pending | Stack still Up at time of writing (the user invocation that drove this run ends with the RESULTS write; `compose down` is the next operator action). |

---

## Bug catalogue

### Bug #9 — Compose env conflates LLM **provider name** with **model name** (DEMO BLOCKER, config-level)

**Symptom:** First `tutor_turn` dispatch returns `success:false` with:

```json
{
  "error": "Unsupported provider: 'gemma4-tutor'. Expected one of: 'local', 'local-coach', 'bedrock' (Phase 0).",
  "error_type": "LLMProviderError"
}
```

The agent receives the command, dispatches to `mcp/adapter.py::tutor_turn`,
the orchestrator invokes `self._player.respond()`, the player adapter
calls `LLMClient(provider=_default_player_model())` — at which point
`LLMClient.generate()` reaches the `raise LLMProviderError(...)` fallthrough
because none of the `if self.provider == "local"/"local-coach"/"bedrock"`
branches matched. The result envelope is published cleanly (Bug #8 fix
verified — `CommandRouter` surfaces the failure as a structured
`ResultPayload` with `success:false`, not as a missing reply).

**Cause:** [`docker-compose.study-tutor.yml:99`](../../docker-compose.study-tutor.yml#L99):

```yaml
AGENT_MODELS__REASONING_MODEL: ${TUTOR_LOCAL_MODEL:-gemma4-tutor}
```

reuses `TUTOR_LOCAL_MODEL` (which carries a **model alias** like
`gemma4-tutor`, the name registered on llama-swap) as the value for
`AGENT_MODELS__REASONING_MODEL` — but
[`src/study_tutor/llm/client.py:103`](../../src/study_tutor/llm/client.py#L103)
treats that env var as a **provider name**:

```python
class LLMClient:
    def __init__(self, provider: str) -> None:
        self.provider = provider

    def generate(self, prompt, system=None) -> str:
        if self.provider == "local": ...
        if self.provider == "local-coach": ...
        if self.provider == "bedrock": ...
        raise LLMProviderError(f"Unsupported provider: {self.provider!r}. ...")
```

[`_default_player_model()`](../../src/study_tutor/llm/client.py#L47) returns
`AGENT_MODELS__REASONING_MODEL` verbatim. The model selection (the value
sent in the OpenAI-compat payload's `"model": ...` field) is driven
separately by `LOCAL_MODEL` inside `_generate_openai_compat()`
([`client.py:173`](../../src/study_tutor/llm/client.py#L173)).

The same mistake is present at
[`docker-compose.study-tutor.yml:107`](../../docker-compose.study-tutor.yml#L107):

```yaml
AGENT_MODELS__COACH_MODEL: ${TUTOR_COACH_MODEL:-qwen36-workhorse}
```

`qwen36-workhorse` is a model alias, not a provider name. Coach hasn't
fired yet during this run (the failure is on the Player path inside
`run_turn` — `_player.respond()` raises before any Coach call is reached)
so the misconfiguration is latent on that side; it will surface on the
first Coach-mediated turn.

The fix is the analogue of Bug #6 from run-1 but in the opposite
direction: run-1 added the `AGENT_MODELS__COACH_*` env vars to satisfy
the loader's "Coach must be set explicitly" guard (per D-COACH-05);
run-2 surfaces that the **values** for both the Player and Coach env
vars must be **provider names**, with the model aliases moved to the
provider-specific model env vars (`LOCAL_MODEL` for Player —
already correct — and `LOCAL_COACH_MODEL` for Coach — not yet set).

**Confirmed by:**
- [`evidence/dddsw-tutor-demo-2026-05-10-run-2/container.log`](evidence/dddsw-tutor-demo-2026-05-10-run-2/container.log)
  — full 30-line traceback ending at
  `study_tutor.llm.client.LLMProviderError: Unsupported provider: 'gemma4-tutor'`.
- [`evidence/dddsw-tutor-demo-2026-05-10-run-2/wire-result.log`](evidence/dddsw-tutor-demo-2026-05-10-run-2/wire-result.log)
  — the third envelope (correlation_id `demo-runbook-2026-05-10-run-2-turn-dagger`)
  carries `payload.success:false`, `payload.result.error_type:LLMProviderError`,
  and the same error text.
- [`evidence/dddsw-tutor-demo-2026-05-10-run-2/dispatch-reply-dagger-turn.txt`](evidence/dddsw-tutor-demo-2026-05-10-run-2/dispatch-reply-dagger-turn.txt)
  — the same error rendered from the request-reply inbox (proves Bug #1
  dual-publish is firing both sides of the publish even on failure).

**Fix options:**

- **(A)** Two-line compose edit. Change
  `AGENT_MODELS__REASONING_MODEL: ${TUTOR_LOCAL_MODEL:-gemma4-tutor}` to
  `AGENT_MODELS__REASONING_MODEL: ${TUTOR_REASONING_PROVIDER:-local}`,
  and `AGENT_MODELS__COACH_MODEL: ${TUTOR_COACH_MODEL:-qwen36-workhorse}`
  to `AGENT_MODELS__COACH_MODEL: ${TUTOR_COACH_PROVIDER:-local-coach}`.
  Add (or re-purpose) `LOCAL_COACH_MODEL: ${TUTOR_COACH_MODEL:-qwen36-workhorse}`
  + `LOCAL_COACH_BASE_URL: ${TUTOR_COACH_ENDPOINT:-http://host.docker.internal:9000}`
  so the Coach side of `LLMClient._generate_openai_compat` (which reads
  `LOCAL_COACH_MODEL` and `LOCAL_COACH_BASE_URL`) gets the alias and
  endpoint it expects. The existing `LOCAL_MODEL=${TUTOR_LOCAL_MODEL:-gemma4-tutor}`
  line at compose line 82 already serves the Player side correctly.
  Smallest blast radius; preserves the operator override knobs.
- **(B)** Rename the runtime env var contract on the code side. Rather
  than `LLMClient` reading the provider name from `AGENT_MODELS__REASONING_MODEL`,
  introduce `AGENT_MODELS__REASONING_PROVIDER` (and the matching Coach
  twin) and treat the existing `*_MODEL` envs as model aliases. Cleanest
  long-term naming; requires the same compose edit as (A) **plus** a
  Python-side rename and a deprecation period; fights with the existing
  D-COACH-05 / AC-LCA-07 docstrings that name `AGENT_MODELS__COACH_MODEL`
  literally.
- **(C)** Make `LLMClient` accept a model alias when no provider matches
  and infer the provider from the endpoint URL. Highest blast radius;
  hides the configuration intent behind heuristics; not advised for a
  Phase-1 deliverable.

**Recommend (A) for the demo**, **(B) as the proper FEAT-NATS / FEAT-39E1
follow-up.** Repository scope: `study-tutor` (compose + a regression test
under `tests/unit/test_compose_structure.py` asserting both `AGENT_MODELS__*`
values are members of `{"local", "local-coach", "bedrock"}` rather than
model-alias strings).

**Important note:** Bug #9 was fully masked by Bug #8 in run-1 — the
dispatch path raised at `_publish_result` before reaching
`_player.respond()`, so the LLMClient was never constructed with the bad
provider value. The PH2-001 readiness gating and the Bug #1 dual-publish
fix together promote this latent bug from a 600s timeout in run-1 (which
would have been ambiguous between adapter-side and config-side) to a
crisp `success:false` envelope with a precise error message in run-2 —
a real win for diagnosis even though the demo is still red.

There is also a documentation-level mismatch worth surfacing while the
fix is being scoped: the docstring on
[`_default_player_model()`](../../src/study_tutor/llm/client.py#L47)
says it returns "the default player-model **provider** from the
environment" and falls back to `"local"`, which is internally consistent
with the LLMClient contract. The compose-file comments at lines 93–106,
by contrast, describe `AGENT_MODELS__REASONING_MODEL` as "Player model
(REASONING_*)" without ever saying it is a *provider name*. The compose
comment block is what an operator reads when setting up a new fleet
member; updating it is the cheapest way to keep this from reappearing.

---

## What's working — narrative

- **Bug #8 fix verified end-to-end.** `CommandRouter._client` is connected
  immediately after `NATSAdapter.start()`; the `_publish_result` path
  emits on both the canonical `agents.result.gcse-tutor` topic and the
  request-reply inbox (Bug #1 dual-publish). Three successive dispatches
  (two starts + one turn) all produced result envelopes — no timeouts,
  no missing replies, no 32-byte JetStream-PubAck-instead-of-result
  edge case.
- **Failure surface is now structured.** The `tutor_turn` failure
  returned a well-formed `ResultPayload` with `success:false`,
  `error_type:LLMProviderError`, and the verbatim error message —
  exactly the wire shape the supervisor on the jarvis side will expect
  to render back to a learner / chat session. The router's `_safe_invoke`
  path (per PH2-001) is doing its job: handler exceptions are caught and
  reported as structured failures rather than swallowed or re-raised.
- **All four Phase-1 invariants hold.** Tool count 4, manifest names
  match exactly (`tutor_start_session`/`tutor_turn`/`tutor_session_status`/
  `tutor_session_end`), heartbeat fires in <30s, KV row appears alongside
  the other fleet members. The "sixth box on the topology slide" line
  from the talk-track frame is now operationally true for everything
  except the dagger-soliloquy turn itself.
- **`tutor_start_session` business logic works** — both the baseline
  plan (rule_selected `baseline`, "introductory diagnostic" topic) and
  the `topic_override` path (rule_selected `rule-1`, "Macbeth —
  Shakespeare" topic) produce the expected `plan_summary` shape with
  `opening_prompt` / `rationale` / etc. The planner itself is therefore
  unaffected by either Bug #8 or Bug #9.

The talk-track narrative slide is two-thirds true today: the sixth box
exists, registers, heartbeats, listens, dispatches, and returns
structured `start_session` results. The Player LLM call from
`tutor_turn` is the one remaining red arrow.

---

## Next steps with concrete fix-and-rerun list

1. **Fix Bug #9** — apply Option (A) in
   [`docker-compose.study-tutor.yml`](../../docker-compose.study-tutor.yml).
   Two edits:
   - line 99: `AGENT_MODELS__REASONING_MODEL: ${TUTOR_REASONING_PROVIDER:-local}`
     (was `${TUTOR_LOCAL_MODEL:-gemma4-tutor}`)
   - line 107: `AGENT_MODELS__COACH_MODEL: ${TUTOR_COACH_PROVIDER:-local-coach}`
     (was `${TUTOR_COACH_MODEL:-qwen36-workhorse}`)
   - add a `LOCAL_COACH_MODEL: ${TUTOR_COACH_MODEL:-qwen36-workhorse}` line
     so the Coach side of `_generate_openai_compat` picks up the alias.
   - add a `LOCAL_COACH_BASE_URL: ${TUTOR_COACH_ENDPOINT:-http://host.docker.internal:9000}` line
     (or omit and let it fall back to `LOCAL_BASE_URL`).
   - update the compose comment block at lines 93–106 to explicitly say
     "these env vars are **provider names**, not model aliases — see
     `study_tutor.llm.client.LLMClient.__init__` for the canonical
     contract".
   Add a regression assertion in `tests/unit/test_compose_structure.py`
   that the rendered compose's `AGENT_MODELS__REASONING_MODEL` and
   `AGENT_MODELS__COACH_MODEL` values resolve to members of
   `{"local", "local-coach", "bedrock"}`. Track as a FEAT-NATS PH3
   follow-up task (or a fresh PH-NN ticket — "compose env: provider
   name vs model alias separation").
2. **Re-run this runbook end-to-end** (run-3). With Bug #9 fixed, Phases
   0–1 should green-light without retries (they already did this run);
   §3 `tutor_turn` against a warm `gemma4-tutor` should produce a
   `success:true` envelope on `agents.result.gcse-tutor` with a
   substantive `reply` field. Save the resulting `TutoringResult` JSON
   to `docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-3/<correlation_id>.json`
   per §4.3 — **that's the slide artefact for the talk**.
3. **Reconnect the interactive jarvis-chat phases** (§2 + §3) at run-3
   or run-4. Two runs in a row have skipped them. They are mandatory
   for the dress rehearsal — the talk track explicitly narrates
   `dispatch_by_capability` resolution against the live KV catalogue,
   which can only be verified by booting jarvis chat per §2.1 and
   typing the §3.1 prompt. The non-interactive driver has now done as
   much as it can without a human in the REPL.
4. **Dress rehearsal** the day before (2026-05-15). Pre-warm
   `gemma4-tutor` and `qwen36-workhorse` with one throwaway call each
   before going on stage — the first-call latency on a cold model is
   what breaks the "while it runs" narration window in §3.

## Hygiene flags (non-blocking but worth addressing)

- **`event=rag_disabled reason=chromadb_missing`** still fires at boot
  (carried over from run-1's hygiene list — same disposition: ship
  ChromaDB or accept the degraded answer quality and drop the RAG
  framing from the talk).
- **`event=rag_disabled reason=collection_provider_unwired`** —
  same root cause as the chromadb_missing line above.
- **Two `Failed to parse NATS message as MessageEnvelope` ERROR lines
  in `container.log`.** Caused by the operator's two early failed
  `echo | nats request` attempts where the body never reached the
  server. The agent surfaces these cleanly without crashing (PH2-001
  readiness gating + per-message exception handling) so this is purely
  cosmetic; reproducing it requires deliberate malformed input. The
  fact that the agent didn't crash is itself useful evidence — keep
  the log lines as part of `container.log`'s narrative.
- **Compose comment-block drift** — the comments at
  `docker-compose.study-tutor.yml:93-106` describe `AGENT_MODELS__REASONING_MODEL`
  as "Player model (REASONING_*)" without disambiguating provider name vs
  model alias. Update alongside Bug #9 (Option A above).
- **Runbook §0.5 quoted example output** still references `RICH_NATS_USER`
  in fix-discussion paragraphs (see runbook lines 215, 222, 224 — the
  `appmilla → rich` Bug #7 narrative). Bug #7 is now committed and the
  compose default is `rich`; the runbook's §0.5 itself uses the unprefixed
  `NATS_USER`/`NATS_PASSWORD` correctly. The narrative paragraphs are
  fine as historical context but could be reordered into a "Bug history"
  appendix at runbook-cleanup time, separately from this run.

## Evidence index

All under [`docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-2/`](evidence/dddsw-tutor-demo-2026-05-10-run-2/):

- `container.log` — `docker logs study-tutor-gcse-tutor-1` captured
  after the three dispatches. Contains the boot sequence
  (`Registered agent 'gcse-tutor' to fleet.register`, `Subscribed (with
  reply) to command subject 'agents.command.gcse-tutor'`,
  `NATSAdapter ready for agent 'gcse-tutor'`), the two RAG-disabled
  WARNINGs, two `Failed to parse NATS message` ERRORs from the
  operator's earlier malformed dispatches, and the full Bug #9
  traceback at the bottom.
- `wire-command.log` — three envelopes captured from the
  `agents.command.>` tap during the dispatches (correlation_ids
  `demo-runbook-2026-05-10-run-2-start`,
  `demo-runbook-2026-05-10-run-2-start-macbeth`,
  `demo-runbook-2026-05-10-run-2-turn-dagger`). Includes two preceding
  `nil body` lines from the operator's failed dispatch attempts —
  preserved as-is.
- `wire-result.log` — three envelopes captured from the `agents.result.>`
  tap, matching the three command correlation_ids. Two `success:true`
  start_session payloads + one `success:false` turn payload with
  the Bug #9 error_type. **The non-emptiness of this file is the
  Bug #8 fix-verification.**
- `dispatch-reply-baseline-start.txt` — the request-reply inbox capture
  from the first `tutor_start_session` `nats request` (proves Bug #1
  dual-publish is firing).
- `dispatch-reply-macbeth-start.txt` — same for the Macbeth-topic
  start_session.
- `dispatch-reply-dagger-turn.txt` — same for the dagger-soliloquy
  `tutor_turn` (the Bug #9 surface; failure envelope).
- `tutoring-result-baseline-start.json` — the parsed `payload.result`
  block from the baseline start_session, ready to drop on a slide.
- `tutoring-result-macbeth-start.json` — same for the Macbeth-topic
  start_session.
