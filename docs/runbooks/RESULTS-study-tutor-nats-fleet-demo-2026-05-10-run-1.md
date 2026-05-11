# RESULTS: study-tutor-nats-fleet-demo (2026-05-10 run-1, first verification)

**Date:** 2026-05-10 evening — first verification walkthrough of the runbook (the
"once for verification" pass mandated by the runbook header before the
2026-05-16 demo).
**Operator:** Claude Code (non-interactive driver; interactive jarvis-chat
phases §2–§3 not executed — see Phase 2/3 row in the table below).
**Machine:** GB10 (`promaxgb10-41b1`) — single-host all-local.
**Runbook executed:** [`RUNBOOK-study-tutor-nats-fleet-demo.md`](RUNBOOK-study-tutor-nats-fleet-demo.md)
(at study-tutor `82f2aba`).

## Participating-repo HEADs

| Repo | HEAD | Last-commit summary |
|---|---|---|
| `study-tutor` | `82f2aba` | history and tasks |
| `jarvis` | `2a70cb6` | updated runbooks and results |
| `specialist-agent` | `153a210` | RAG feature spec and plan |
| `nats-core` | `01e796e` | updated version |
| `nats-infrastructure` | `d8ece24` | Merge remote-tracking branch 'origin/main' |

Image tags:

- `study-tutor:dev` — built **2026-05-10 20:28 BST** during this run, after
  Bug #5 patch (the 13:45 build that was sitting on disk at the start of
  Phase 0 was stale relative to `src/study_tutor/adapters/`, which had
  been rewritten at 20:02 — caught by §0.3's "post the last code change
  to `src/study_tutor/adapters/`" check).

**Companion files (prior runs of the same runbook):** none — first
execution.

**In-tree changes applied during this run** (uncommitted on `main` at run
end; user explicitly chose to halt rather than continue patching, so any
of these can be reverted before fixing Bug #8 properly):

- [`Dockerfile`](../../Dockerfile) — added `COPY study-tutor/roles/`,
  `COPY study-tutor/data/`, and `COPY study-tutor/.guardkit/graphiti.yaml`
  after the `src/` copy. Fixes Bug #5.
- [`docker-compose.study-tutor.yml`](../../docker-compose.study-tutor.yml) — added
  `AGENT_MODELS__COACH_MODEL` / `AGENT_MODELS__COACH_ENDPOINT` (default
  `qwen36-workhorse` on the same llama-swap host). Fixes Bug #6.
- [`docker-compose.study-tutor.yml`](../../docker-compose.study-tutor.yml) —
  changed `NATS_USER` default from `appmilla` to `rich`. Fixes Bug #7.

---

## Outcome

❌ **RED — DEMO BLOCKED.** Phases 0–1 fully green after three configuration
fixes (Bugs #5–#7). Phase 4.1 captured the inbound `agents.command.>`
envelope from a non-interactive direct dispatch test, but Phase 4.2
captured **zero** result envelopes: the in-process `CommandRouter` raises
`RuntimeError: client is not connected` from `_publish_result` (Bug #8),
so no `agents.result.gcse-tutor` payload is ever emitted. The interactive
chat phases (§2–§3) were not executed because the dispatch path is
demonstrably broken — running them through jarvis would have produced
the identical 600s timeout.

The most load-bearing piece of evidence is the container traceback in
[`evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log`](evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log)
showing `command_router.py:234 → publish_raw → RuntimeError: client is
not connected`, paired with the empty
[`evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-result.log`](evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-result.log).

## Demo blocking?

**YES.** Demo cannot proceed until Bug #8 is fixed. Bugs #5–#7 are
shipped patches in the working tree; either keep and commit them, or
revert and replicate via the `evidence/.../container.log` traceback.

The next walkthrough's prerequisite is a connected `CommandRouter._client`
(or, equivalently, a router that publishes via the adapter's existing
client). Re-running the runbook should then go green through Phase 1.5,
and the direct-dispatch test (re-run of the §4 wire-tap experiment with
`nats request agents.command.gcse-tutor`) should produce a result
envelope on `agents.result.gcse-tutor` with `payload.success: true`.

---

## What's new vs prior run

First execution — no prior comparison.

---

## Phase × Gate × Outcome × Evidence summary

| Phase | Gate | Outcome | Evidence |
|---|---|---|---|
| 0.1 | study-tutor main + clean tree | ✅ | clean tree on `main` at `82f2aba`; top-of-log includes FEAT-39E1 PH1-002 (manifest factory) and PH1-005 (NATSAdapter salvage) |
| 0.2 | specialist-agent + jarvis main | ✅ | specialist-agent `153a210`, jarvis `2a70cb6`; both clean |
| 0.3 | `study-tutor:dev` image current | ⚠️ → ✅ | Initial image (13:45) was stale vs `src/study_tutor/adapters/` (20:02). Rebuilt twice — once after Bug #5 Dockerfile patch, once again to land that — final image `17568088bfa5` at 20:28. |
| 0.4 | llama-swap + `gemma4-tutor` | ✅ | port 9000 listening; `/v1/models` lists `architect-agent`, `gemma4-tutor`, `nomic-embed`, `qwen36-workhorse`, `qwen-graphiti` |
| 0.5 | NATS up + APPMILLA creds | ✅ | `ships-computer-nats` Up (healthy, 5h); `RICH_NATS_PASSWORD` set from `.env` |
| 0.6 | Canonical NATS provisioning | ✅ | `verify-nats.sh` 7/7 streams (PIPELINE/AGENTS/JARVIS/NOTIFICATIONS/SYSTEM/FLEET/FINPROXY) + APPMILLA + FINPROXY auth checks all PASS |
| 1.1 | tutor stack up | ✅ (after 4 retries) | First three attempts crash-looped — see Bugs #5, #6, #7. Fourth attempt: `study-tutor-gcse-tutor-1   Up 12 seconds`, no restart. |
| 1.2 | container env propagated (incl. `/v1`) | ✅ | `OPENAI_BASE_URL=http://host.docker.internal:9000/v1` (suffix preserved); `LOCAL_MODEL=gemma4-tutor`, `AGENT_MODELS__COACH_MODEL=qwen36-workhorse`, `AGENT_MODELS__REASONING_MODEL=gemma4-tutor`, `NATS_USER=rich` |
| 1.3 | KV registration | ✅ | `kv ls agent-registry` returned `jarvis / product-owner-agent / architect-agent / gcse-tutor` |
| 1.4 | Manifest advertises 4 tools | ✅ | `tool count: 4` — `tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end` |
| 1.5 | Heartbeat firing | ✅ | First envelope on `fleet.heartbeat.gcse-tutor` arrived in <30s with `status:ready`, `uptime_seconds:30`, `event_type:agent_heartbeat` |
| 2.1 | jarvis boot clean | ⏭ | Skipped — Phase 2/3 are interactive-REPL phases this run could not execute. The dispatch path was independently exercised via `nats request` (see §3 below) and shown broken at the agent-side, which would also break a jarvis-driven dispatch. |
| 2.2 | Live catalogue surfaces tutor | ⏭ | Skipped — see 2.1. The KV row is present (1.3); jarvis's live KV watch should pick it up — not verified this run. |
| 3 | Dispatch fires + result rendered | ❌ | Direct `nats request agents.command.gcse-tutor` with a hand-crafted `MessageEnvelope{event_type=command, payload=CommandPayload{command="tutor_start_session", args={student_id:"demo-student-001"}}}` was published successfully; the agent received and dispatched the command (proven by container log + wire-command.log) but failed to publish the result back. **See Bug #8.** |
| 4.1 | Wire tap on `agents.command.>` | ✅ | One envelope captured at [`evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-command.log`](evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-command.log) — correlation_id `demo-runbook-1778441600-start` |
| 4.2 | Wire tap on `agents.result.>` | ❌ | Zero envelopes — [`evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-result.log`](evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-result.log) is empty (0 bytes). |
| 4.3 | TutoringResult captured | ❌ | No result to capture. |
| 7.1 | Chat transcript saved | ⏭ | No interactive chat run. |
| 7.2 | Routing-history offload | ⏭ | No supervisor run. |
| 7.3 | command_history.md entry | ⏭ | Not added — operator chose to halt and document via this RESULTS file instead of recording a green session. |
| 7.4 | RESULTS file written | ✅ THIS FILE | — |
| 8 | Demo close | ⚠️ | Tutor stack brought down via `compose down` (graceful — `gcse-tutor` deregistered from `agent-registry` KV; verified absent post-shutdown). NATS, llama-swap, specialist-agent dual-role stack left running. |

---

## Bug catalogue

### Bug #5 — Dockerfile does not copy runtime assets (`roles/`, `data/`, `.guardkit/graphiti.yaml`) into the image (DEMO BLOCKER)

**Symptom:** Container restart-loops at startup. First layer of the gap:

```
FileNotFoundError: Role manifest not found:
/workspace/study-tutor/roles/tutor/role.yaml.
Ensure the bash wrapper cd's to the absolute repo root (SR-02).
```

After patching `roles/` + `data/` into the Dockerfile, the next layer
surfaced:

```
FileNotFoundError: graphiti config not found at .guardkit/graphiti.yaml.
Refusing to silently fall back to defaults — see DECISION-DF-001 / AC-LOAD-06.
Run from the project root or pass an explicit path.
```

Both surface from `_build_nats_runtime` at boot
([`src/study_tutor/cli/main.py:491`](../../src/study_tutor/cli/main.py#L491)
and
[`:502`](../../src/study_tutor/cli/main.py#L502)),
so the agent never reaches its NATS connect.

**Cause:** [`Dockerfile`](../../Dockerfile) copies only application code:

```dockerfile
COPY study-tutor/pyproject.toml study-tutor/uv.lock ./
COPY study-tutor/src/ ./src/
```

`roles/`, `data/`, and `.guardkit/graphiti.yaml` are runtime assets
required at boot but never shipped into the image. The role-manifest
loader and the graphiti-config loader both refuse to fall back to
defaults (deliberately, per DECISION-DF-001 / AC-LOAD-06), so the missing
files crash the process.

**Confirmed by:** [`evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log`](evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log)
captures the post-patch traceback; the pre-patch traceback was identical
in shape but at the `roles/tutor/role.yaml` line. `docker run --rm
--entrypoint sh study-tutor:dev -c 'ls /workspace/study-tutor/'` on the
13:45 image confirmed only `src/`, `pyproject.toml`, `uv.lock`, `.venv`
present.

**Fix options:**

- **(A)** Add `COPY study-tutor/roles/`, `COPY study-tutor/data/`, and
  `COPY study-tutor/.guardkit/graphiti.yaml` to the Dockerfile after the
  `src/` copy. **Applied during this run** — the working tree has the
  patch.
- **(B)** Bind-mount `roles/`, `data/`, and `.guardkit/` via the compose
  file. Fast but couples the image to the host layout — not what we want
  for a Phase-3 "ships under the same operational shape" demo.
- **(C)** Move role/data resolution to packaged resources via
  `importlib.resources`. Cleanest long-term; biggest blast radius.

**Recommend (A).** Repository scope: `study-tutor`. Worth adding a
regression assertion to
[`tests/unit/test_compose_structure.py`](../../tests/unit/test_compose_structure.py)
(or a sibling test) that the built image contains these three asset
paths, so the same gap doesn't reappear.

**Important note:** Bug #5 fully masked Bugs #6, #7, and #8 — fixing it
peeled them in sequence on subsequent boot attempts.

---

### Bug #6 — `AGENT_MODELS__COACH_MODEL` not configured in compose (DEMO BLOCKER)

**Symptom:** After Bug #5 fix, container crash-loops with:

```
study_tutor.llm.client.LLMProviderError: AGENT_MODELS__COACH_MODEL is not set.
Phase-1 requires the Coach provider to be explicitly configured and to differ
from AGENT_MODELS__REASONING_MODEL (the D3 two-provider invariant ...).
```

Surfaces in `_build_nats_runtime` → `MCPAdapter.__init__` →
`orchestrator_factory()` → `_default_coach_model()`
([`src/study_tutor/llm/client.py:85`](../../src/study_tutor/llm/client.py#L85)).
The loader is explicit: per D-COACH-05 (FEAT-6CC5) **no fallback** is
permitted.

**Cause:** [`docker-compose.study-tutor.yml:85`](../../docker-compose.study-tutor.yml#L85)
sets `AGENT_MODELS__REASONING_MODEL` (Player) but never sets the Coach
counterpart, and the validator forbids them being equal.

**Confirmed by:** Container traceback in
[`evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log`](evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log).

**Fix options:**

- **(A)** Add `AGENT_MODELS__COACH_MODEL` + `AGENT_MODELS__COACH_ENDPOINT`
  to compose, mirroring the existing REASONING_* pattern, with a
  `TUTOR_COACH_MODEL` override knob. **Applied during this run** with
  default `qwen36-workhorse` (operator-confirmed). The endpoint defaults
  to the same llama-swap.
- **(B)** Set the two env vars at the shell before `compose up`. Demo-
  only fix; doesn't survive restarts cleanly.
- **(C)** Defer Coach configuration into the role manifest. Largest
  change.

**Recommend (A)** — repository scope: `study-tutor`. The choice of
default Coach model is a real call, not just plumbing — `qwen36-workhorse`
is already loaded on the same llama-swap and is the supervisor's model
on the jarvis side, so demo-day GPU contention is real and should be
profiled at rehearsal time.

**Important note:** Masked by Bug #5 until it was fixed. Once Bug #5
shipped, Bug #6 fired on the next boot attempt.

---

### Bug #7 — `NATS_USER` default in compose is `appmilla` (account name), not `rich` (user name) (DEMO BLOCKER)

**Symptom:** After Bugs #5–#6 fixes, container repeatedly logs:

```
nats.errors.Error: nats: 'Authorization Violation'
```

every two seconds while `nats-py` retries the connect. The container
itself stays Up (the auth retry loop doesn't crash the process), but
registration to `agent-registry` never happens and no command subscription
is established.

**Cause:** [`docker-compose.study-tutor.yml`](../../docker-compose.study-tutor.yml)
had `NATS_USER: ${RICH_NATS_USER:-appmilla}`. `appmilla` is the **account**
name in
[`nats-infrastructure/config/accounts/accounts.conf.template`](../../../nats-infrastructure/config/accounts/accounts.conf.template);
the actual **user** in the APPMILLA account is `rich`. Sending `appmilla`
as the username triggers Authorization Violation. The runbook's §0.5 also
exports `RICH_NATS_USER=appmilla`, which would propagate the same wrong
value if the operator follows the runbook verbatim.

**Confirmed by:** Container log at
[`evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log`](evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log)
(post-Bug-#6 attempt). Cross-checked against
[`nats-infrastructure/config/accounts/accounts.conf.template:30-50`](../../../nats-infrastructure/config/accounts/accounts.conf.template#L30)
which defines the APPMILLA account with users `rich` and `james` — no
user named `appmilla`.

**Fix options:**

- **(A)** Change the compose default to `${RICH_NATS_USER:-rich}`.
  **Applied during this run.** Update the runbook §0.5 to drop the
  `RICH_NATS_USER=appmilla` export (or change it to `=rich`).
- **(B)** Leave compose alone and require `RICH_NATS_USER=rich` to be
  exported every time. Pushes the burden onto every operator and contradicts
  the runbook.
- **(C)** Allow either `rich` or `appmilla` at the NATS-server config
  level by adding a duplicate user entry. Not advised — `appmilla` is
  semantically the account, conflating it with a user name muddies the
  multi-tenancy model.

**Recommend (A)** — repository scope: `study-tutor` (compose) +
`study-tutor` (runbook). Two-line edit.

**Important note:** Masked by Bugs #5 and #6. The architect-agent fleet
member registers fine (visible in `agent-registry`) which suggests its
compose has the right user — worth a one-line check that the architect
compose says `NATS_USER: rich` (or has that as the default) so that
study-tutor's compose can be aligned.

---

### Bug #8 — `CommandRouter._client` is constructed but never connected (DEMO BLOCKER, code-level)

**Symptom:** Container is up and registered (Phase 1 fully green), but the
moment a command envelope arrives the router fails:

```
File "/workspace/study-tutor/src/study_tutor/adapters/command_router.py", line 234, in _publish_result
    await self.client.publish_raw(
File "/workspace/nats-core/src/nats_core/client.py", line 242, in publish_raw
    raise RuntimeError(msg)
RuntimeError: client is not connected
```

Wire-tap evidence: `agents.command.gcse-tutor` captured one envelope
(the test command landed); `agents.result.gcse-tutor` captured zero — the
agent received the command, started processing, and the result-publish
path raised, so no result ever made it onto the wire.

**Cause:** [`src/study_tutor/cli/main.py:516`](../../src/study_tutor/cli/main.py#L516)
constructs a *second* `NATSClient` solely for the router:

```python
nats_client = NATSClient(config.nats, source_id=agent_id)
router = CommandRouter(..., client=nats_client)
adapter = NATSAdapter(config, manifest, command_router=router)
```

Only `NATSAdapter._client` is connected (in `NATSAdapter.start()`); the
router's `nats_client` is never `connect()`ed. The first time the router
hits the Bug-#1 dual-publish path
([`command_router.py:236`](../../src/study_tutor/adapters/command_router.py#L236)
— `await self.client.publish_raw(reply_to, ...)`), it raises. Almost
certainly an incomplete piece of the recent FEAT-39E1 PH1-005 NATSAdapter
salvage / PH2-001 readiness gating sequence visible in the git history.

**Confirmed by:**
[`evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log`](evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log)
(traceback after the test dispatch);
[`evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-command.log`](evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-command.log)
(one envelope captured, correlation_id `demo-runbook-1778441600-start`);
[`evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-result.log`](evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-result.log)
(empty file).

**Fix options:**

- **(A)** In `NATSAdapter.start()`, immediately after
  `await self._client.connect()`, inject the connected client into the
  router: `self._command_router.client = self._client`. One line. Reuses
  the adapter's connection. Smallest blast radius.
- **(B)** Make `_build_nats_runtime` async (or wrap an `asyncio.run`) and
  `await nats_client.connect()` before passing to CommandRouter. Two NATS
  connections per process; wasteful and duplicates lifecycle management.
- **(C)** Refactor so `CommandRouter` doesn't own a client — `NATSAdapter`
  constructs the router internally and gives it whatever publish helper it
  needs. Cleanest architectural fix; biggest blast radius. Probably the
  right end-state for FEAT-39E1.

**Recommend (A) for the demo**, **(C) as the proper FEAT-39E1 task.**
Add a regression test that `CommandRouter._publish_result` succeeds (or
at least that `self.client.is_connected` is true) immediately after
`NATSAdapter.start()` returns. Pair test: a full round-trip integration
test under `tests/` that publishes a `CommandPayload` and asserts a
`ResultPayload` lands on `agents.result.gcse-tutor`.

**Important note:** Masked by Bugs #5–#7. This is the bug the runbook
exists to surface — Reference Bug #1 is precisely the same wire-level
failure mode (no result envelope ever materialises), but for a different
root cause. The Reference Bug #1 fix is in `NATSAdapter`; Bug #8 is the
sibling failure in `CommandRouter` that the dual-client wiring re-introduced.

---

## What's working — narrative

- **Infrastructure layer:** NATS JetStream up healthy on `ships-computer-nats`;
  llama-swap serving `gemma4-tutor`, `qwen36-workhorse`, `qwen-graphiti`,
  `architect-agent`, `nomic-embed`. `verify-nats.sh` passes 7/7 streams.
  APPMILLA + FINPROXY auth working. NATS-infrastructure side of the demo
  is unambiguously demo-ready.
- **study-tutor image build:** `scripts/docker-build.sh` with the BuildKit
  named context (`--build-context nats-core=../nats-core`) is clean; cache
  layering is correct (only `src/` and the new asset COPYs invalidate;
  `uv sync` of dependencies stays cached). After Bug #5 fix the image is
  bootable.
- **Container lifecycle:** Once Bugs #5–#7 are patched, the container reaches
  `NATSAdapter ready for agent 'gcse-tutor'` in ~3s. `compose down` is
  graceful — the `gcse-tutor` row is removed from `agent-registry` KV
  on shutdown (verified post-run), so no §6 stale-registry cleanup is
  required.
- **Capability registration:** `gcse-tutor` registers alongside `jarvis`,
  `architect-agent`, `product-owner-agent` in `agent-registry` KV with
  the correct four-tool manifest (`tutor_start_session`, `tutor_turn`,
  `tutor_session_status`, `tutor_session_end`).
- **Heartbeat:** Heartbeat envelopes flow on `fleet.heartbeat.gcse-tutor`
  with correct shape (`status:ready`, `agent_id:gcse-tutor`,
  `event_type:agent_heartbeat`, `uptime_seconds` increasing). The fleet's
  liveness signal works end-to-end.
- **Inbound dispatch:** `agents.command.gcse-tutor` is subscribed; the
  inbound envelope from a `nats request` test was received and parsed
  (the container reached `_publish_result` before raising — i.e. the
  command verb was understood, the role/coach were resolved, the result
  payload was constructed). The break is at the **publish-back** step,
  not at parsing or business logic.

The demo narrative slide ("five boxes plus a sixth") is half-true today:
the sixth box exists, registers, heartbeats, and listens on the right
subject. The arrow back from box 6 is broken at the `RuntimeError: client
is not connected` line.

---

## Next steps with concrete fix-and-rerun list

1. **Fix Bug #8 (`CommandRouter._client` never connected)** — apply
   Option (A) in `NATSAdapter.start()`: after `await self._client.connect()`,
   `self._command_router.client = self._client`. Add a unit test asserting
   `router.client.is_connected` after `adapter.start()`. Run the existing
   PH1-005/PH1-007 unit tests to confirm no regression. Track as a task
   under FEAT-39E1 (mentioned in commits `7c21475` and `b83151b` —
   either PH1-005 follow-up or a new PH-NN ticket explicitly about the
   dual-client wiring).
2. **Decide on Bugs #5–#7 disposition.** The patches are in the working
   tree but uncommitted. Options:
   - Commit them as `fix(FEAT-39E1): ship roles/data/.guardkit and Coach config + correct NATS user` (or split into three commits matching each bug). Lowest-effort path to a green next run.
   - Revert and treat each as a separate FEAT-39E1 task with its own
     test-coverage discipline. Slower, but matches FEAT-39E1's tracked-
     task style.
3. **Update the runbook.** §0.5's `RICH_NATS_USER=appmilla` export is
   wrong (Bug #7) and should either be deleted (the compose default
   covers it once the default is `rich`) or changed to `RICH_NATS_USER=rich`.
   Re-add an explicit Phase 0 step that asserts the image timestamp is
   after the most recent `src/study_tutor/adapters/`, `roles/`, `data/`,
   or `.guardkit/graphiti.yaml` modification — the runbook's §0.3 only
   names `src/study_tutor/adapters/`, which let this run's stale-image
   problem slip until I happened to read it carefully.
4. **Re-run this runbook end-to-end.** With Bug #8 fixed and the in-tree
   patches committed, Phases 0–1 should green-light without re-tries and
   §3 / §4 should produce both the inbound `agents.command` envelope and
   the outbound `agents.result` envelope. Save the resulting
   `TutoringResult` JSON to
   `docs/runbooks/evidence/dddsw-tutor-demo-<DATE>/<correlation_id>.json`
   per §4.3 — that's the slide artefact for the talk.
5. **Add the interactive jarvis-chat phases** (§2 + §3) to the next run.
   This run's halt happened on the agent side, so the interactive phases
   were skipped. They are mandatory for the dress rehearsal — the talk
   track explicitly narrates `dispatch_by_capability` resolution against
   the live KV catalogue, which can only be verified by booting jarvis
   chat per §2.1 and typing the §3.1 prompt.
6. **Dress rehearsal** the day before (2026-05-15). Warm `gemma4-tutor`
   and `qwen36-workhorse` with one throwaway call each before going on
   stage — the first-call latency on a cold model is the kind of thing
   that breaks the "while it runs" narration window in §3.

## Hygiene flags (non-blocking but worth addressing)

- **`event=rag_disabled reason=chromadb_missing`** — container boot logs
  this WARNING. The image doesn't ship ChromaDB; the RAG path is
  silently disabled. Won't block the §3 demo turn (the runbook narrative
  doesn't mention RAG-grounded answers), but the tutor's response quality
  will be lower than when run from the host venv. Decide before the demo:
  ship ChromaDB in the image, or accept the degraded answer quality and
  drop the RAG framing entirely.
- **`event=rag_disabled reason=collection_provider_unwired`** —
  `MCPAdapter` logs this immediately after the `chromadb_missing` warning.
  Same root cause; same disposition decision.
- **In-tree uncommitted changes after runbook execution.** Three files
  modified (Dockerfile, docker-compose.study-tutor.yml, this RESULTS
  file). Decide commit/revert before any other work continues against
  `main` — easy to lose the patches.
- **Runbook drift.** §0.5 export instructions are wrong (Bug #7 root).
  §1.2 expected output for `NATS_URL` shows `nats://appmilla:***@...`
  format which doesn't match the current compose (where user/pass come
  from separate env vars, not the URL). Update the runbook to match the
  compose contract.

## Evidence index

All under [`docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/`](evidence/dddsw-tutor-demo-2026-05-10-run-1/):

- `container.log` — `docker logs study-tutor-gcse-tutor-1` captured
  immediately before `compose down`. Contains the full Bug #8 traceback
  at the bottom, plus the boot sequence showing `Registered agent
  'gcse-tutor' to fleet.register`, `Subscribed (with reply) to command
  subject 'agents.command.gcse-tutor'`, and the two RAG-disabled WARNINGs.
- `wire-command.log` — single envelope captured from the
  `agents.command.>` tap during the direct-dispatch test
  (correlation_id `demo-runbook-1778441600-start`).
- `wire-result.log` — empty (0 bytes). This emptiness *is* the evidence
  for Bug #8.
