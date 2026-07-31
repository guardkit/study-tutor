# Handoff — backend support for the live robot-session mirror (spark lane)

**For:** the study-tutor backend session on **spark** · **From:** the MacBook/app leg · **Date:** 2026-07-31
**Method:** orchestrated-build-playbook (`ai-transition/docs/ways-of-working/playbook/orchestrated-build-playbook.md`) — design pass done for you below; the build is coach-gated stages, local path-limited commits, nothing pushed until your review.
**Sources of truth:** the mission (`docs/software-factory-mission-statement-2026-07-25.md`) and THE PLAN (`docs/software-factory-plan-of-record.md`) are WHY/WHAT; this is one lane's WHAT-to-build. No lane assumes a frontier coordinator (M0).

---

## The feature, in plain language

When Lilymay is in a spoken tutoring session with the **Reachy Mini robot**, she wants to **watch that same conversation appear on her phone in real time** — so when the robot later asks her to string together everything she's worked through, she can glance at the phone and refer back before answering. It's a **read-only live view** of the session the robot is driving.

This works because the robot and the phone are the **same study-tutor session**: the robot's `ask_tutor` tool calls `start` with `resume_if_active: true, subject: "english"`, so its turns land on Lilymay's one active `(lilymay, english)` session — the same cross-device pickup proven at the 2026-07-05 D8 walk. The phone just needs to *watch* that session grow.

## Design pass — the session-API seams (verified file:line, not assumption)

- **`GET /api/sessions/{id}/resume`** → `{session_id, student_id, status, turns: [{role, content, ts}]}` — the **full ordered transcript**. Works while the session is **active**; raises `SessionEnded` once ended (`src/study_tutor/http/app.py` `resume_session`, ~:330-365). Ownership is enforced from the bearer token (`_resolve_student_id`), so the phone signed in as `lilymay` may resume the session the robot drives.
- **`GET /api/sessions/{id}/status`** → `{session_id, student_id, status, turn_count, started_at, last_activity, resumable}` — **cheap metadata**, works for **active *and* ended** sessions (`app.py` `session_status`). `turn_count` here is user+tutor **pairs** (`turn_count // 2` at the projection, ~:26); `resume`'s `turns[]` are the individual rows.
- **Discovery:** the phone finds the live session via `GET /api/sessions?status=active` filtered to `subject=english` (the app already lists active sessions on Home).
- **What does NOT exist:** there is **no** turns-since/delta endpoint and **no** new-turn push. The only session-stream WebSocket (`/api/sessions/{id}/ws`, `app.py:617`) is the voice path and returns `NotImplementedError` for session streaming.

### Conclusion the app lane is building on
**The live mirror ships app-side on the endpoints that exist today** — poll `status` every ~3 s; when `turn_count` rises, fetch `resume` and render the new rows read-only (reusing the ended-session transcript rendering), and handle the active→ended transition (keep the last transcript, show "session ended"). **No backend change is required for a functional v1.** The backend work below is **enhancement**: efficiency (stop re-pulling the whole transcript) and true real-time (kill the ~3 s poll lag). Build it if the plan-of-record rates the polish above other spark work; otherwise mark it a named, dated deferral (playbook amendment 5 — no silent parking).

---

## What to build (stages — copy into the playbook skeleton's STAGES array)

### Stage 1 — `turns-since` delta read (efficiency) · scope M · **recommended**
`GET /api/sessions/{id}/turns?since={n}` → `{session_id, status, turns: [{role, content, ts}], next: <int>}`, returning **only** the transcript rows at index ≥ `n` (0-based into the same ordered rows `resume` returns), plus `next` = the new total row count for the client's next poll. `since` beyond the end returns `turns: []` (not an error). The phone polls this instead of re-pulling the full transcript, so update cost is O(new rows), not O(whole conversation).

- **Seat it occupies (amendment 5):** the phone's live-mirror poll calls `turns?since=` in place of `status`+`resume`. Name it in the plan; don't ship it unseated.
- **Fences (verbatim in PREFLIGHT):** ownership from the bearer only (never client-asserted `student_id`); same `{role, content, ts}` row shape as `resume` (byte-identical field names) so the app's existing parser is reused; `since` is a plain row offset (not a timestamp); works for **active and ended** sessions (unlike `resume`, so the poll survives the end transition); additive route — it does **not** touch the six frozen session verbs or their status codes, so **no `CONTRACT_SHA`/`BINDING_SHA` re-pin** (it's a new read verb, like `GET /api/student-model` was — binding `docs/design/contracts/API-session-http-binding.md`).

### Stage 2 — real-time push (kill the poll lag) · scope L · **needs a plan ruling first**
Push new turns to a subscribed viewer so the robot's question appears on the phone the instant it's stored, with no ~3 s lag. Options for the design pass to choose between (don't pre-decide): SSE (`text/event-stream`) on a `GET …/turns/stream` — simplest, one-way, fits a read-only viewer; **or** extend the existing `/ws` route to emit `turn_appended` frames. Either way it's a **read/notify** channel, not a new write path.

- **Gate this on a ruling** (amendment 6 — no fourth owner act invented; if this needs one, park with a §8 note by name). v1 (poll) already satisfies the feature; Stage 2 is a UX upgrade, so it should earn its place against the rest of the spark backlog rather than ride in automatically.

---

## PREFLIGHT the builders must execute (not redesign)

```
You are an Opus EXECUTOR building the turns-since delta read in
/Users/richardwoollcott/Projects/appmilla_github/study-tutor (spark checkout equivalent).
BINDING SPEC — read in full first: this handoff §"What to build", and
docs/design/contracts/API-session-http-binding.md (row shape + additive-route rules).
RULES: build to spec verbatim, do not redesign; tests for everything (unit for the service
read + route test for the envelope/ownership/since-semantics, hermetic — no live models);
commit LOCALLY, path-limited to the files you built; NEVER push or deploy.
FENCES: ownership resolved from the bearer only; {role,content,ts} rows byte-identical to
resume; since is a row offset; empty (turns:[]) when since >= total; works for active AND
ended sessions; additive route — do not alter the six session verbs or their status codes;
ephemeral/no-audio-at-rest is unaffected (this is text turns only).
BROKER ISOLATION (standing): NEVER connect to, publish to, or subscribe on any NATS broker
(no nats CLI, no client library, no port 4222). Tests needing a broker use a mock/fake or an
in-test server on an ephemeral port; if a test would need nats://…:4222 it is out of scope —
report it.
```

**Coach (verify by driving, per stage):** run the new tests yourself and read the diff. Confirm: the row shape equals `resume`'s exactly; `since=0` equals the full transcript; `since=total` returns `[]`; a non-owner's token is rejected; an ended session still returns its rows; and grep the stage's diff + tests for live-broker access (`nats://`, `:4222`, `nats sub|pub|stream`, NATS client imports in non-mock code) → any hit is a BLOCKER. `blocker=true` only for a defect Stage 2 must not build on.

---

## The app side (so you know the consumer)

Built on the MacBook/app lane, no backend dependency for v1: discover via `listSessions(status:active)`; poll (Stage-1 endpoint if it lands, else `status`→`resume`); render read-only, reusing `SessionScreen`'s ended-state transcript view; graceful active→ended handoff. When Stage 1 ships, the app swaps its poll to `turns?since=` behind the same UI. The app change is additive and does not gate your work.

## Related spark-lane items already written up (not this handoff's scope — pointers only)

- **TTS ~60 s audio cap** — long spoken replies lose their tail; investigation + options (server-side reply chunking recommended) in `docs/runbooks/INVESTIGATION-voice-tts-audio-60s-cap.md`.
- Standing spark backlog from the 07-26 handoff: RAG `[rag]` extra (`rag_disabled reason=chromadb_missing`), the `:8101` keycloak standup on spark, the fleet-gateway re-point (GB10→spark `:8100`), and the Phase-D GB10 retirement / standing-model-posture decision.

---

## The greenlight prompt (paste into the spark coordinator session)

> *Orchestrate the backend support for the phone's live robot-session mirror. Spec = `docs/runbooks/HANDOFF-spark-live-robot-session-mirror.md` (this doc — read all of it) grounded in the session binding it names. The design pass is done (seams verified file:line); v1 already ships app-side on existing endpoints, so this is enhancement — confirm against the plan-of-record that Stage 1 (the `turns-since` delta read) earns its place before building, and treat Stage 2 (real-time push) as ruling-gated. Mechanism: the playbook skeleton — one Opus builder + one independent Opus coach per stage, coach verifies by driving, one fix pass then stop, local path-limited commits, PREFLIGHT + fences verbatim as in this doc, broker isolation standing. Nothing pushed until my review (re-run suites, read the full diff, fences held, lane-wide broker grep). Owner acts stay three (spec word / gate tap / merge word) — no fourth act. Plain language throughout (phrase-book names). Effort high. If a stage blocks twice, stop and tell me.*

Owner's three acts (amendment 6): the **spec word** (this handoff, digested plain), the **gate tap**, the **merge word** — no PR review, no file edit, no fourth act. Fix loops run before the merge word and add zero acts.
