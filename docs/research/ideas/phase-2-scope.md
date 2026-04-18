# Phase 2 Scope — Gamification State + Dashboard + Submission Polish

## For: Claude Code `/system-arch` → `/system-design` → `/system-plan` → `/feature-spec` → `/feature-plan` → AutoBuild
## Date: 17 April 2026
## Status: **SCOPE ONLY — build plan deferred to Thursday 1 May per hybrid cadence**
## Predecessor: `phase-1-scope.md`, `phase-1-build-plan.md` (Phase 1 completes Friday 2 May)
## Successor: no further phase planned; Reachy stretch is scoped separately at `reachy-integration-conversation-starter.md`
## Context: Week 3 of the 31-day burn. Takes the working three-layer tutor from Phase 1 and layers retention mechanics (XP, levels, achievements, streaks) on top, generates a submission-quality dashboard via Claude Design for the demo video, and produces the final submission artefacts (demo video, technical write-up, public repo polish).

---

## Build-plan deferral rationale

Per `planning-cadence-hybrid-approach.md` Rule 2, the Phase 2 build plan is written Thursday 1 May — during Phase 1's execution, once the Phase 1 Saturday latency spike and Coach tuning outcomes are known. Key Phase-1 outcomes the Phase 2 build plan needs as inputs:

- **Graphiti latency measurements.** Determines whether gamification state engine reads Graphiti live per user turn or polls with a cached snapshot. Affects day-by-day build time for FEAT-PH2-001.
- **Coach evaluation signal quality.** Determines whether gamification triggers attach to Coach output (topic mastery, AO coverage) or to simpler session metrics. Affects complexity of FEAT-PH2-002.
- **Session-export JSON shape.** Phase 1 defines this; Phase 2 dashboard consumes it; Phase 2 build plan depends on the shape being fixed.
- **Claude Design output quality (first real test).** Won't be known until Phase 2 Sunday at earliest. But the Phase 2 build plan can allocate time for iteration based on Phase 1's observed quality bar.

Writing the scope now, building the plan Thursday keeps the scope stable while protecting the build plan from being speculative. This is a direct application of the lesson documented in LES1 §8.

---

## Motivation

Phase 1 produces a tutor that adapts to Lilymay's progress across sessions — the three-layer architecture is real, the Coach enforces quality, the student model persists. What Phase 1 does not do is make the experience *sticky*. Without gamification, the tutor is a slightly better chatbot that a teenager will abandon after the novelty fades — exactly the failure mode documented in `GCSE_Gamification_Research.md` ("the disengagement cliff").

Phase 2's primary job is applying the gamification design from `docs/gamification/design.md` (written in Phase 0 FEAT-PO-001) as executable rules that turn session outcomes into XP, level progressions, achievements, streaks, and daily challenge completion. This is what makes the submission's "engagement" dimension credible to judges — visible retention mechanics, not just claimed ones.

Phase 2's secondary job is producing submission-quality artefacts: dashboard, demo video, polished technical write-up, public repo gate-check. The 18 May submission deadline is 16 days after Phase 2 starts; substantial working time is polish rather than code.

Phase 2 explicitly does NOT include Reachy work. If the 4 May go/no-go passes (per DEC-06), Reachy runs as a parallel stretch phase on a separate thread. If the go/no-go fails, Phase 2 absorbs the pre-recorded future-vision segment as demo content.

---

## Scope: Three Features + Submission Polish Track

The hybrid approach surfaces an important asymmetry in Phase 2 that didn't apply to Phases 0 and 1: the feature work (gamification + dashboard) and the submission-polish work (video, write-up, repo) run in parallel across the 10–12 day budget. Features need critical-path scheduling; polish needs buffer time. The scope below reflects both tracks.

### FEAT-PH2-001: Gamification State Engine

**Problem.** `docs/gamification/design.md` (Phase 0 deliverable) specifies XP values, level titles, achievement names, unlock gates, and confidence thresholds. None of this is wired into the tutor. Phase 1's `session_completed` Graphiti episodes carry the raw data; Phase 2 consumes that data and emits gamification events.

**Changes required.**

#### 1. Deterministic rules engine

The gamification logic is rule-based, not LLM-driven (consistent with the session planner choice in Phase 1). Rules are written in Python, testable without network, deterministic given the same session summary input. LLM-backed "creative rewards" are explicitly out of scope for the hackathon.

**Rule categories:**
- **XP award rules.** Session completion (+100 XP base + per-topic bonus + streak modifier), daily challenge completion (+50 XP), Boss Battle (+1000 XP), etc. All values from `docs/gamification/design.md`.
- **Streak rules.** Increment on consecutive-day completion; reset on miss; award milestone achievements (3-day, 7-day, 14-day, 30-day).
- **Level progression rules.** XP thresholds per level (15 named levels); unlock gates (daily challenges at L2, exam questions at L6, Boss Battle at L8, Teaching Mode at L10). Gates are checked at level-up; unlocks are flagged in the gamification state.
- **Achievement rules.** 6 categories, each with 3–5 named achievements. Per-achievement unlock criteria (streak count, topic mastery threshold, session variety, etc.).
- **Topic confidence adjustment rules.** Consume Coach evaluation scores from session turns; adjust `TopicConfidence.percentage` per topic using a simple weighted-average algorithm. Crossing a band boundary (struggling → developing → secure → mastered) emits a state-change event.

#### 2. State engine module

`src/study_tutor/gamification/state.py` and `src/study_tutor/gamification/rules.py`. State module holds the student's current gamification state (XP, level, streak, achievements, unlocked features). Rules module is pure functions from (state, session_summary) → (new_state, events_emitted).

Rules module has zero dependencies on the tutor core — pure data transformation. Tested independently with no network.

#### 3. State persistence

State persists to Graphiti as a dedicated entity type: `GamificationState` (student_id, current_xp, current_level, current_streak, unlocked_features, last_session_at). Written asynchronously per SR-08 after each session completion.

`GamificationState` is distinct from existing `Student` entity to keep gamification-free tutoring possible (important for content-strategy story: the tutor works without gamification; gamification is opt-in personalisation).

#### 4. Integration with session lifecycle

Phase 1's `_end_tutor_session` MCP handler is extended: after writing the `session_completed` episode, call the gamification engine with the session summary, receive the new state + events, write the new `GamificationState` and any achievement unlock events asynchronously.

Events surface back to the MCP caller as part of the session-end response:
```
{"session_id": "...", "summary": "...", "xp_awarded": 220, "level": "Apprentice", "level_up": false,
 "achievements_unlocked": ["First Week Warrior"], "streak": 7}
```

#### 5. Event feed for downstream consumers

Gamification events (level_up, achievement_unlocked, streak_milestone) are logged to a local JSONL event stream at `~/.study_tutor/events.jsonl`. This is the data Reachy reads (if the stretch phase runs) and the dashboard consumes.

**Dependencies:** Phase 0 `docs/gamification/design.md` (economy spec), Phase 1 FEAT-PH1-001 (Graphiti student model), Phase 1 FEAT-PH1-003 (`session_completed` episodes as input).

---

### FEAT-PH2-002: Static HTML Dashboard via Claude Design

**Problem.** The gamification state exists as data (Graphiti + event stream) but isn't visible. The demo video needs a visual artefact showing streak, level, recent XP, active quest, near-unlockable achievements — the standard gamification dashboard shape from `GCSE_Gamification_Research.md §4`.

Per DEC-05, this is secondary demo content, generated via Claude Design (frontend-design skill), static HTML rendered from a session-export JSON. Not an interactive product; a video-ready artefact.

**Changes required.**

#### 1. Session-export JSON schema (actually a Phase 1 deliverable)

The session-export is the contract between Phase 1 (producer) and Phase 2 (consumer). Phase 1 must commit to a stable shape by end of Phase 1; Phase 2 consumes it without further shape negotiation.

**Expected shape:**
```json
{
  "student": {"name": "Lilymay", "level": 5, "level_title": "Scholar", "current_xp": 2340, "xp_to_next_level": 660, "streak": 9, "target_grade": 7},
  "recent_sessions": [{"date": "...", "topic": "Macbeth witches", "duration_min": 18, "xp": 120, "aos": ["AO1", "AO2"]}, ...],
  "topic_confidence": [{"topic": "Macbeth", "band": "developing", "percentage": 62}, {"topic": "Power & Conflict Poetry", "band": "secure", "percentage": 78}, ...],
  "active_quest": {"name": "Fortnight Force", "progress": "9/14 days", "reward_xp": 500},
  "near_unlocks": [{"achievement": "Quote Champion", "criterion": "analyse 10 quotations", "progress": "7/10"}, ...],
  "recent_achievements": [{"name": "First Week Warrior", "unlocked": "..."}, ...]
}
```

Phase 1 Thursday build-plan work codifies this shape. Phase 2 takes it as given.

#### 2. Dashboard generation via Claude Design

Invoke the frontend-design skill with:
- Session-export JSON as data input
- Target audience: "Year 10 GCSE student, engaging but not childish"
- Aesthetic brief: "warm academic — think Obsidian meets Duolingo but GCSE-appropriate"
- Output: single-file HTML with embedded CSS (no external dependencies, works offline, video-capturable)
- Specific elements required: level progress bar with named title, streak counter with fire icon, recent XP timeline, active quest card, near-unlockable achievements grid, topic confidence heat-map or bar chart

Generate, review, iterate. Budget one evening for first pass, one for polish.

#### 3. Dashboard served statically

`scripts/render_dashboard.py` reads a session-export JSON, runs Claude Design generation (or uses a cached template with data substitution if the generated HTML is stable enough), writes `output/dashboard.html` + any asset files. Opens in a browser for video capture.

No web server, no React, no live-binding. Demo-only.

#### 4. Session-export generation

`scripts/export_session.py` reads current Graphiti state for the student, produces a session-export JSON per the schema. This is also the script Reachy would use (if the stretch phase runs) to read gamification state.

**Dependencies:** Phase 1's `session_completed` episode shape, FEAT-PH2-001 (`GamificationState` entity).

---

### FEAT-PH2-003: Demo Video Production

**Problem.** The hackathon submission includes a demo video. Good demo videos require planning, scripting, capture, editing. Rough footage captured during builds is not submission-quality; it needs a dedicated production pass.

The target is a 3–4 minute video demonstrating the submission's differentiators:
- 30s — working today (Open WebUI session with Lilymay using the tutor)
- 60s — architecture reveal (MCP invocation showing the three layers, Player-Coach loop, Graphiti student model)
- 60s — gamification walkthrough (dashboard view, level-up moment, achievement unlock, streak visualisation)
- 30s — Reachy segment (live interaction if go/no-go passed; pre-recorded future-vision otherwise)
- 30s — vision and roadmap

**Changes required.**

#### 1. Script finalised

`docs/submission/demo-script.md` (Phase 0 stub) expanded to a shot-by-shot script. Rich as narrator; Lilymay on-screen for the working-today segment; Rich demoing the architecture reveal and dashboard segments.

#### 2. Capture plan

`docs/submission/capture-plan.md` — new doc. For each segment: location, equipment, timing, what needs to be working. Captures "working today" first (lowest-risk footage); captures architecture and dashboard last (after Phase 2 features land).

#### 3. Recording sessions

- Session 1 (early in Phase 2): working-today capture with Lilymay. Lowest-risk; if it goes well, that's 30 seconds in the can.
- Session 2 (mid Phase 2): architecture reveal. Screen recording of MCP invocation + terminal + Claude Desktop. Requires Phase 1 features working reliably.
- Session 3 (late Phase 2): gamification and dashboard. Requires FEAT-PH2-001 and FEAT-PH2-002 landed.
- Session 4 (final weekend): Reachy if applicable; vision segment; audio corrections.

#### 4. Edit pass

Combining, trimming, captions, music (if any). Target: 3–4 minutes final runtime. Produced in whatever tool Rich is already familiar with — this is not the place to learn video editing under deadline pressure.

#### 5. Upload and submission form

Video hosted on YouTube unlisted or similar; URL submitted via the hackathon form. Test the URL works from a private browser window before submission.

**Dependencies:** Phase 1 fully working, FEAT-PH2-001 and FEAT-PH2-002 landed, `docs/submission/demo-script.md` (Phase 0 stub).

---

### Submission Polish Track (parallel to FEATs)

These are not discrete features but continuous work across Phase 2. Each lands incrementally as Phase 2 progresses.

#### Technical write-up finalisation

`docs/submission/technical-writeup.md` gets its final pass. Real content in every section. Specifically:
- Pipeline methodology with evidence (agentic-dataset-factory run metrics, fine-tune loss curves if available)
- Architecture diagram — mermaid or embedded PNG produced via Claude Design
- Gamification design with references to `docs/gamification/design.md`
- On-device vs Bedrock deployment with cost evidence from Phase 0 validation
- Evaluation section — what we measured, what we didn't
- Copyright and provenance — full accounting referencing `copyright-training-data-analysis.md`

Target: 3000–5000 words. Polished prose, not bullet lists.

#### Public repo gate-check

Final sweep for submission-readiness:
- README stands on its own as a submission narrative
- LICENSE clear
- `.env.example` clean (SR-06 re-verified)
- No copyrighted content accidentally committed (`find . -name '*.pdf'` and `find . -name '*.gguf'` both empty)
- All six parity surfaces SR-01 through SR-07 still green
- Fresh MacBook walkthrough repeated one more time (or at least tested on a different user account)

#### Submission form completion

Kaggle or hackathon platform submission form. Fields filled, materials uploaded, confirmation received.

---

## Do-Not-Change

These decisions are closed for Phase 2. Reopenable only per `decisions-log-2026-04-17.md §Revision policy`.

- **The seven structural requirements SR-01 through SR-08 remain load-bearing.** Phase 2 code does not regress them. SR-08 async Graphiti write-back applies to gamification state writes as well.
- **Gamification rules are deterministic.** No LLM-backed creative rewards. Probabilistic variety in achievement suggestions (if implemented) uses weighted random sampling over deterministic candidate sets, not an LLM.
- **Dashboard is static HTML, generated once per capture.** No React, no live-bind, no backend server. This is DEC-05.
- **Session state persistence is Graphiti-only for Phase 2.** If demo needs in-memory state across an MCP server restart, that's a Phase 1 backport, not a Phase 2 feature.
- **Reachy is a separate stretch phase.** Phase 2 does not block on or assume Reachy work.
- **Single student remains Lilymay.** Multi-student is post-hackathon.
- **Bedrock remains validated but not mandatory for demo.** If GB10 is free, demo runs against GB10 Ollama. If not, Bedrock. No last-minute switching during capture.
- **No new dependencies in Phase 2.** Everything Phase 2 needs — Graphiti, Gemini, Ollama, Claude Design frontend-design skill — is already in place from Phases 0 and 1.
- **Three-layer architecture story stays.** Even if Phase 1 outcomes produce stronger differentiators elsewhere, the core submission narrative is three-layer + Player-Coach + gamification. Don't rewrite the narrative this late.

---

## Success Criteria

Phase 2 is complete when all of the following are true:

1. **Gamification state engine lands.** XP, level, streak, achievement logic working. A completed session produces the expected state change (XP increment, streak advance, maybe level-up or achievement unlock), verified against `docs/gamification/design.md`.

2. **Session-end response carries gamification events.** MCP `tutor_session_end` response includes xp_awarded, level, level_up flag, achievements_unlocked, streak.

3. **Dashboard renders real state.** `scripts/export_session.py` + Claude-Design-generated HTML produces a dashboard showing Lilymay's actual current state. Capturable on video.

4. **Demo video complete.** 3–4 minute video covering five segments per the scope. Uploaded to hosting, URL accessible.

5. **Technical write-up finalised.** All sections have real content. Architecture diagram present. 3000+ words.

6. **Submission form complete.** All required fields filled, materials attached, confirmation received from the hackathon platform.

7. **Public repo gate-check passed.** Final sweep complete, nothing copyrighted committed, `.env.example` clean, parity surfaces still green.

8. **Reachy outcome final.** If stretch phase ran: live Reachy segment in the demo. If go/no-go failed: pre-recorded future-vision segment in the demo.

9. **Phase 2 validation gate run for Phase 1.** `phase-1-validation.md` produced early in Phase 2 reviewing what held, what drifted, what was falsified in the Phase 1 plan. Per hybrid cadence.

10. **Lilymay can articulate what this tool does for her.** Informal success marker, not a deliverable. If Lilymay can describe the tutor to a friend in one sentence and it sounds like what we built, the submission's user-centred story is authentic.

---

## Phase 2 as the last phase

There is no Phase 3 in the hackathon-target plan. Post-hackathon work (multi-subject, mobile app, Reachy as primary interface, template extraction, LES2 round) is explicitly out of scope.

The Thursday evening Phase 2 wrap-up task is therefore: **write a post-hackathon wishlist doc**, not another phase plan. Captures what Phase 3 would be *if* we continued — mostly as input to the post-hackathon retrospective and the `langchain-deepagents-tutor` template cut.

The Reachy stretch phase's success criteria (whichever applies) fold into Phase 2's success criterion 8 rather than existing as their own phase.

---

## Knock-on to post-hackathon work

Identified here so they're not forgotten:

- **LES2 round (second lessons-learned doc).** Written post-submission. Folds in Study Tutor lessons as new rows in the six parity surfaces checklist, plus any new parity surfaces discovered. Template: `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md` format.
- **`/template-create` cut of `langchain-deepagents-tutor`.** Per `state-of-the-project-and-phase-recommendation.md` Appendix A.8. Post-hackathon, from the working study-tutor repo.
- **Multi-subject expansion.** Maths content added to the dataset factory; fine-tune re-run; ChromaDB per-subject collections; role-differentiated Coach rubrics if subjects diverge pedagogically.
- **Flutter mobile app.** Primary interface long-term; not achievable in 31 days.
- **Reachy as primary interface.** Subject of the stretch-phase conversation starter; post-hackathon if not achieved pre-submission.
- **Bedrock cost monitoring.** If Bedrock sees real usage post-hackathon, proper budget alerts and per-session cost attribution needed.

---

## Relationship to the roadmap

The Phase 2 features map to the 13-feature roadmap as follows:

| Phase 2 feature | Roadmap feature | Notes |
|---|---|---|
| FEAT-PH2-001 Gamification State Engine | FEAT-PO-007 roadmap | Same scope |
| FEAT-PH2-002 Static HTML Dashboard | FEAT-PO-009 roadmap | Downscoped per DEC-05: static HTML not React; one-evening build per the decision |
| FEAT-PH2-003 Demo Video Production | not on the roadmap | Submission deliverable, not a product feature |
| Submission polish track | FEAT-PO-012, FEAT-PO-013 roadmap | Public repo + technical write-up |

Roadmap features not shipped in this hackathon (post-hackathon): FEAT-PO-008 (Boss Battle / advanced challenge modes), FEAT-PO-010 (multi-subject), FEAT-PO-011 (mobile app).

---

*Phase 2 scope: 17 April 2026*
*Status: scope only — build plan written Thursday 1 May per hybrid cadence*
*Consuming: `phase-1-scope.md` outcomes (pending), `docs/gamification/design.md` (Phase 0), `planning-cadence-hybrid-approach.md`, `decisions-log-2026-04-17.md`*
*Target: hackathon-submission-complete by end of Saturday 17 May. Submission deadline 18 May 23:59 UTC.*
