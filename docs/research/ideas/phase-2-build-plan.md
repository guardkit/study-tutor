# Phase 2 Build Plan — Gamification State + Dashboard + Submission Polish

## For: Weekend build (Saturday 2 – Sunday 3 May 2026) + weekday evenings 4–8 May + submission polish window 9–17 May
## Date: 30 April 2026 (Thursday — written one day ahead of `phase-2-scope.md`'s scheduled "Thursday 1 May" slot per hybrid cadence Rule 2; Phase 1's Thursday-evening Phase-2-planning slot moved up because three of four Phase 1 features had already landed by Wednesday and the fourth — FEAT-PH1-004 — was planned the same day; see `phase-1-build-plan.md §"Schedule recovery as of 2026-04-30"`).
## Date-label convention: the source docs (`phase-2-scope.md`, `phase-1-build-plan.md`) label 1 May as "Thursday" and slide each subsequent day one slot, treating 3-4 May as the weekend. Calendar-true: **30 April = Thursday, 1 May = Friday, 2-3 May = Saturday-Sunday, 18 May = Monday**. **This build plan uses calendar-true day labels throughout** so the day-by-day schedule maps cleanly onto real Saturdays and Sundays. Cross-references to source docs preserve the source's date strings (e.g. "Thursday 1 May" when quoting the scope) but my own scheduling uses calendar-true labels.
## Status: **Drafted from scope while Phase 1 close-out is still in flight.** FEAT-PH1-001 + FEAT-PH1-002 + FEAT-PH1-003 merged. **FEAT-PH1-004 (Primary-Text RAG + Quote Verifier) PLANNED today as `FEAT-70A4`** — 7 subtasks across 5 waves in `tasks/backlog/primary-text-rag-and-quote-verifier/`, BDD scenarios `@task:`-tagged for R2 oracle activation, smoke gates wired between waves, AC-quality linter clean. Build pending — Friday 1 May evening if a clean autobuild run lands; Saturday 2 May morning otherwise. **Reachy Mini "Scholar" delivery confirmed for Friday 8 May 2026** (Pollen Robotics dispatch text, received 30 April PM). This changes the Reachy posture from "uncertain hardware arrival" to "hardware arrives at the close of Phase 2 features track" — DEC-06 go/no-go gate moves from the speculative Sunday 3 May slot to **Saturday 9 May** (post-delivery unbox + SDK hello-world), and the **live Reachy demo segment moves from possible-fallback to likely outcome** (capture target Wednesday 13 May; future-vision segment becomes the late-stage fallback if integration is blocked). Phase-1 outcomes that feed this build plan are split into KNOWN (Graphiti latency spike done; SR-08 elevated to CRITICAL; three layers integrated; Reachy delivery confirmed) and **TBD (Coach calibration data, real turn p50/p95, end-to-end demo session, Reachy operational status post-unbox)** — TBD items are flagged inline below with explicit revisit triggers.
## Repo: `study-tutor` (Phase 1 codebase shipping — `src/study_tutor/{knowledge,planner,tutoring}/` populated).
## Machine: MacBook Pro M2 Max (primary), GB10 over Tailscale (Ollama + nomic-embed-text + bge-reranker-v2-m3), Synology NAS over Tailscale (FalkorDB), Google Gemini (Coach + Graphiti entity extraction).
## Target completion: End of Friday 8 May 2026 (close of Week 3). Submission polish through Saturday 16 May. **Hackathon submission deadline: Monday 18 May 23:59 UTC.**

---

## What Phase 2 IS

Week 3 of the 31-day build. Layers retention mechanics on top of the working three-layer tutor that Phase 1 ships: XP, levels, streaks, achievements, daily challenges, topic mastery via the gamification economy already published in `docs/gamification/design.md` (a Phase 0 deliverable, fixed since 17 April). Generates a static HTML dashboard via Claude Design for the demo video. Captures and edits the submission video. Polishes the public repo, the technical write-up, and the submission form. **The submission becomes a credible candidate during this phase — Phase 1 makes it work; Phase 2 makes it shippable.**

## What Phase 2 IS NOT

- Not a re-architecture (Phase 1's three-layer + Player-Coach + Graphiti story stays — Do-Not-Change in scope §)
- Not a new dependency (everything Phase 2 needs — Graphiti, Gemini, Ollama, Claude Design — is already wired)
- Not Reachy *integration* code work (gated to a separate stretch phase per DEC-06; integration runs as a parallel thread starting Saturday 9 May post-delivery, outside Phase 2's day-by-day plan). **Reachy *capture* for the demo video IS in Phase 2's polish-track schedule** (Wednesday 13 May target) because it's video production, not integration code — but the underlying SDK / Graphiti-to-speech build is the parallel thread.
- Not multi-student (Lilymay only — post-hackathon)
- Not multi-subject (post-hackathon)
- Not a React app, mobile app, or backend server (DEC-05; static HTML only)
- Not LLM-backed gamification rules (deterministic rules engine; no creative-rewards LLM)
- Not new state-engine feature work after the dashboard lands — Wednesday onward is polish, not build

## Success Criteria (reiterated from scope doc)

1. **Gamification state engine lands.** XP, level, streak, achievement logic working against the FEAT-PH1-001 Graphiti schema. A completed session produces the expected state change. → FEAT-PH2-001.
2. **Session-end response carries gamification events.** MCP `tutor_session_end` response includes `xp_awarded`, `level`, `level_up`, `achievements_unlocked`, `streak`. → FEAT-PH2-001.
3. **Dashboard renders real state.** `scripts/export_session.py` + Claude-Design-generated HTML produces a dashboard showing Lilymay's actual state. Capturable on video. → FEAT-PH2-002.
4. **Demo video complete.** 3–4 minute video covering five segments. Uploaded to hosting, URL accessible. → FEAT-PH2-003.
5. **Technical write-up finalised.** Real content in every section; architecture diagram present; 3000+ words. → Submission Polish track.
6. **Submission form complete.** Fields filled, materials attached, confirmation received. → Submission Polish track.
7. **Public repo gate-check passed.** Final sweep complete; nothing copyrighted committed; `.env.example` clean; parity surfaces still green. → Submission Polish track.
8. **Reachy outcome final.** Live Reachy segment (capture target Wednesday 13 May, contingent on Saturday-9-May go/no-go passing post-unbox) OR pre-recorded future-vision segment if integration is blocked late. → Demo video Session 4.
9. **Phase 2 validation gate run for Phase 1.** `phase-1-validation.md` produced early in Phase 2 reviewing what held / drifted / falsified. → Saturday 2 May morning.
10. **Lilymay can articulate what this tool does for her.** Informal success marker. → No deliverable; observed during demo capture.

---

## Prerequisites — to confirm before Saturday 2 May starts

These are gates Phase 1 must close before Phase 2 weekend kicks off. If any are red on Friday 1 May evening, the affected Saturday 2 May activity slips by the fix time rather than starting on broken foundations.

### Must be green by Friday 1 May evening (Phase 1 close-out)

- [ ] **FEAT-PH1-004 status decided** — either (a) shipped (FEAT-70A4 autobuild green; verifier integrated into Coach pipeline at `src/study_tutor/tutoring/orchestrator.py`) OR (b) deferred to Phase 2 with the 5-criterion Coach fallback documented in `phase-1-validation.md`. Phase 2 build plan accommodates BOTH outcomes — see "Branching for FEAT-PH1-004 outcome" below.
- [ ] **Lilymay seeded against Synology FalkorDB** — `python scripts/seed_student_model.py --student lilymay` ran clean; `get_student_state("lilymay")` returns the expected baseline (see Phase 1 G2). FEAT-PH2-001 cannot be exercised without seeded state.
- [ ] **End-to-end demo session via MCP run at least once** (Phase 1 G3) — `tutor_start_session` → 5–7× `tutor_turn` → `tutor_session_end` from Claude Desktop, with at least one Coach revision observed and a `session_completed` episode written to Graphiti. Without this, Phase 2 is building gamification rules against a session lifecycle that's never produced a real summary.
- [ ] **Six parity surfaces SR-01..SR-07 still green; SR-08 + SR-09 honoured.** No regression from Phase 1 work.
- [ ] **`phase-1-validation.md` seeded** — at least the four-paragraph outline (held / drifted / falsified / changes-current-phase). Saturday 2 May morning's first task finalises it; the seed has to exist Friday evening.

### Should be green; can absorb on Saturday morning if not

- [ ] Coach calibration pass run at least once — initial rubric weights/threshold revisited against real session signal. Materially affects FEAT-PH2-001 confidence-update integration; if not done, Saturday morning absorbs ~1h.
- [ ] `tutor_session_end` MCP response shape stable — Phase 2 augments it with gamification fields (per scope §FEAT-PH2-001 item 4), so the Phase 1 baseline must be settled before extension.

### Nice to have

- [ ] Tech writeup Phase 1 section drafted with real content (low priority; defer-into-Phase-2 acceptable per Phase 1 G5).
- [x] **Reachy hardware status known** — ✅ Scholar delivery confirmed for Friday 8 May 2026 (Pollen Robotics dispatch text 30 April PM). The DEC-06 go/no-go gate moves to Saturday 9 May (post-delivery, post-unbox); see "Day-by-day plan" Saturday 9 May entry. Reachy *integration* thread runs in parallel from Saturday 9 May → Tuesday 12 May, outside Phase 2's day-by-day. **Reachy thread runway is 10 days from delivery to submission** (8 May → 18 May) — feasible for the 30-second demo segment per the conversation starter doc, tight for anything more ambitious.

---

## Status as of 2026-04-30 (Thursday) — write-time snapshot

### What is known

| Input | Status | What this gives Phase 2 |
|---|---|---|
| **Graphiti latency** | ✅ MEASURED 2026-04-27 — `add_episode` median **78.98s**, `search_nodes` 0.07s ([graphiti-latency-spike-results.md](./graphiti-latency-spike-results.md)) | `GamificationState` writes MUST be async (SR-08 + ADR-ARCH-019). Cannot block session-end response on Graphiti write completion. Confirmed with overwhelming margin. |
| **Async write-back surface** | ✅ MERGED — `src/study_tutor/knowledge/async_write.py` exposes `GraphitiWriteHelper` with `write_misconception`, `write_session_episode`, `write_planner_topic_confidence`, `drain(timeout=GRAPHITI_DRAIN_WINDOW=5.0)` | FEAT-PH2-001's `write_gamification_state` extends this same helper — CC-13 single-call-site invariant preserved. No new dispatch surface. |
| **Session-completed episode shape** | ✅ MERGED — `SessionCompletedEpisode` (in `src/study_tutor/knowledge/episodes.py`) carries `session_id`, `student_id`, `subject_slug`, `text_name`, `topics_covered: list[str]`, `aos_exercised: list[str]`, `narrative_summary`, `started_at`, `ended_at` | FEAT-PH2-001 rules engine inputs are exactly these fields plus the per-turn Coach observations from the orchestrator's session log. No Phase 1 schema extension needed. |
| **DDR-003 ordering** | ✅ MERGED — `session.completed` event emit happens BEFORE `asyncio.create_task(write_session_episode)` on the same code path inside `tutor_session_end` | FEAT-PH2-001 inserts the gamification rules computation BETWEEN the emit and the F3 dispatch — rules are pure-functional (no I/O), so they don't push session-end response latency. |
| **Coach rubric six criteria including `quote_fidelity`** | ⏳ DEPENDS ON FEAT-PH1-004 (FEAT-70A4 planned today) | Branching note below: if FEAT-PH1-004 ships, the Coach evaluation produces six criterion scores; FEAT-PH2-001's confidence-update consumes the rubric output. If FEAT-PH1-004 defers, the Coach has 5 criteria with re-balanced weights and the same consumer pattern still works. |
| **Graphiti student model schema** | ✅ MERGED — `Student`, `Subject`, `Text`, `Topic`, `AssessmentObjective`, `Misconception`, `TopicConfidence` plus six relationship constants | FEAT-PH2-001 adds **one new entity** (`GamificationState`) and **one new relationship** (`Student HAS_GAMIFICATION_STATE GamificationState`). Achievement and Quest entities are co-located with `GamificationState` rather than as separate Graphiti entities (lower cost, tighter cohesion). |
| **Hybrid cadence Rule 3** | Phase-1-validation gate at Saturday 2 May morning, per cadence | Day 1 starts with the gate, not with code. ~30 min, captures held/drifted/falsified for the full Phase 1 set. |
| **Reachy Mini delivery date** | ✅ CONFIRMED — Friday 8 May 2026 per Pollen Robotics dispatch text (30 April PM) | Hardware arrival no longer uncertain. DEC-06 go/no-go moves to Saturday 9 May (post-unbox + SDK hello-world). Live Reachy segment elevates from possible-fallback to likely-outcome; capture target Wednesday 13 May. Future-vision segment becomes the late-stage fallback only if integration is blocked by Tuesday 12 May. |

### What is TBD (revisit triggers below)

| Open input | Why it matters | Revisit trigger |
|---|---|---|
| **FEAT-PH1-004 build outcome** | Determines whether Phase 1 ships a 6-criterion or 5-criterion Coach. Affects `quote_fidelity` consumer in FEAT-PH2-001 confidence-update logic. | Friday 1 May evening: check FEAT-70A4 autobuild status. If green, six criteria. If not, fall back to 5-criterion Coach + `phase-1-validation.md` records the deferral. |
| **Real turn p50 / p95 latency** | If turns are at 25s+ on average, the gamification rules computation cannot itself add latency — must stay sub-100ms (it's pure-functional, so this is achievable; just confirm). Also affects the Reachy "celebration" timing if Reachy is in play. | Saturday 2 May morning: check the latency log from the end-to-end demo session run during Phase 1 G3. If turns are within budget, no plan changes. If turns are at the 30s ceiling, FEAT-PH2-001 must keep its session-end addition strictly under 100ms. |
| **Coach signal quality** | Determines whether topic-confidence updates use the Coach's per-turn `criterion_scores` directly OR a smoothed aggregate. Affects FEAT-PH2-001 §6.2 confidence-update rule. | Saturday 2 May morning: read Tuesday's Coach observations + any tuning notes. If signal is clean (consistent scoring patterns, low rejection-loop count), use direct mapping. If noisy, smooth across the session's turns. |
| **Session-export JSON shape stability** | Phase 2 dashboard consumes this; if the shape moves during Phase 2, dashboard work re-runs. | Saturday 2 May late morning: codify the shape in `scripts/export_session.py` + write a frozen-shape contract test. From that moment on, the shape is fixed. |
| **Claude Design output quality** | First time the frontend-design skill is asked to produce submission-quality dashboard HTML. Quality determines whether one polish evening is enough or whether a hand-coded fallback template is needed. | Tuesday 5 May evening: first-pass run. If quality is acceptable after one polish iteration, FEAT-PH2-002 lands as planned. If not, Wednesday 6 May falls back to a hand-coded HTML template with data substitution from the same JSON. |
| **Reachy operational status post-unbox** | Hardware arrives Friday 8 May (confirmed). Operational status — onboard Pi 4 reachable on home WiFi, Python SDK responsive, Daemon up, basic head/eye animation works — is unknown until Saturday 9 May unbox. The DEC-06 go/no-go evaluates this. **Source-doc dating note:** DEC-06 names "4 May" as the gate, written when delivery was speculative. With confirmed delivery 8 May, the gate logically moves to **Saturday 9 May** (delivery-day-plus-one). | Saturday 9 May AM: dedicated unbox + go/no-go slot (~2-3h). Five criteria: hardware powers up + on home WiFi + MacBook reaches Daemon over LAN + Python SDK `pip install reachy_mini` + hello-world (head movement + speech) succeeds + minimal POC gamification → verbal-ack works. All five green → spin up Reachy *integration* thread as parallel work Sun 10 → Tue 12 May. Any red that can't be resolved Sat 9 May → fall back to future-vision segment captured Friday 15 May. |
| **Lilymay availability for capture** | Demo video Session 1 (working-today, lowest-risk) needs Lilymay on-screen. Other sessions are Rich-only. | Each capture session day: confirm Lilymay's availability. If not, Rich-only segments still produce a complete video; Lilymay segments slip to next available evening. |

### Branching for FEAT-PH1-004 outcome

The build plan accommodates both Friday-evening outcomes for `FEAT-70A4`:

**Path A (FEAT-PH1-004 ships):** Phase 2 starts with a 6-criterion Coach. FEAT-PH2-001 confidence-update logic consumes all six criteria including `quote_fidelity`. The dashboard's `topic_confidence` heat-map reflects per-AO scores from the Coach. Demo video architecture-reveal segment names the verifier explicitly as a differentiator.

**Path B (FEAT-PH1-004 defers):** Phase 2 starts with a 5-criterion Coach (rubric weights re-balanced to sum to 1.0 — the change documented in `phase-1-validation.md`). FEAT-PH2-001 confidence-update logic consumes five criteria; behaviour is unchanged from Path A's perspective at the gamification engine boundary. The dashboard renders identically. Demo video architecture-reveal segment frames the verifier as Phase 3 / post-hackathon work; the source-typed quote-verifier story moves from a built differentiator to a designed-and-deferred differentiator. Less compelling, but credible.

**Rich's discretion at the Friday-evening checkpoint.** Both paths are clean.

---

## Feature Summary

| # | Feature | Depends On | Complexity | Days | Status |
|---|---------|------------|------------|------|---------|
| VALIDATION | Phase 1 validation gate | Phase 1 closed Fri 1 May | 1/10 (document) | Sat 2 May AM | ⏳ Not started — outline seeded Fri |
| FEAT-PH2-001 | Gamification state engine + session-lifecycle integration | FEAT-PH1-001 (schema), FEAT-PH1-003 (session-end pipeline), FEAT-PH1-004 outcome (Path A or B) | 6/10 | Sat 2 – Mon 4 May | ⏳ Scope only; spec + plan + build during Phase 2 |
| FEAT-PH2-002 | Static HTML dashboard via Claude Design + session-export script | FEAT-PH2-001 (`GamificationState` written) | 4/10 | Tue 5 – Wed 6 May | ⏳ Scope only |
| FEAT-PH2-003 | Demo video production (script + capture + edit + upload) | FEAT-PH2-001 + FEAT-PH2-002 + Phase 1 stable | 5/10 | Thu 7 – Sat 16 May (capture spans days) | ⏳ Scope only |
| POLISH-WRITEUP | Technical write-up finalisation (3000+ words, architecture diagram, evidence) | Each FEAT as it lands | 3/10 | Continuous Sat 9 May → Fri 15 May | ⏳ Phase 1 sections drafted; Phase 2 sections written as features land |
| POLISH-REPO | Public repo gate-check (README, LICENSE, `.env.example`, parity surfaces, no copyrighted commits) | All features merged | 1/10 | Fri 15 – Sat 16 May | ⏳ Final sweep |
| POLISH-SUBMIT | Submission form + video upload + URL test | Demo video uploaded | 1/10 | Sat 16 May | ⏳ Final sweep |

**Dependency chain:**

```
[Phase 1 close-out + FEAT-PH1-004 outcome] ──► VALIDATION (Sat AM)
                                                    │
                                                    ▼
                                              FEAT-PH2-001 (Sat PM → Mon eve)
                                                    │
                                                    ▼
                                              FEAT-PH2-002 (Tue eve → Wed eve)
                                                    │
                                                    ▼
                                              FEAT-PH2-003 captures (Thu eve onward)
                                                    │
                                                    ▼
                                              POLISH-* (Sat 9 → Sat 16 May)
                                                    │
                                                    ▼
                                              Submission deadline Mon 18 May 23:59 UTC
```

FEAT-PH2-001 and FEAT-PH2-002 are sequential because the dashboard consumes `GamificationState` writes. FEAT-PH2-003 captures span Phase 2 — Session 1 (working-today) can run on Day 1 because Phase 1 is what's being captured; Sessions 2–4 require progressively more Phase 2 features in place.

Reachy stretch work — if the Saturday-9-May go/no-go passes — runs as a **parallel thread outside Phase 2's day-by-day plan**, between delivery (Fri 8 May) and the live capture session (Wed 13 May). Its only Phase 2 artefacts are a 30-second segment in the demo video and a ~300-word section in the technical writeup.

---

## Day-by-Day Plan

The plan is structured in two tracks. The **feature track** runs Saturday 2 May → Friday 8 May (close of Week 3). The **submission polish track** runs Saturday 9 May → Saturday 16 May, with the submission deadline on Monday 18 May 23:59 UTC (Sunday 17 May is buffer-only). Submission polish steals at most one evening per weekday during the feature track for tech-writeup content as features land — content first, polish later.

### Saturday 2 May (Phase 2 Day 1, full day, ~6h) — Validation gate + FEAT-PH2-001 spec & plan + capture working-today

This is the day the Phase 1→Phase 2 boundary is crossed. Per hybrid cadence Rule 3, the morning is the validation gate; per scope §FEAT-PH2-003 the lowest-risk capture (working-today with Lilymay) lands today because Phase 1 is what's being captured and Phase 2 hasn't introduced any risk yet.

#### Morning (~3h) — Phase-1 validation gate + Phase 2 system-level re-grounding

1. **Run Phase 1 validation gate** (~30 min). Open `phase-1-validation.md` (seeded Friday). Mark each Phase 1 success criterion (1–14) green/yellow/red against shipped reality. Mark each `phase-1-scope.md §Do-Not-Change` item as held/drifted/falsified. Close out the four headings (held / drifted / falsified / changes-current-phase). Commit. **Output:** finalised `phase-1-validation.md`.

2. **Update architecture and design for Phase 2 scope** (~1h):

   ```bash
   /system-arch \
     --from docs/research/ideas/phase-2-scope.md \
     --context docs/research/ideas/phase-2-build-plan.md \
     --context docs/research/ideas/phase-1-validation.md \
     --context docs/architecture/ARCHITECTURE.md \
     --context docs/research/ideas/decisions-log-2026-04-17.md \
     --context docs/gamification/design.md

   /system-design \
     --from docs/architecture/ARCHITECTURE.md \
     --context docs/research/ideas/phase-2-scope.md \
     --context docs/research/ideas/phase-2-build-plan.md \
     --context docs/gamification/design.md \
     --context src/study_tutor/knowledge/student_model.py \
     --context src/study_tutor/knowledge/episodes.py \
     --context src/study_tutor/knowledge/async_write.py

   /system-plan \
     --from docs/design/DESIGN.md \
     --context docs/architecture/ARCHITECTURE.md \
     --context docs/research/ideas/phase-2-scope.md \
     --context docs/research/ideas/phase-2-build-plan.md
   ```

   Expected output: ARCHITECTURE.md and DESIGN.md updated to add the gamification subsystem (one new entity, one new relationship, one new write-helper method, one event-stream sink). No invariants change. CC-13 (single-call-site write helper) and CC-14 (runtime LLM param assertion) still apply.

3. **Spec + plan FEAT-PH2-001** (~1.5h):

   ```bash
   /feature-spec "Gamification State Engine — XP/level/streak/achievement rules, GamificationState entity, session-lifecycle integration, event-stream sink" \
     --context docs/research/ideas/phase-2-scope.md \
     --context docs/research/ideas/phase-2-build-plan.md \
     --context docs/gamification/design.md \
     --context src/study_tutor/knowledge/student_model.py \
     --context src/study_tutor/knowledge/episodes.py \
     --context src/study_tutor/knowledge/async_write.py \
     --context src/study_tutor/tutoring/session_end.py \
     --context src/study_tutor/tutoring/orchestrator.py

   /feature-plan "Gamification State Engine" \
     --context features/gamification-state-engine/gamification-state-engine_summary.md
   ```

   Expected output: 5–6 subtasks across 3–4 waves (per the FEAT-PH1-001/002/003 cadence — 5 to 7 subtasks each). Anticipated subtask shapes:

   - **TASK-PH2-G-001 — `GamificationState` Pydantic entity + relationship constant** (declarative, complexity 2, wave 1) — co-located with existing `student_model.py`; reuses the seven-entity / six-relationship pattern. Adds one entity, one relationship name (`HAS_GAMIFICATION_STATE`), and a Pydantic episode type for `gamification_state_updated`.
   - **TASK-PH2-G-002 — Pure-functional rules module** (feature, complexity 5, wave 2) — `src/study_tutor/gamification/rules.py`: `apply_session_xp(state, session_summary)`, `apply_streak(state, session_summary)`, `apply_level_progression(state, xp_delta)`, `apply_achievement_check(state, session_summary, level_up)`, `apply_topic_confidence(state, coach_observations)`. All functions are pure: `(state, input) → (new_state, list[Event])`. Zero I/O. Tested without network. Achievement / quest / level data is loaded once at module init from `docs/gamification/design.md`-derived constants in `src/study_tutor/gamification/economy.py`.
   - **TASK-PH2-G-003 — State engine module + GraphitiWriteHelper extension** (feature, complexity 4, wave 3) — `src/study_tutor/gamification/state.py`: thin wrapper that loads current `GamificationState` from Graphiti via `queries.get_gamification_state(student_id)` (new query helper), invokes the rules pipeline, and dispatches the new state via `helper.write_gamification_state(student_id, new_state)`. The new helper method extends `src/study_tutor/knowledge/async_write.py` — CC-13 single-call-site invariant honoured. Fire-and-forget per ADR-ARCH-019.
   - **TASK-PH2-G-004 — Session-lifecycle integration** (feature, complexity 4, wave 3) — extends `src/study_tutor/tutoring/session_end.py` (existing FEAT-PH1-003 module): after the DDR-003-ordered emit and before the F3 `create_task(write_session_episode)`, the rules pipeline runs (pure-functional, sub-100ms), the new state is computed, gamification fields are added to the `tutor_session_end` MCP response (`xp_awarded`, `level`, `level_up`, `achievements_unlocked`, `streak`), and the new state is dispatched via the helper as a parallel `create_task`. Existing CC-13 / DDR-002 / DDR-003 invariants unchanged.
   - **TASK-PH2-G-005 — Event-stream sink** (feature, complexity 3, wave 4) — `src/study_tutor/gamification/event_stream.py`: writes one JSON line per gamification event to `~/.study_tutor/events.jsonl`. This is the data Reachy reads (if go-no-go passes) and that the dashboard consumes. Append-only, no schema migration concerns at this scale.
   - **TASK-PH2-G-006 — Integration smoke + per-criterion test fixtures** (testing, complexity 3, wave 5) — end-to-end test: a synthetic `SessionCompletedEpisode` with three turns of Coach observations runs through the rules engine, produces the expected XP delta, streak advance, achievement unlock, confidence delta, and event-stream entries. Also verifies the session-end MCP response shape matches scope §2.

   The actual `/feature-plan` output may differ — these are anticipated shapes for budgeting. Both `bdd-linker` and AC-quality linter run as part of `/feature-plan` Step 11 and 10.5; expected zero blockers given the design's deterministic shape.

#### Afternoon (~2h) — FEAT-PH2-001 Wave 1 + capture working-today

4. **Run Wave 1 of FEAT-PH2-001 (`TASK-PH2-G-001`)** (~30 min). Pydantic models are foundation. Direct mode (complexity 2). Verify with import + a Pydantic round-trip test.

5. **Capture working-today video segment with Lilymay** (~1h). 30s of video is the Session 1 deliverable per scope §FEAT-PH2-003. Lilymay opens Open WebUI, asks a Macbeth question, the tutor responds with verbatim Shakespeare + AO labelling + Socratic close — the real session, captured as evidence of "this is what works today before any Phase 2 layering." Lowest-risk capture because it doesn't depend on any Phase 2 code. **If Lilymay isn't available today, this slips to Sunday or any subsequent day — Session 1 can land anytime in Phase 2.**

6. **Run /feature-build for FEAT-PH2-001 Wave 2** (~30 min, can run in background while capture runs). `TASK-PH2-G-002` rules module — pure functions, no I/O, fastest task to autobuild because the test surface is simple.

#### Evening (~1h) — Commit + Reachy delivery-week prep

7. **Reachy delivery-week prep** (~30 min). Delivery is confirmed for Friday 8 May (six days away). Quick check: has the Reachy Mini Quick Start guide been read? Is the Pollen Robotics SDK README (`pollen-robotics/reachy_mini`, branch `develop`) downloaded for offline reference? Is `reachy-integration-conversation-starter.md` open in a separate Claude Desktop window so the integration thread can spin up Saturday 9 May with full context loaded? Skip if all three are already true.

8. **Commit Saturday work.** `chore: phase-2 day 1 — validation gate + arch refresh + FEAT-PH2-001 wave 1`.

**End-of-Saturday state:**
- Phase 1 validation gate run; `phase-1-validation.md` finalised
- Architecture + design refreshed for Phase 2; no invariant drift detected
- FEAT-PH2-001 spec + plan landed; subtask structure in `tasks/backlog/gamification-state-engine/`
- FEAT-PH2-001 Wave 1 (Pydantic models) done; Wave 2 (rules module) running or done
- 30 seconds of submission video footage captured

---

### Sunday 3 May (Phase 2 Day 2, ~3h) — FEAT-PH2-001 build-out

The original day plan reserved a 2h Reachy go/no-go slot here; with delivery confirmed for Friday 8 May the gate moves to Saturday 9 May, leaving Sunday lighter than originally planned. The freed time becomes recovery slack — useful given Saturday 2 May is a heavy 6h day. If Saturday's spec/plan slipped at all, Sunday's freed slot absorbs it.

#### Morning (~2h) — FEAT-PH2-001 Waves 3 + 4

1. **Run /feature-build for FEAT-PH2-001 Wave 3** (~1h). `TASK-PH2-G-003` (state engine + helper extension) and `TASK-PH2-G-004` (session-lifecycle integration). These are the load-bearing wave: the helper extension preserves CC-13; the lifecycle integration preserves DDR-002 + DDR-003. Conductor parallelism if Wave 3 has two independent tasks (state engine module independent of session-end wiring before TASK-PH2-G-004 lands).

2. **Run /feature-build for FEAT-PH2-001 Wave 4** (~30 min). `TASK-PH2-G-005` (event stream). Append-only file writer; smallest task in the feature.

3. **Smoke test the full session-lifecycle path against seeded Lilymay state** (~30 min). Run a real `tutor_session_end` from Claude Desktop. Verify:
   - MCP response carries gamification fields (`xp_awarded`, `level`, etc.)
   - `~/.study_tutor/events.jsonl` shows the expected events
   - `GamificationState` written to Graphiti (via `get_student_state("lilymay")`)
   - Session-end response time still under budget (no new latency from rules computation)

#### Afternoon (~1h) — FEAT-PH2-001 Wave 5 + tech-writeup gamification section

4. **Run /feature-build for FEAT-PH2-001 Wave 5** (~30 min). `TASK-PH2-G-006` integration smoke. Closes the feature. Smoke gate runs `pytest -m "feat_ph2_001 and smoke" -x --no-cov`. Marker registration MUST use underscores (lesson from TASK-DSP-009 — hyphens parse as Python subtraction in pytest's `-m` expression).

5. **Draft tech-writeup gamification section** (~30 min). Open `docs/submission/technical-writeup.md`. Add the gamification economy paragraph (referencing `docs/gamification/design.md`), the state-engine architecture paragraph (deterministic rules + async write-back), and one paragraph on why the design is rule-based not LLM-backed. Content first, edit later.

#### Evening (~0-1h optional) — Reachy thread pre-reading

6. **Optional: re-read `reachy-integration-conversation-starter.md`** (~30 min). Hardware arrives Friday 8 May; integration thread starts Saturday 9 May. A re-read now means Saturday's unbox starts with full context loaded. Skip if Sunday energy is low.

**End-of-Sunday state:**
- FEAT-PH2-001 fully landed and integrated; smoke gate green
- Tech writeup gamification section drafted
- Reachy integration context refreshed (optional)

---

### Monday 4 May (evening, ~2h) — FEAT-PH2-001 verification + observation

This day is built for slack. If FEAT-PH2-001 didn't fully land Sunday, Monday absorbs the overflow. If it did, Monday is observation.

1. **Run a full multi-session sequence** (~1h). Three sessions in a row from Claude Desktop:
   - Session A: regular session, observe XP delta and streak advance
   - Session B: session triggering an achievement (e.g. `Three Day Run` if streak hits 3)
   - Session C: session triggering a confidence-band crossing (developing → secure on a topic)

   Verify each session's MCP response carries the right gamification fields and that the event stream + Graphiti state both reflect the changes.

2. **Calibrate any rule that's misfiring** (~30 min). If XP values feel off, adjust constants in `src/study_tutor/gamification/economy.py` (these are derived from `docs/gamification/design.md` so any change requires updating both — or noting that the shipped values diverge). Achievement criteria sometimes need clarification when first observed in real data; expected adjustments are minimal because the economy is fixed in the design doc.

3. **Document Phase 2 state in `phase-1-validation.md`** (~30 min). Update the doc to record Phase 2 progress so far — held/drifted/falsified for the Phase 2 success criteria 1–2.

**End-of-Monday state:** FEAT-PH2-001 verified across multiple sessions. Any rule-tuning landed. Tech writeup updated.

---

### Tuesday 5 May (evening, ~2h) — FEAT-PH2-002 spec + first dashboard pass

1. **Spec + plan FEAT-PH2-002** (~1h):

   ```bash
   /feature-spec "Static HTML Dashboard via Claude Design — session-export script + frontend-design HTML generation + offline-capturable single-file output" \
     --context docs/research/ideas/phase-2-scope.md \
     --context docs/research/ideas/phase-2-build-plan.md \
     --context docs/gamification/design.md \
     --context src/study_tutor/gamification/state.py \
     --context src/study_tutor/knowledge/queries.py

   /feature-plan "Static HTML Dashboard" \
     --context features/static-html-dashboard/static-html-dashboard_summary.md
   ```

   Expected output: 3–4 subtasks. Anticipated:

   - **TASK-PH2-D-001 — Session-export JSON contract + script** (feature, complexity 3, wave 1) — `scripts/export_session.py` reads current Graphiti state for a student via the existing `queries.py` helpers + the new `get_gamification_state`, emits the dashboard-ready JSON shape from scope §FEAT-PH2-002 §1. Frozen-shape contract test added in the same task.
   - **TASK-PH2-D-002 — Claude Design first-pass HTML generation** (manual via skill, complexity 4, wave 2) — invoke the `frontend-design` skill against the session-export JSON with the aesthetic brief from scope §FEAT-PH2-002 §2 ("warm academic — Obsidian meets Duolingo but GCSE-appropriate"). Save output to `output/dashboard.html`. **This is the unknown-quality step.** Budget one evening.
   - **TASK-PH2-D-003 — Dashboard rendering script + iteration loop** (feature, complexity 3, wave 3) — `scripts/render_dashboard.py` reads the JSON, runs the generation step (or applies cached templates with data substitution if the generated HTML is stable across runs), writes the output file. Includes a `--dry-run` mode for capturing JSON-only.
   - **TASK-PH2-D-004 — Dashboard polish + capture-readiness check** (feature, complexity 2, wave 4) — second-pass Claude Design refinement based on what the first pass produced; verify the output is single-file (no external dependencies), works offline, video-capturable. **If the second pass is not capture-ready, fall back to a hand-coded HTML template with data substitution from the same JSON.** Time-boxed to 1.5h.

2. **First dashboard pass via Claude Design** (~1h). Run TASK-PH2-D-002 manually in this session. **This is where the Claude Design quality bar is established.** Expected outcomes:

   - **Acceptable first-pass**: minor polish needed Wednesday. Continue with TASK-PH2-D-003.
   - **Marginal first-pass**: Claude Design produces structurally-correct HTML but the aesthetic is off. One iteration with a refined brief Wednesday. If still marginal after iteration, fall back.
   - **Unacceptable first-pass**: hand-coded fallback. ~1.5h additional work to write a Jinja-template HTML rendering against the same JSON. Less differentiating but submission-ready.

3. **Document the dashboard outcome in `phase-1-validation.md`** (~10 min). One sentence: which path ran (Claude Design / Claude Design + iteration / hand-coded fallback).

**End-of-Tuesday state:** Dashboard first pass exists. Quality bar known.

---

### Wednesday 6 May (evening, ~2h) — Dashboard polish + capture architecture-reveal

1. **Dashboard second pass / fallback** (~1h). Per the Tuesday outcome:
   - If Claude Design pass acceptable: TASK-PH2-D-004 polish iteration.
   - If marginal: refined brief + second generation; if still marginal at end of this hour, switch to fallback.
   - If unacceptable Tuesday: hand-coded fallback now.

2. **Verify dashboard renders Lilymay's actual state** (~15 min). `python scripts/export_session.py --student lilymay > /tmp/lilymay-export.json && python scripts/render_dashboard.py --input /tmp/lilymay-export.json --output output/dashboard.html && open output/dashboard.html`. Confirm: level title + progress bar, streak counter, recent XP, active quest (if any), near-unlocks, topic mastery grid all rendering with correct data.

3. **Capture demo video Session 2: architecture reveal** (~45 min). Screen recording of:
   - Open WebUI session (carrying over from Session 1)
   - Cut to terminal: `tutor_start_session` shown via Claude Desktop tool invocation
   - Brief tour of the three layers — Player-Coach loop, planner querying Graphiti, Coach evaluation surfacing
   - 60 seconds total. Requires Phase 1 features working reliably, which they are by this point.

**End-of-Wednesday state:** Dashboard capture-ready. 90 seconds of video footage in the can.

---

### Thursday 7 May (evening, ~2h) — Demo video first cut + FEAT-PH2-003 spec

1. **Spec + plan FEAT-PH2-003** (~30 min):

   ```bash
   /feature-spec "Demo Video Production — script finalisation, capture plan, recording sessions, edit pass, upload" \
     --context docs/research/ideas/phase-2-scope.md \
     --context docs/research/ideas/phase-2-build-plan.md \
     --context docs/submission/demo-script.md

   /feature-plan "Demo Video Production" \
     --context features/demo-video-production/demo-video-production_summary.md
   ```

   This is more checklist than software feature. Expected output: a structured `tasks/backlog/demo-video-production/` folder with task IDs for each capture session, edit pass milestones, and upload steps. The "build" is video editing, not code.

2. **Finalise `docs/submission/demo-script.md`** (~30 min). Expand from the Phase 0 stub to a shot-by-shot script:
   - 0:00–0:30 — Working today (Lilymay using Open WebUI, captured Sat 2 May)
   - 0:30–1:30 — Architecture reveal (Player-Coach loop + Graphiti, captured Wed 6 May)
   - 1:30–2:30 — Gamification + dashboard walkthrough (captured Friday 8 May)
   - 2:30–3:00 — Reachy segment (live, captured Wednesday 13 May, contingent on Saturday-9-May go/no-go passing post-unbox; pre-recorded future-vision fallback captured Friday 15 May only if go/no-go failed or integration was blocked by Tuesday 12 May)
   - 3:00–3:30 — Vision and roadmap

3. **Edit first cut combining Sessions 1 + 2** (~1h). 90 seconds of rough video assembled — working-today + architecture reveal. Establishes the editing tool / workflow. Music, captions, transitions can be deferred until the full cut.

**End-of-Thursday state:** First 90 seconds of the video roughly assembled. Demo script v1 in the repo. Capture plan locked.

---

### Friday 8 May (evening, ~2h) — Capture gamification + dashboard + Phase 2 close-out

This is the close of Week 3 and the close of Phase 2's feature track. From Saturday 9 May, the work is polish.

1. **Capture demo video Session 3: gamification walkthrough + dashboard** (~1h). Screen recording:
   - Run a session that triggers an achievement (or use a pre-staged scenario — the engine is deterministic, so a specific session-summary input produces a known event sequence)
   - Show the level-up / achievement-unlock / streak-milestone moment
   - Cut to the rendered dashboard showing the post-session state
   - 60 seconds total. Requires FEAT-PH2-001 + FEAT-PH2-002 both shipping, which they do by this point.

2. **Phase 2 success criteria check** (~30 min). Run criteria 1–7 + 9 against shipped reality:
   - [ ] Gamification state engine lands ✓ FEAT-PH2-001 merged
   - [ ] Session-end response carries gamification events ✓ FEAT-PH2-001 TASK-PH2-G-004 verified
   - [ ] Dashboard renders real state ✓ FEAT-PH2-002 captured
   - [ ] Demo video complete — IN PROGRESS (Sessions 1, 2, 3 captured; Reachy capture Wed 13 May, final cut + edit + upload over polish track)
   - [ ] Technical write-up finalised — DRAFT IN PROGRESS
   - [ ] Submission form complete — NOT STARTED (Sat 16 May)
   - [ ] Public repo gate-check passed — NOT STARTED (Fri 15 – Sat 16 May)
   - [ ] Reachy outcome final — go/no-go DECIDED Sat 9 May (post-delivery); capture target Wed 13 May
   - [ ] Phase 2 validation gate — N/A (no Phase 3); fold into post-hackathon retrospective
   - [ ] Lilymay can articulate what this tool does — INFORMAL OBSERVATION

3. **Tag the repo** (~5 min). `git tag phase-2-features-complete`. Submission polish track from here on.

4. **Write `phase-2-validation.md` outline** (~25 min). Same four-paragraph shape as `phase-1-validation.md` but a smaller doc — Phase 2 is smaller in scope and has no successor phase. The doc folds into the post-hackathon retrospective rather than feeding a Phase 3.

**End-of-Friday state:** All FEATs complete. Three of four video segments captured. Submission polish window opens.

---

## Submission Polish Track — Saturday 9 May → Saturday 16 May

This is the back-half of the 31-day burn. No new Phase 2 feature work. Everything from here is shipping the artefacts. **The Reachy stretch thread runs in parallel across this track** — integration code lives outside Phase 2's day-by-day per DEC-06, but key Reachy milestones (delivery, unbox + go/no-go, capture session) are scheduled here because they touch demo-video production.

### Saturday 9 May (~4h) — **Reachy delivery-day-plus-one: unbox + DEC-06 go/no-go + tech writeup full pass**

Reachy Mini "Scholar" delivered Friday 8 May. Saturday is the first proper integration day. The morning opens the box and runs the gate; the afternoon is tech writeup work (no dependency on Reachy). If unbox blocks for some reason, the whole afternoon absorbs into Reachy debug; tech writeup slips to Sunday.

#### Morning (~2-3h) — Reachy unbox + DEC-06 go/no-go gate

1. **Unbox + power-on + onto home WiFi** (~30 min). Plug in, follow the Reachy Mini Quick Start, get Scholar onto the home WiFi. Confirm the onboard Pi 4 is reachable from MacBook on the LAN. (Per `reachy-integration-conversation-starter.md`, Tailscale is likely not needed inside the house — local network is enough.)

2. **SDK install + hello-world** (~45 min). On MacBook, `pip install reachy_mini` per Pollen Robotics' SDK README (https://github.com/pollen-robotics/reachy_mini, branch `develop`). Run a minimal head-movement + speech script — the SDK's documented "hello world" pattern. Confirm Daemon-on-Pi receives the command and Scholar responds.

3. **Tailscale path verification** (~15 min). If Lilymay's bedroom (where Scholar will live for the demo) is on a different WiFi segment than the MacBook, confirm the path works. (Likely OK — most homes have one WiFi network.) Otherwise document the workaround.

4. **POC: gamification event → Reachy verbal-ack** (~45 min). Pull a stub `GamificationState` from Graphiti (or use a hand-built fixture if the Phase 2 gamification engine isn't seeded yet). Generate a simple speech response — *"Lilymay's at Level 6, with an 8-day streak"* — and pipe to Scholar's TTS. Confirm Scholar speaks the line. **This is the load-bearing POC for the demo segment.**

5. **DEC-06 go/no-go evaluation** (~15 min). Five criteria (per the TBD table above):
   - [ ] Hardware powered up
   - [ ] Scholar on home WiFi, MacBook reaches Daemon over LAN
   - [ ] Python SDK installs cleanly + hello-world (head + speech) succeeds
   - [ ] Tailscale or local-network path confirmed for the demo capture location
   - [ ] POC: gamification event → verbal-ack works

   **All five green → GO**. Spin up the Reachy *integration* thread as parallel work Sun 10 → Tue 12 May. Per DEC-06, this thread sits outside Phase 2's day-by-day plan; it has its own conversation starter (`reachy-integration-conversation-starter.md`) which scopes the actual integration build (Graphiti queries → script selection → TTS → SDK calls).

   **Any red that can't be resolved Saturday → NO-GO**. Fall back to future-vision segment captured Friday 15 May. Phase 2 absorbs no further Reachy work.

   **Outcome recorded** in `reachy-go-no-go-2026-05-09.md` (one paragraph + the criteria checklist).

#### Afternoon (~2h) — Tech writeup full pass

6. **Tech writeup first full draft** (~2h). All sections fleshed out from existing notes. Target 3000+ words. Sections per scope §"Submission Polish Track":
   - Pipeline methodology with evidence (agentic-dataset-factory run metrics, fine-tune loss curves)
   - Architecture diagram (Mermaid or PNG via Claude Design)
   - Gamification design (cross-reference `docs/gamification/design.md`)
   - On-device vs Bedrock deployment with cost evidence
   - Evaluation section (what we measured / didn't measure)
   - Copyright and provenance (cross-reference `copyright-training-data-analysis.md`)
   - **Reachy companion section** (new — ~300 words, refs `reachy-integration-conversation-starter.md` and `docs/gamification/design.md §9`)

**End-of-Saturday state:**
- Reachy unboxed + go/no-go decided + outcome recorded
- If GO: integration thread spun up; tech writeup includes a Reachy section
- Tech writeup first full draft exists

### Sunday 10 May (~2h) — Tech writeup polish + architecture diagram

1. **Tech writeup second pass** (~1h). Polish prose, fix references, verify cross-links, ensure the differentiator story is named explicitly (three-layer + Player-Coach + source-typed verifier — Path A — or three-layer + Player-Coach + designed-and-deferred-verifier — Path B).

2. **Architecture diagram** (~1h). Generate via Claude Design (frontend-design skill or static-image generation) or Mermaid. Embed in tech writeup. Should show:
   - The three layers (fine-tune / RAG / student model)
   - The Player-Coach loop
   - The MCP boundary
   - The Graphiti async write surface
   - The gamification engine + dashboard

### Monday 11 May (evening, ~1h) — Buffer / overflow + Reachy integration thread (parallel)

This is buffer time. If anything from the polish track is behind, this evening absorbs it. If everything's on track, this evening is for any spec/plan TBD-resolution work — e.g. the `phase-2-validation.md` content if not done Friday.

**Parallel: Reachy integration thread (if go-no-go passed Saturday).** Per DEC-06, the integration runs as a separate work item against `reachy-integration-conversation-starter.md`, not as part of Phase 2's day-by-day. By end of Monday the target is: Graphiti `get_gamification_state(student_id)` query → script-selection logic (parent-query / near-unlocks / celebration scenarios from `docs/gamification/design.md §9.1`) → TTS string → Reachy SDK call. Aim for a working "How's Lilymay's revision going?" round-trip by Tuesday evening.

### Tuesday 12 May (evening, ~1h) — Demo video edit pass second cut + Reachy integration polish (parallel)

Combine all captured segments into a single 3–4 minute video. Add captions, music if any, transitions. Tool-of-Rich's-choice — not the place to learn video editing.

**Parallel: Reachy integration polish.** Refine the round-trip from Monday: cleaner head/eye animation timing, multiple scenario scripts, error-fallback when Graphiti is slow. **Capture-readiness checkpoint Tuesday evening:** if the integration is solid enough to capture Wednesday, proceed. If brittle, push capture to Thursday and use Friday as the future-vision fallback day.

### Wednesday 13 May (~2-3h) — **Reachy capture (live segment) + demo video polish**

This is the day the live Reachy demo segment gets captured, contingent on Saturday's go/no-go passing and Tuesday's integration capture-readiness checkpoint.

#### Capture session (~1.5h)

1. **Set up the scene** (~30 min). Lilymay's bedroom or a neutral home setting. Scholar on a flat surface within arm's reach. MacBook running the integration code. Camera framing: Scholar in centre, slight angle to capture head movement; lighting consistent.

2. **Run the parent-query scenario** (~30 min). Rich asks *"How's Lilymay's revision going?"* on-camera. Scholar responds — verbatim level title + streak + recent XP + one near-unlockable achievement. Multiple takes; pick the cleanest. Per `docs/gamification/design.md §9.1` and `GCSE_Gamification_Research.md §3`.

3. **Optional: Lilymay-interaction take** (~30 min if available). Lilymay asks Scholar *"What achievements am I close to?"* — Scholar identifies 2-3 nearest unlockable achievements and suggests a targeted session. Bonus footage; not load-bearing for the 30-second segment.

#### Demo video polish (~1h)

4. **Polish edit pass** (~1h). Trim, balance audio, finalise captions, export at 1080p or 4K, name appropriately. Now the full 3-4 minute video has all five segments roughly in place.

**End-of-Wednesday state:** Reachy live segment captured; demo video close to final cut. Friday's future-vision-fallback slot is now redundant (unless capture quality was unacceptable).

### Thursday 14 May (evening, ~1h) — Buffer + tech writeup final read + post-hackathon-wishlist

Final read of the technical writeup; fix typos; verify all links; ensure compliance gate-check items are mentioned (`copyright-training-data-analysis.md` cross-reference, AQA exclusion etc.). Buffer for any last-minute capture re-take if Wednesday was rough. Write `post-hackathon-wishlist.md` per scope §"Phase 2 as the last phase".

### Friday 15 May (evening, ~1h) — Reachy backup capture / future-vision fallback + repo gate-check

1. **Reachy outcome decision point**:
   - **If Wednesday's Reachy capture was good**: skip the Reachy work today; proceed straight to repo gate-check.
   - **If Wednesday's capture was marginal**: re-shoot today using the integration improvements from Thursday (if any).
   - **If Saturday's go-no-go failed OR integration was blocked by Tuesday**: capture the future-vision segment now. 30 seconds — `reachy-integration-conversation-starter.md` doc on screen + static mock-up + Rich narrating the future vision. This is the documented DEC-06 fallback.

2. **Public repo gate-check** (per scope §"Public repo gate-check"):
   - [ ] README stands on its own as a submission narrative
   - [ ] LICENSE clear
   - [ ] `.env.example` clean (SR-06 re-verified)
   - [ ] No copyrighted content committed: `find . -name '*.pdf' | grep -v venv | head` is empty (no PDFs in `domains/*/sources/`); `find . -name '*.gguf'` is empty
   - [ ] Six parity surfaces SR-01..SR-07 still green; SR-08 + SR-09 honoured; CC-13 single-call-site invariant audited
   - [ ] Fresh-MacBook walkthrough repeated (or tested on a different user account) — README copy-paste produces a working MCP-accessible tutor

### Saturday 16 May (~2h) — Final submission preparations

1. **Demo video upload** (~30 min). YouTube unlisted (or hackathon-platform-preferred host). Test URL from a private browser window. Confirm playback at full quality.

2. **Submission form completion** (~1h). All required fields filled. Materials uploaded or linked. Confirmation email received from the platform.

3. **Final repo tag** (~10 min). `git tag submission-2026-05-18`. Push to origin.

4. **Final read of submission package** (~20 min). Spot-check that the submission's external-facing artefacts (README, video, writeup, demo URL) all tell a consistent story.

### Sunday 17 May (buffer, no new work scheduled)

Buffer for anything that broke at the last minute. Recommended posture: do nothing scheduled; only address blockers.

### Monday 18 May (~1h max) — Submission deadline 23:59 UTC

Final upload only if 17 May absorbed something blocking. Otherwise the submission is already in by Saturday's end.

---

## GuardKit Command Sequence

Phase 2 follows the same GuardKit pattern as Phases 0 and 1 — system-level commands once at the start of the phase, then per-feature spec-and-plan-and-build.

### Saturday 2 May morning sequence

```bash
# After phase-1-validation.md is finalised:

/system-arch \
  --from docs/research/ideas/phase-2-scope.md \
  --context docs/research/ideas/phase-2-build-plan.md \
  --context docs/research/ideas/phase-1-validation.md \
  --context docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/decisions-log-2026-04-17.md \
  --context docs/gamification/design.md

/system-design \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-2-scope.md \
  --context docs/research/ideas/phase-2-build-plan.md \
  --context docs/gamification/design.md \
  --context src/study_tutor/knowledge/student_model.py \
  --context src/study_tutor/knowledge/episodes.py \
  --context src/study_tutor/knowledge/async_write.py

/system-plan \
  --from docs/design/DESIGN.md \
  --context docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-2-scope.md \
  --context docs/research/ideas/phase-2-build-plan.md
```

### Per-feature sequence

```bash
# FEAT-PH2-001 — Saturday 2 May late morning
/feature-spec "Gamification State Engine — XP/level/streak/achievement rules, GamificationState entity, session-lifecycle integration, event-stream sink" \
  --context docs/research/ideas/phase-2-scope.md \
  --context docs/research/ideas/phase-2-build-plan.md \
  --context docs/gamification/design.md \
  --context src/study_tutor/knowledge/student_model.py \
  --context src/study_tutor/knowledge/episodes.py \
  --context src/study_tutor/knowledge/async_write.py \
  --context src/study_tutor/tutoring/session_end.py \
  --context src/study_tutor/tutoring/orchestrator.py

/feature-plan "Gamification State Engine" \
  --context features/gamification-state-engine/gamification-state-engine_summary.md

# Then either /feature-build FEAT-PH2-XXXX (autonomous) for low-risk waves
# or /task-work TASK-PH2-G-NNN (interactive) for the lifecycle-integration task

# FEAT-PH2-002 — Tuesday 5 May
/feature-spec "Static HTML Dashboard via Claude Design — session-export script + frontend-design HTML generation + offline-capturable single-file output" \
  --context docs/research/ideas/phase-2-scope.md \
  --context docs/research/ideas/phase-2-build-plan.md \
  --context docs/gamification/design.md \
  --context src/study_tutor/gamification/state.py \
  --context src/study_tutor/knowledge/queries.py

/feature-plan "Static HTML Dashboard" \
  --context features/static-html-dashboard/static-html-dashboard_summary.md

# FEAT-PH2-003 — Thursday 7 May
/feature-spec "Demo Video Production — script finalisation, capture plan, recording sessions, edit pass, upload" \
  --context docs/research/ideas/phase-2-scope.md \
  --context docs/research/ideas/phase-2-build-plan.md \
  --context docs/submission/demo-script.md

/feature-plan "Demo Video Production" \
  --context features/demo-video-production/demo-video-production_summary.md
```

**Autobuild recommended** for FEAT-PH2-001 Waves 1 + 2 + 5 (declarative + pure functions + integration smoke — well-specified, low-risk surfaces). **Reviewer-in-loop recommended** for FEAT-PH2-001 Waves 3 + 4 (helper extension + lifecycle integration — the load-bearing CC-13 / DDR-002 / DDR-003 conformance surface). FEAT-PH2-002 is mostly manual (Claude Design generation step is not automatable). FEAT-PH2-003 is checklist work, not autobuild.

---

## Files That Will Change

### New files in study-tutor

| File | Feature | Change type |
|------|---------|-------------|
| `src/study_tutor/gamification/__init__.py` | FEAT-PH2-001 | NEW |
| `src/study_tutor/gamification/economy.py` | FEAT-PH2-001 | NEW (XP / level / achievement / quest constants from `docs/gamification/design.md`) |
| `src/study_tutor/gamification/rules.py` | FEAT-PH2-001 | NEW (pure-functional rules pipeline) |
| `src/study_tutor/gamification/state.py` | FEAT-PH2-001 | NEW (state engine module — load + dispatch) |
| `src/study_tutor/gamification/event_stream.py` | FEAT-PH2-001 | NEW (`~/.study_tutor/events.jsonl` writer) |
| `tests/unit/gamification/test_rules.py` | FEAT-PH2-001 | NEW (per-rule unit tests) |
| `tests/unit/gamification/test_state.py` | FEAT-PH2-001 | NEW |
| `tests/unit/gamification/test_event_stream.py` | FEAT-PH2-001 | NEW |
| `tests/integration/test_gamification_lifecycle.py` | FEAT-PH2-001 | NEW (end-to-end: synthetic session-summary → state delta + events) |
| `tests/smoke/test_gamification_session_end.py` | FEAT-PH2-001 | NEW (asserts MCP `tutor_session_end` response shape) |
| `scripts/export_session.py` | FEAT-PH2-002 | NEW |
| `scripts/render_dashboard.py` | FEAT-PH2-002 | NEW |
| `output/dashboard.html` | FEAT-PH2-002 | NEW (generated artefact; gitignored) |
| `tests/contract/test_session_export_shape.py` | FEAT-PH2-002 | NEW (frozen-shape contract test) |
| `docs/submission/capture-plan.md` | FEAT-PH2-003 | NEW |
| `docs/research/ideas/phase-1-validation.md` | VALIDATION | NEW (finalised Sat 2 May AM from Friday seed) |
| `docs/research/ideas/phase-2-validation.md` | VALIDATION | NEW (close-out, Fri 8 May or Sun 17 May) |
| `docs/research/ideas/post-hackathon-wishlist.md` | Phase 2 close-out | NEW (per scope §"Phase 2 as the last phase") |
| `docs/research/ideas/reachy-go-no-go-2026-05-09.md` | DEC-06 outcome | NEW (one paragraph + 5-criteria checklist, written Saturday 9 May post-unbox) |

### Modified files

| File | Change |
|------|--------|
| `src/study_tutor/knowledge/student_model.py` | Add `GamificationState` Pydantic entity + `HAS_GAMIFICATION_STATE` relationship constant |
| `src/study_tutor/knowledge/episodes.py` | Add `GamificationStateUpdatedEpisode` (or extend `EpisodeKind` Literal) |
| `src/study_tutor/knowledge/async_write.py` | Add `write_gamification_state(student_id, state)` method on `GraphitiWriteHelper` (CC-13 single-call-site invariant preserved) |
| `src/study_tutor/knowledge/queries.py` | Add `get_gamification_state(student_id)` query helper |
| `src/study_tutor/tutoring/session_end.py` | Insert rules-engine call between DDR-003 emit and F3 `create_task`; extend MCP response with gamification fields |
| `src/study_tutor/mcp/adapter.py` | `_end_tutor_session` returns extended response shape including `xp_awarded`, `level`, `level_up`, `achievements_unlocked`, `streak` |
| `pyproject.toml` | Register `feat_ph2_001`, `feat_ph2_002`, `feat_ph2_003`, `feat_ph2_001 and smoke` markers (underscores per TASK-DSP-009 lesson) |
| `docs/architecture/ARCHITECTURE.md` | Updated by `/system-arch` for Phase 2 (new gamification subsystem) |
| `docs/design/DESIGN.md` | Updated by `/system-design` for Phase 2 |
| `docs/submission/technical-writeup.md` | Phase 2 sections drafted Sun 3 May; full pass Sat 9 May; polish Sun 10 May |
| `docs/submission/demo-script.md` | Expanded from Phase 0 stub to shot-by-shot script Thu 7 May |
| `README.md` | Submission narrative pass Fri 15 May |
| `.env.example` | Re-verified Fri 15 May; no new env vars expected |
| `.gitignore` | Add `output/dashboard.html`, `~/.study_tutor/events.jsonl` (the latter is outside the repo anyway) |

### No changes expected

- `src/study_tutor/knowledge/{corpus_models,corpus,retrieval,quote_verifier,coach_handover}.py` — Phase 1 FEAT-PH1-004 work; Phase 2 doesn't touch the verifier
- `src/study_tutor/tutoring/coach/*` — Phase 1 FEAT-PH1-003 work; no rubric changes in Phase 2
- `src/study_tutor/planner/*` — Phase 1 FEAT-PH1-002 work; planner is rule-1/3/4 only in Phase 2 (rules 2 + 5 still stubs per scope `# TODO(phase-2)` — explicitly NOT promoted to active in Phase 2 of the hackathon, despite the comment label, because gamification quest tracking lands in FEAT-PH2-001 instead and does not require planner changes)
- Modelfile / Ollama configs — Phase 0/1 work; no inference changes in Phase 2
- Reachy code — separate stretch phase, not Phase 2

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| FEAT-PH1-004 doesn't ship Friday 1 May | Medium | Medium | Path B (5-criterion Coach + deferred verifier) is documented; Phase 2 build plan is unchanged in shape, only the demo narrative shifts |
| Saturday 2 May validation gate surfaces a Phase 1 regression | Low | Medium | Saturday morning reserves 3h; if a fix takes more, FEAT-PH2-001 spec slips to evening; Sunday morning still has 2h for Wave 1 + 2 |
| Claude Design first pass produces unacceptable HTML | Medium | Medium | Tuesday-evening fall-through to Wednesday; if Wednesday also marginal, Wednesday afternoon switches to hand-coded fallback (~1.5h work). Dashboard is video content, not a product surface — slight aesthetic compromise is acceptable |
| Reachy unbox blocks on Saturday 9 May (hardware DOA, network issue, SDK install fails) | Low | Low | Future-vision segment plan is the documented fallback; capture Friday 15 May. Demo loses the "live embodied" beat but keeps the conversation starter showing intent |
| Reachy integration learning curve eats more than 3-4 days (Sun 10 → Wed 13 May) | Medium | Medium | Tuesday-evening capture-readiness checkpoint; if integration is brittle, push capture to Thursday and use Friday as the future-vision fallback day; if still blocked Friday, future-vision fallback ships |
| Reachy delivery slips past Friday 8 May despite confirmation | Low | Medium | Future-vision fallback is the same as the integration-blocked path — capture Friday 15 May. The 10-day runway absorbs a 1-2 day slip; longer than that, the live segment is off the table for this submission |
| Lilymay unavailable on Saturday 2 May for Session 1 capture | Low | Low | Session 1 (working-today) is the lowest-risk capture; can land any day in Phase 2 — Sunday, Monday evening, etc. |
| Latency budget breached by gamification rules computation | Very Low | High | Rules are pure-functional and target sub-100ms; if profiling shows slower, the offending rule is moved to async-after-emit (loses session-end response visibility but preserves turn budget) |
| `GamificationState` Graphiti write fails silently | Low | Medium | CC-13 / ADR-ARCH-019 — failure emits structured-log line; in-memory state is the source of truth for the MCP response so the user sees no failure; reconciliation on next session start (Phase 1 pattern) |
| Tech writeup runs over time / under-quality | Medium | Medium | Saturday 9 May is the dedicated full-pass slot; Sunday 10 May polish; budget reservation is 5h total, plenty for a 3000-word submission writeup |
| Submission form has surprise field requirements | Low | High | Sunday 17 May is buffer; Mon 18 May only needed if absolute last-minute |
| Coach calibration falsifies a Phase 2 design assumption | Low | Medium | Monday 4 May observation pass catches this before FEAT-PH2-002 starts; if signal is unusably noisy, smoothed-aggregate confidence-update fallback (already noted in TBD section) |

---

## Review Gates

The cadence rule (Rule 3) puts a validation gate at each phase boundary. Within a phase, GuardKit's quality gates apply per-task. Phase 2 has three explicit human review gates:

### Gate 1 — Phase 1 validation gate (Saturday 2 May AM)

Per hybrid cadence Rule 3. Output: finalised `phase-1-validation.md`. Pass criterion: every Phase 1 success criterion + every `phase-1-scope.md §Do-Not-Change` item marked held / drifted / falsified, with concrete consequence noted for any drift or falsification.

### Gate 2 — FEAT-PH2-001 lifecycle integration review (Sunday 3 May AM)

Wave 3 + Wave 4 of FEAT-PH2-001 are the load-bearing structural-conformance work. Coach-approved CC-13 / DDR-002 / DDR-003 audit before merge. Reviewer-in-loop, not autobuild. Pass criterion: greppable test confirms a single `add_episode` call site (CC-13); unit test confirms the bus emit happens before the F3 `create_task` (DDR-003); helper-protocol seam test confirms the Coach AsyncSubAgent owns its own writes (DDR-002 unchanged from Phase 1).

### Gate 3 — Phase 2 success criteria check (Friday 8 May evening)

Output: `phase-2-validation.md` outline + tag `phase-2-features-complete`. Pass criterion: criteria 1–3 + 9 green; criteria 4–7 + 8 in flight (polish track is from Saturday 9 May onwards, so green status by Friday is not expected); criterion 10 informal — check Lilymay can describe the tutor in one sentence.

### Mid-phase informal checkpoints

- **Sunday 3 May evening** — FEAT-PH2-001 smoke gate green; multi-session demo run successful
- **Tuesday 5 May evening** — Claude Design quality bar known; fall-through-to-fallback decision made
- **Thursday 7 May evening** — 90 seconds of video footage in the can; demo script v1 finalised

---

## Outcomes feeding the post-hackathon retrospective

Per scope §"Phase 2 as the last phase", there is no Phase 3 in the hackathon-target plan. Some evening in the polish track (likely Thursday 14 May during the buffer slot) sees a `post-hackathon-wishlist.md` written, capturing what would be Phase 3 *if* the project continued. Inputs:

- **LES2 round** — second lessons-learned doc, written post-submission, folds Study Tutor lessons into the six parity surfaces checklist plus any new parity surfaces discovered. Template per `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`.
- **`/template-create` cut of `langchain-deepagents-tutor`** — post-hackathon, from the working study-tutor repo. Per `state-of-the-project-and-phase-recommendation.md` Appendix A.8.
- **Multi-subject expansion** — Maths content, fine-tune re-run, ChromaDB per-subject collections, role-differentiated Coach rubrics if subjects diverge pedagogically.
- **Flutter mobile app** — primary interface long-term; not achievable in 31 days.
- **Reachy as primary interface** — subject of the stretch-phase conversation starter; post-hackathon if not achieved pre-submission.
- **Bedrock cost monitoring** — if Bedrock sees real usage post-hackathon, budget alerts and per-session cost attribution needed.

---

## TBD markers consolidated

For ease of revisiting, all TBD items are listed here with their revisit triggers. Each one should be revisited at the named moment and either resolved or escalated.

| TBD | Revisit trigger | Default if unresolved |
|-----|-----------------|------------------------|
| FEAT-PH1-004 build outcome | Friday 1 May evening | Path B (5-criterion Coach); document deferral |
| Real turn p50/p95 latency | Saturday 2 May AM (after Phase 1 demo session log) | Assume budget OK; rules computation strictly < 100ms |
| Coach signal quality | Saturday 2 May AM | Direct mapping (per-criterion) confidence-update; fallback to smoothed if observed-noisy on Sun 3 May |
| Session-export JSON shape | Saturday 2 May late AM | Codify scope §FEAT-PH2-002 §1 shape; frozen-shape contract test in TASK-PH2-D-001 |
| Claude Design output quality | Tuesday 5 May evening | Acceptable → polish Wed; marginal → iterate Wed; unacceptable → hand-coded fallback Wed afternoon |
| Reachy operational status post-unbox | Saturday 9 May AM (DEC-06 gate, post-delivery — delivery confirmed Friday 8 May) | Future-vision segment captured Friday 15 May |
| Reachy integration capture-readiness | Tuesday 12 May evening (capture-readiness checkpoint) | If integration brittle → push capture Wed→Thu; if still blocked Friday → future-vision fallback |
| Lilymay availability for capture sessions | Each capture session day | Slip to next available evening; Session 1 first because lowest-risk |
| Tech writeup quality bar | Sunday 10 May polish | If under-quality, Monday 11 May buffer absorbs second polish pass |

---

## Schedule summary

All day labels are calendar-true for May 2026.

| Day | Date | Hours | Primary work |
|-----|------|-------|--------------|
| Thu | 30 Apr | (today) | This build plan written |
| Fri | 1 May | (Phase 1) | Phase 1 close-out: FEAT-PH1-004 build outcome + `phase-1-validation.md` seed |
| Sat | 2 May | 6 | **Phase 2 Day 1** — Validation gate + system-level refresh + FEAT-PH2-001 spec/plan/Wave 1 + capture Session 1 |
| Sun | 3 May | 3 | **Phase 2 Day 2** — FEAT-PH2-001 Waves 3 + 4 + 5 + tech writeup gamification section. _Reduced from 5h: the original Reachy go/no-go slot moved to Sat 9 May after delivery confirmation._ |
| Mon | 4 May | 2 | FEAT-PH2-001 verification + multi-session run + tuning |
| Tue | 5 May | 2 | FEAT-PH2-002 spec/plan + first Claude Design pass |
| Wed | 6 May | 2 | Dashboard polish or fallback + capture Session 2 (architecture reveal) |
| Thu | 7 May | 2 | FEAT-PH2-003 spec + demo script finalisation + first edit pass |
| **Fri** | **8 May** | **2** | **Capture Session 3 + Phase 2 success criteria check + `phase-2-features-complete` tag.** _Reachy Mini delivery during the day — receive + cursory power-on only; full unbox + setup deferred to Saturday so the Phase 2 close-out doesn't compete._ |
| **Phase 2 features complete** |       |       | **End of Friday 8 May** |
| **Sat** | **9 May** | **4** | **Reachy unbox + DEC-06 go/no-go (AM, ~2-3h)** + tech writeup full draft (PM, ~2h). _Increased from 3h: Reachy unbox now lives here per delivery confirmation._ |
| Sun | 10 May | 2 | Tech writeup polish + architecture diagram. _Reachy integration thread starts as parallel work (outside this row)._ |
| Mon | 11 May | 1 | Buffer / overflow. _Parallel: Reachy integration round-trip target — "How's Lilymay's revision going?" working end-to-end._ |
| Tue | 12 May | 1 | Demo video edit pass second cut. _Parallel: Reachy integration polish + capture-readiness checkpoint._ |
| **Wed** | **13 May** | **2-3** | **Reachy live capture (~1.5h) + demo video polish (~1h).** _Live segment is captured today contingent on Sat-9-May go/no-go pass + Tue-12-May capture-readiness check._ |
| Thu | 14 May | 1 | Buffer + tech writeup final read + `post-hackathon-wishlist.md`. _Reachy capture re-take if Wednesday was marginal._ |
| Fri | 15 May | 1 | Future-vision fallback **only if needed** (Sat 9 go/no-go failed or Wed capture unusable) + repo gate-check |
| Sat | 16 May | 2 | Demo upload + submission form + `submission-2026-05-18` tag + final read |
| Sun | 17 May | <1 | Buffer day — only act on blockers |
| Mon | 18 May | <1 | Submission deadline 23:59 UTC — no work scheduled if everything green |
| **TOTAL** |  | **~33h** | Across 18 days (Phase 2 day-by-day). **Reachy integration thread runs in parallel Sat 9 → Tue 12 May, ~6-8h additional, outside this table per DEC-06.** |

---

*Phase 2 build plan: 30 April 2026 (drafted one day ahead of `phase-2-scope.md`'s "Thursday 1 May" slot per hybrid cadence Rule 2; calendar-true 1 May is Friday — see Date-label convention at the top of this document).*
*Revised: 30 April 2026 (PM) — Reachy Mini "Scholar" delivery confirmed for Friday 8 May per Pollen Robotics dispatch text. DEC-06 go/no-go gate moved from speculative Sunday 3 May slot to Saturday 9 May (post-delivery unbox). Live Reachy demo segment elevated from possible-fallback to likely outcome; capture target Wednesday 13 May. Sunday 3 May reduced from 5h to 3h; Saturday 9 May increased from 3h to 4h.*
*Consuming: `phase-2-scope.md`, `phase-1-build-plan.md` outcomes (where landed), `graphiti-latency-spike-results.md`, `docs/gamification/design.md`, `decisions-log-2026-04-17.md`, `planning-cadence-hybrid-approach.md`, `reachy-integration-conversation-starter.md`.*
*Scheduled to be revised on Saturday 2 May morning if the Phase 1 validation gate surfaces drift not anticipated here, and on Saturday 9 May AM if the Reachy unbox surfaces operational issues that change the integration runway.*
*Target: hackathon-submission-complete by end of Saturday 16 May 2026. Submission deadline Monday 18 May 23:59 UTC.*
