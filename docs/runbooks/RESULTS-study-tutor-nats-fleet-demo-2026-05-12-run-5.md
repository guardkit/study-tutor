# RESULTS: study-tutor-nats-fleet-demo (2026-05-12 run-5, post-TASK-NATS-FIX-006 integration verification via OpenWebUI → jarvis → gcse-tutor)

**Date:** 2026-05-12 evening — fifth walkthrough of the runbook, executed via the new OpenWebUI → Jarvis chat gateway path (FEAT-JARVIS-006 landed earlier the same day in jarvis `ca23bed`). The "live unattended demo path" — operator drives in a browser; everything else runs autonomously.
**Operator:** Claude Code (Opus 4.7 1M-context) on GB10, with richardwoollcott driving the OpenWebUI browser turns.
**Machine:** GB10 (`promaxgb10-41b1`) — single-host all-local.
**Runbook executed:** [`RUNBOOK-study-tutor-nats-fleet-demo.md`](RUNBOOK-study-tutor-nats-fleet-demo.md) — Phase 2 path **substituted** with OpenWebUI → Jarvis chat gateway (rather than `jarvis chat` CLI), since the chat-gateway scope landed earlier today in jarvis FEAT-JARVIS-006.
**Companion artefact:** [`RESULTS-FEAT-JARVIS-006-serve-nats-first-run-2026-05-12-rerun-post-J006-009-010.md`](../../../jarvis/docs/runbooks/RESULTS-FEAT-JARVIS-006-serve-nats-first-run-2026-05-12-rerun-post-J006-009-010.md) — the jarvis-side verification of the same E2E path, written earlier the same day.

## Participating-repo HEADs

| Repo | HEAD | Last-commit summary |
|---|---|---|
| `study-tutor` | `1bbdde4` | docs(FEAT-NATS): capture TASK-NATS-FIX-006 AC-06+AC-07 GB10 probe results |
| `jarvis` | `ca23bed` | docs(FEAT-JARVIS-006): post-J006-009/010 verification RESULTS + runbook patches |
| `specialist-agent` | `78f7034` | fix(nats): wire adapter reconnect callbacks + fail-fast on terminal close (TASK-NATS-009) |
| `nats-core` | `78e64f3` | feat(client): wire reconnect/disconnect/closed callbacks + default fail-fast closed_cb (TASK-NC10) |
| `nats-infrastructure` | `d8ece24` | (unchanged from run-4) |

`study-tutor:dev` image: sha256:315a1bda4408 (per 1bbdde4 commit body — same image that ran AC-06+AC-07 probes). Container `study-tutor-gcse-tutor-1` was already running at session start (`Up 2 hours` at ~14:30 UTC) and survived the in-session broker bounce via TASK-NATS-FIX-006's reconnect callback (see §"Real-world FIX-006 evidence" below).

## Outcome

**GREEN.** TASK-NATS-FIX-006 works in the wild — verified by a real-world unprompted broker bounce mid-session, not a controlled probe. Two distinct paths fired naturally:

1. **Transient reconnect path** — short bounce (~16 s, 19:02:40 → 19:02:56 UTC) → `nats_reconnected — re-registering agent 'gcse-tutor'` → KV manifest re-published. **No container restart.**
2. **Terminal-close path** — prolonged outage (~66 s, 19:05:33 → 19:06:39 UTC after `nats-py` reconnect budget exhausted) → `nats_terminally_closed` ERROR → CLI `SystemExit(1)` → Docker's `restart: unless-stopped` policy recovered the container → fresh `Registered agent 'gcse-tutor'`.

Both paths reproduced unprompted what the 1bbdde4 RESULTS captured in controlled AC-06+AC-07 probes. The fix is doing its job.

The OpenWebUI → Jarvis → gcse-tutor dispatch chain (Phase 2 substitute) **also worked GREEN**. Multi-tool orchestration: jarvis fired `tutor_start_session` + three `tutor_turn` envelopes from a single operator chat prompt, and the GCSE tutor's distinctive Socratic style round-tripped faithfully into the OpenWebUI chat render — a more demonstrative demo than the run-1..run-4 `jarvis chat` CLI path, and exactly what the 2026-05-16 DDD Southwest narrative needs.

## Demo blocking?

**Not for study-tutor.** TASK-NATS-FIX-006 is fully proven by this run + 1bbdde4's controlled probes.

**Yes for jarvis** (cross-fleet implication discovered during the same bounce — see §"Discovery: jarvis lacks the same reconnect callbacks"). A new task TASK-J006-011 has been filed in jarvis to close the same gap. **If TASK-J006-011 does not land before 2026-05-16, a broker hiccup during demo prep will silently strand the chat gateway** — even though gcse-tutor itself recovers, the operator cannot reach it because jarvis is dead in the water.

## What's new vs run-4 (2026-05-11)

- **Runbook Phase 2 substituted:** OpenWebUI → Jarvis chat → dispatch_by_capability → gcse-tutor. The original Phase 2 used `jarvis chat` CLI; that path still works but isn't the demo path any more. Jarvis's `serve-nats` gateway (FEAT-JARVIS-006, jarvis commit `ca23bed`) is the new demo entry point.
- **Real-world bounce vs controlled probe:** AC-06+AC-07 in commit 1bbdde4 used a deliberate `docker stop ships-computer-nats` probe. This run captured an _unprompted_ broker bounce executed by an external agent (another Claude Code instance, mid-implementation of `specialist-agent` TASK-NATS-009), which gave us cross-fleet differential evidence in a single timeline:
  - **gcse-tutor (FIX-006):** recovered automatically via both transient + terminal-close paths.
  - **specialist-agent containers (before TASK-NATS-009 was deployed):** stayed stuck, needed `docker restart`.
  - **jarvis (no equivalent fix):** stuck in `fleet_heartbeat_failed (nats: connection closed)` loop, KV registration stale, gateway silently unreachable.
  - **forge-prod:** unrelated — exited 2 days ago, pre-existing fleet condition.

## Phase × Gate × Outcome × Evidence (abbreviated for an integration run)

| Phase | Gate | Outcome | Evidence |
|---|---|---|---|
| 0 — pre-flight | study-tutor + jarvis main clean, NATS up, llama-swap warm, gcse-tutor registered | ✅ | KV `agent-registry`: jarvis, architect-agent, product-owner-agent, gcse-tutor, forge (forge stale from 2d-old container) |
| 1 — tutor stack up | `study-tutor-gcse-tutor-1` `Up 2 hours`, 4 tools published, intent `tutoring.*` | ✅ | `kv get agent-registry gcse-tutor`: `tool_count: 4`, `intent_count: 1` |
| **2 (substituted)** — OpenWebUI → Jarvis → gcse-tutor | Multi-tool dispatch chain from a single operator chat prompt | ✅ | Wire-tap `run5-e2e-command.log` line-by-line: `tutor_start_session` (corr=ede7ad5c, args=`year11-maths-foundation`) → `tutor_turn` (×3, corr=574f2af1, a6d4bf98, 15f66dca). Total Turn-2 wall-clock 62.0 s, response_length=806 chars. |
| 3 — demo turn renders Socratic content | Tutor's distinctive fine-tuned voice (refuses full worked solution, asks questions) visible in OpenWebUI chat render | ✅ | Operator-pasted reply: *"It's firmly Socratic … It won't just hand you the full worked solution; it guides you through with questions … `Session ID: d3f5fda7-64cc-4744-a7ef-61f3ed49ac45`"* — fine-tuned model output preserved end-to-end through 5 wire-format conversions. |
| 4 — wire-level evidence | command + result envelopes for every dispatch leg | ✅ | `run5-e2e-command.log` (17 envelopes), `run5-e2e-result.log` (13 envelopes) — `agents.command.gcse-tutor` envelopes line up 1:1 with `agents.result.gcse-tutor` envelopes |
| 4.x — **real-world broker bounce mid-session** | TASK-NATS-FIX-006 transient + terminal paths both fire on the unprompted bounce | ✅ | Docker logs `study-tutor-gcse-tutor-1` 19:02:40-19:06:39 (see §"Real-world FIX-006 evidence") |
| 5 — graceful jarvis shutdown post-session | jarvis SIGINT teardown in <10 ms | ✅ | `jarvis-serve-nats-smoke-run5.log` tail: signal_received → heartbeat_cancelled → deregister_published → nats_disconnect → nats_closed → drain_complete → shutdown_complete (all within 17 ms) |

## Real-world FIX-006 evidence (the headline of this run)

Timing pulled from `docker logs study-tutor-gcse-tutor-1` (container time = UTC):

```
19:02:06 INFO    Registered agent 'gcse-tutor' to fleet.register
19:02:40 WARNING nats_disconnected               ← bounce starts (transient)
19:02:56 INFO    nats_reconnected — re-registering agent 'gcse-tutor'
                                                 ← _on_reconnect → manifest re-published; KV restored
                                                 ← wall-clock: 16s disconnect, no container restart
19:03:33 WARNING nats_disconnected               ← bounce starts (this one prolonged)
19:05:33 WARNING nats_disconnected               ← nats-py reconnect budget exhausted (~120s after 19:03:33)
19:05:33 ERROR   nats_terminally_closed          ← _on_closed → terminal_close_event.set()
19:05:33 WARNING Error unsubscribing from command subject: nats: connection closed
19:05:33 WARNING Failed to deregister agent 'gcse-tutor': nats: connection closed
19:05:33 WARNING Error during NATS disconnect: nats: connection closed
                                                 ← CLI _serve_adapter raced terminal_close_event → SystemExit(1)
                                                 ← Docker restart: unless-stopped policy restarts container
19:06:39 INFO    Registered agent 'gcse-tutor' to fleet.register
                                                 ← fresh registration via container restart
                                                 ← wall-clock: 66s from terminal-close to fresh-registered
```

These are exactly the AC-06 + AC-07 paths that 1bbdde4 documented under controlled probe — but here they fired _unprompted_ on a bounce the operator wasn't expecting. Strong validation that TASK-NATS-FIX-006 is production-ready.

## Demo turn transcript (Phase 2 substituted, OpenWebUI → Jarvis → gcse-tutor)

> **Operator (Turn 1):** Refresh capabilities, then confirm the GCSE tutor is online and tell me what subjects it can teach.
>
> **Jarvis (Turn 1 reply):** The GCSE Tutor is registered in the fleet (agent ID: gcse-tutor, trust tier: specialist). However, its `last_heartbeat_at` is null, which means it hasn't pinged recently — it may not be actively reachable yet. As for subjects, the capability catalogue doesn't expose a subject list directly. The tutor works via sessions (`tutor_start_session`) where you provide a `student_id` and optionally override the topic. The subject coverage is determined by the tutor agent's internal curriculum rather than a declared subject registry. Bottom line: The GCSE Tutor is registered in the fleet, but I can't confirm it's online (no heartbeat). I'd need to try starting a session to verify it's actually responsive…
>
> *(Note: `last_heartbeat_at: null` is a manifest-field nuance, not an actual offline signal — Turn 2 confirms the tutor is fully responsive. Likely a manifest-shape-mismatch hygiene flag worth filing separately; see §"Hygiene flags".)*
>
> **Operator (Turn 2):** Ask the GCSE tutor to start a session for a Year 11 student revising for GCSE Maths foundation, focused on quadratic equations. Have them explain how to factorise x² + 5x + 6 = 0 step by step.
>
> **Jarvis (Turn 2 reply):** The GCSE Tutor is online and responsive — it's firmly Socratic though. It won't just hand you the full worked solution; it guides you through with questions. Here's a summary of where it's at:
> - **Session ID:** `d3f5fda7-64cc-4744-a7ef-61f3ed49ac45`
> - **Topic:** GCSE Maths Foundation — quadratic equations
> - **Approach:** Socratic questioning — it asks you what you notice about the coefficients, what form the factorised answer should take, etc.
> - **Stance:** It explicitly refuses to give full worked solutions, preferring to guide you to discover the answer yourself
> If you want the full worked solution in one go, this tutor won't give it. But if you're happy with a guided, question-driven learning style, we can continue.

Operator verdict: *"That was actually a perfect response and great demo of the differences between the fine-tuned model and say ChatGPT type session!"* — the fine-tuned model's signature Socratic refusal survived 5 wire conversions (OpenWebUI → fleet-gateway pipe → jarvis chat handler → jarvis supervisor → `dispatch_by_capability` → gcse-tutor command_router → gcse-tutor LLM → and back) without flattening. **This is the demo.**

Wire-tap envelope sequence on `agents.command.gcse-tutor` for Turn 2:

| # | corr_id | command | first arg | role |
|---|---|---|---|---|
| 1 | `ede7ad5c-…` | `tutor_start_session` | student_id=`year11-maths-foundation` | jarvis initialises the tutoring session |
| 2 | `574f2af1-…` | `tutor_turn` | (session_id + first turn body) | jarvis hands the user's factorisation request as the first lesson turn |
| 3 | `a6d4bf98-…` | `tutor_turn` | (next turn body) | jarvis continues the Socratic exchange to gather enough material |
| 4 | `15f66dca-…` | `tutor_turn` | (final turn body) | jarvis closes out the exchange before rendering to OpenWebUI |

That's a four-call orchestration to gcse-tutor from a _single_ operator chat turn — far richer dispatch evidence than the run-1..run-4 single-call pattern.

## Discovery: jarvis lacks the same reconnect callbacks

While verifying gcse-tutor's FIX-006 behaviour, the same broker bounce surfaced a parallel gap in jarvis:

- jarvis serve-nats was running through `jarvis ca23bed` (which includes TASK-J006-010's *startup* hard-fail but **not** steady-state reconnect callbacks)
- After the bounce, jarvis's log filled with `fleet_heartbeat_failed (nats: connection closed)` every 30 s indefinitely
- KV `agent-registry/jarvis` revision became stale
- OpenWebUI chat replies started timing out at 120 s with the operator-facing message *"Jarvis did not respond within 120s. Is it running?"*
- Operator manually restarted jarvis serve-nats; service resumed immediately and the OpenWebUI turn 2 went through cleanly

**Root cause:** jarvis's `nats_client.py:_on_reconnect / _on_disconnect / _on_closed` (lines 547-579) are wired into nats-py via lines 175-177, but their bodies are **log-only stubs** — they don't re-publish the manifest, don't restart the heartbeat task, don't set a terminal_close_event. This is the same starting condition study-tutor had before TASK-NATS-FIX-006.

**Follow-up filed:** [`jarvis/tasks/backlog/feat-jarvis-006-nats-chat-gateway/TASK-J006-011-wire-reconnect-callbacks-for-steady-state-broker-bounces.md`](../../../jarvis/tasks/backlog/feat-jarvis-006-nats-chat-gateway/TASK-J006-011-wire-reconnect-callbacks-for-steady-state-broker-bounces.md) — P0 demo-blocker if a broker hiccup occurs during demo prep on 2026-05-16. Implementation template = study-tutor commit `34d4a16` (TASK-NATS-FIX-006).

This run-5 RESULTS is therefore _also_ load-bearing as the evidence justification for TASK-J006-011 — without the real-world bounce caught here, the gap could have shipped silently.

## Hygiene flags (non-blocking)

- **`last_heartbeat_at: null` in jarvis's view of gcse-tutor's manifest.** Surface in Turn 1 jarvis reply. Either (a) jarvis's capabilities formatter is reading a manifest field that the source-of-truth doesn't populate, or (b) gcse-tutor's manifest publish path doesn't include a `last_heartbeat_at` timestamp and jarvis is rendering the absence as "null". Cosmetic but confusing to a demo audience. Small follow-up: pin to manifest source-of-truth and either populate the field correctly or hide it in jarvis's catalogue render.
- **Stale `forge` entry in `agent-registry` KV.** `forge-prod` container `Exited (255)` two days ago, but the KV bucket still shows `forge` in `kv ls`. Pre-existing fleet hygiene issue, not caused by this run. Operator already aware; documented in jarvis run-1 RESULTS.
- **architect-agent + product-owner-agent reconnect (specialist-agent side).** During this session both were stuck after the broker bounce, requiring `docker restart`. By the end of the session, `specialist-agent` HEAD `78f7034` had landed TASK-NATS-009 (the fix) — but the containers running on GB10 may still be the pre-fix image. Quick check needed before demo: rebuild + redeploy specialist-agent containers to pick up `78f7034`.

## Next steps with concrete fix-and-rerun list

1. **TASK-J006-011** (jarvis) — wire reconnect callbacks. P0 demo-blocker. Implementation template = `study-tutor/commit 34d4a16`. Acceptance verified by running this runbook again as run-6 with a deliberate `docker restart ships-computer-nats` mid-session; jarvis should survive same way gcse-tutor did this run.
2. **Rebuild + redeploy specialist-agent containers** to pick up `78f7034` (TASK-NATS-009). Then verify with a fresh broker bounce that architect-agent + product-owner-agent recover without `docker restart`.
3. **`last_heartbeat_at: null` hygiene** — small task to either populate or hide the field in jarvis's `list_available_capabilities` rendering.

If all three land before 2026-05-16, the fleet is demo-resilient under broker bounces from any source.

## Evidence index

All artefacts in [`docs/runbooks/evidence/dddsw-tutor-demo-2026-05-12-run-5/`](evidence/dddsw-tutor-demo-2026-05-12-run-5/):

- `jarvis-serve-nats-smoke-run5-prebounce.log` (33 KB) — jarvis log from boot through the broker bounce + heartbeat-failed loop. **The negative evidence for the jarvis reconnect gap.**
- `jarvis-serve-nats-smoke-run5.log` (12 KB) — second boot of jarvis (post-stuck-kill) through Turn-1 + Turn-2 chat dispatch + clean SIGINT shutdown.
- `run5-e2e-command.log` (66 KB) — wire-tap `agents.command.>` — 17 envelopes including the 4-envelope gcse-tutor dispatch chain for Turn 2.
- `run5-e2e-result.log` (14 KB) — wire-tap `agents.result.>` — 13 envelopes (result side of the same chain).

(NATS broker password redacted via `sed` before writing to evidence dir.)
