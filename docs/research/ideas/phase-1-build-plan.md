# Phase 1 Build Plan — Three-Layer Architecture + Student Model

## For: Weekend build (26–27 April 2026) + weekday evenings 28 April – 1 May
## Date: 17 April 2026 (last updated 23 April 2026 — FEAT-PH1-004 added from 23 Apr empirical findings)
## Status: Ready to execute when Phase 0 closes Friday 24 April
## Repo: `study-tutor` (Phase 0 scaffolding already present)
## Machine: MacBook Pro M2 Max (primary), GB10 over Tailscale (Ollama + embedder), Synology NAS over Tailscale (FalkorDB), Google Gemini (Graphiti entity extraction + Coach)
## Target completion: End of Friday 2 May 2026 (close of Week 2 of the 31-day burn)

---

## What Phase 1 IS

Week 2 of the 31-day build. Turns the Phase 0 MCP-accessible single-LLM tutor into a genuine three-layer adaptive system with a Graphiti-backed student model, a deterministic session planner, and a Player-Coach tutoring loop. This is the load-bearing phase — if Phase 1 ships, the submission has the differentiating architectural story. If Phase 1 partially ships, Phase 2 scope absorbs the slip.

## What Phase 1 IS NOT

- Not gamification state (Phase 2)
- Not a dashboard (Phase 2)
- Not Reachy (gated, separate phase)
- Not persistent session state beyond Graphiti episodes (maybe Phase 2)
- Not multi-student (post-hackathon)
- Not multi-subject (post-hackathon)

## Success Criteria (reiterated from scope doc)

1. Graphiti latency spike published
2. Student model populated for Lilymay
3. Session planner produces explainable plans
4. Player-Coach tutoring loop runs end-to-end
5. Session completion writes to Graphiti
6. Demo flow works end-to-end
7. Six parity surfaces still green (SR-01..SR-07); SR-08 (async write-back) and **SR-09 (runtime LLM param assertion)** established
8. Technical write-up has content
9. Phase 2 build plan drafted
10. Phase 0 validation gate run
11. **Source-typed corpus ingested** (FEAT-PH1-004)
12. **Quote verifier operational in Coach loop** (FEAT-PH1-004 + FEAT-PH1-003)
13. **Dynamic retrieval decision observable** in at least one Shakespeare session (retrieves) and one Inspector Calls session (skips, analysis mode)

---

## Prerequisites (Friday 25 April evening)

Phase 0 closed by end of Friday 24 April. Before the weekend starts, confirm these are true. If any are not, delay Saturday morning start by the fix time rather than starting on broken foundations.

- [ ] Phase 0 success criteria all green (clean-machine walkthrough passed Wednesday)
- [ ] `phase-0-validation.md` at least sketched — what held, what drifted, what was falsified. Per the hybrid cadence approach doc.
- [ ] FalkorDB reachable on Synology NAS from MacBook over Tailscale. Quick test: `redis-cli -h <synology-tailscale-name> -p <falkor-port> ping` or Graphiti's own connection test.
- [ ] Google Gemini API key configured and tested. `GRAPHITI_LLM_PROVIDER=gemini`, model set to `gemini-2.5-pro` or whatever Graphiti expects.
- [ ] nomic-embed-text-v1.5 on GB10 port 8001 responsive per `specialist-agent/.claude/reviews/TASK-REV-B8E4-walkthrough-log.md §6` — curl returns HTTP 200 with model listed.
- [ ] `graphiti-core` installed in study-tutor venv: `.venv/bin/pip install graphiti-core`
- [ ] `langchain-google-genai` installed (already in `[providers]` from Phase 0)
- [ ] Latest specialist-agent Graphiti integration code reviewed — specifically `src/specialist_agent/tools/graphiti_client.py` and `graphiti_query.py` — to confirm reuse shape

---

## Feature Summary

| # | Feature | Depends On | Complexity | Wave |
|---|---------|------------|------------|------|
| SPIKE | Graphiti three-hop latency measurement | Prereqs green | 2/10 (measurement, no code) | 1 |
| VALIDATION | Phase 0 validation gate | Phase 0 complete | 1/10 (document) | 1 |
| FEAT-PH1-001 | Graphiti student model (schema, helpers, seeding) | SPIKE | 6/10 | 2 |
| FEAT-PH1-002 | Deterministic session planner | FEAT-PH1-001 | 4/10 | 3 |
| FEAT-PH1-004 | Primary-text RAG + source-typed quote verifier | FEAT-PH1-001 (Text entity), FEAT-PH1-002 (focus_aos) | 5/10 | 3 (parallel with PH1-002) |
| FEAT-PH1-003 | DeepAgents tutoring loop + Coach (Coach integrates verifier from PH1-004) | FEAT-PH1-001, FEAT-PH1-002, FEAT-PH1-004 | 8/10 | 4 |
| TECH-WRITEUP | Phase 1 content in technical-writeup.md | Each FEAT as it lands | 2/10 | continuous |

**Dependency chain:**

```
Spike + Phase 0 validation ──► FEAT-PH1-001 (student model) ──┬─► FEAT-PH1-002 (planner) ─────────┐
                                                               │                                    ├─► FEAT-PH1-003 (tutoring loop + Coach)
                                                               └─► FEAT-PH1-004 (RAG + verifier) ──┘
                                                                                                    └─► TECH-WRITEUP continuous
```

FEAT-PH1-002 and FEAT-PH1-004 can run in parallel after PH1-001 — they touch different modules (`agents/session_planner.py` vs `knowledge/corpus.py` + `knowledge/retrieval.py` + `knowledge/quote_verifier.py`). Both feed PH1-003.

---

## Day-by-Day Plan

### Saturday 26 April (weekend day 1) — Spike + validation + student model schema

**Target:** Graphiti latency known. Phase 0 drift documented. Student model schema defined and first episodes writing successfully.

#### Morning (3 hours) — SPIKE + VALIDATION

The morning is intentionally two short deliverables rather than one big code push. Both are cheap in hours and unblock everything downstream.

1. **Phase 0 validation gate (45 min).** Open `phase-0-scope.md`. Walk through the do-not-change list and success criteria. For each: held, drifted, or falsified. Write `docs/research/ideas/phase-0-validation.md` — four paragraphs per the hybrid cadence approach doc. If anything is red, decide before Saturday afternoon whether to fix in Phase 1 or accept as tech debt.

2. **Graphiti latency spike (2 hours).** This is the primary deliverable of the morning. Write a small Python script at `scripts/graphiti_latency_spike.py` that:
   - Connects to FalkorDB on Synology
   - Calls `add_episode` three times against a test group_id
   - Calls `search_nodes` by group_id three times
   - Calls `search_memory_facts` three times
   - Prints min/median/max per operation
   - Uses the real Gemini API (not a mock) so entity-extraction latency is in the measurements

   Record results in `docs/research/ideas/graphiti-latency-spike-results.md`. Two paragraphs plus the measurements table. Decision statements: "add_episode median = Xs, so SR-08 async write-back is [critical / defensive only]." "search_nodes median = Ys, so tutor_start_session stays [long-running / can be reclassified sync]."

3. **Lock or adjust MCP tool classifications.** Based on spike results, update the tool registration in `src/study_tutor/mcp/adapter.py` if the classifications changed. This is a 15-minute edit if needed, zero if the Phase 0 classifications hold.

#### Afternoon (4 hours) — FEAT-PH1-001 schema

Switch to Claude Code for implementation.

4. **Define the Pydantic entities.** Create `src/study_tutor/knowledge/student_model.py`. Seven entity types (Student, Subject, Text, Topic, AssessmentObjective, Misconception, TopicConfidence). Six relationship types. Follow the scope doc's tables exactly — don't invent new types.

5. **Define the episode types.** Create `src/study_tutor/knowledge/episodes.py`. Three types (`session_completed`, `topic_confidence_updated`, `misconception_observed`). Each a Pydantic model with the payload fields from the scope doc.

6. **Implement the Graphiti client wrapper.** Create `src/study_tutor/knowledge/graphiti_client.py`. Follow the specialist-agent pattern: lazy import of graphiti-core, fail gracefully if unavailable (logged warning, return None from queries), typed exception surface. Copy the lazy-import shape from `specialist-agent/src/specialist_agent/tools/graphiti_client.py`.

7. **Implement the query helpers.** Three functions per the scope doc: `get_student_state`, `get_topic_recommendations`, `record_session_completion`. Each ≤50 lines. Unit tests mock Graphiti responses; integration tests hit the real Synology FalkorDB.

8. **First commit of the day.** "Phase 1 Saturday: latency spike + Phase 0 validation + student model schema + Graphiti client wrapper."

#### Evening (2 hours) — Seeding

9. **Write `scripts/seed_student_model.py`.** Creates Lilymay's Student entity, her Subject/Text/Topic entities for AQA 8700 + 8702, initial TopicConfidence entries (human-estimated), AO1–AO6 AssessmentObjective entities.

10. **Run the seeding script against Synology FalkorDB.** Verify with a direct query (via Graphiti MCP tool in Claude Desktop or a CLI): `search_nodes(query="Lilymay", group_ids=["student:lilymay"])` returns the Student entity with expected attributes.

11. **Commit seeding.** Do not commit the seeding script's runtime output — seeding happens once per environment.

**End-of-Saturday state:** Latency known. Phase 0 drift documented. Student model schema defined. Graphiti helpers callable. Lilymay's baseline state is in FalkorDB. No tutoring changes yet — the MCP tutor_turn still works Phase 0-style but is ready for Phase 1 integration.

---

### Sunday 27 April (weekend day 2) — Session planner + RAG layer + Tutoring loop integration

**Target:** Deterministic planner working. Source-typed corpus ingested. Quote verifier callable. MCP handlers upgraded to read student state and return plans. First end-to-end Phase 1 session runs.

**Scope note:** Two parallel tracks this morning (planner + RAG layer) converge into the afternoon's Coach loop. If going solo, do planner first (2h), then RAG layer (2h), then afternoon Coach. If pairing, one dev on each track.

#### Morning track A (2 hours) — FEAT-PH1-002 session planner

1. **Implement `src/study_tutor/agents/session_planner.py`.** Planner function signature: `plan_session(student_id: str, topic_override: str | None = None) -> SessionPlan`. Implements the deterministic rules 1, 3, 4 from the scope doc. Rules 2 and 5 stubbed with `# TODO(phase-2)` comments.

2. **Wire planner into `_start_tutor_session` MCP handler.** The handler now: generates session_id, calls planner with student_id (hardcoded to `lilymay` for Phase 1), stores the SessionPlan in the in-memory session dict, returns session_id + plan summary to the caller.

3. **Test the planner.** Unit tests against mocked student state for a handful of shapes:
   - All topics secure → planner falls through to rule 5 (random developing-band topic)
   - One topic struggling + not revised recently → planner picks it
   - One topic with recent misconception → planner picks it
   - topic_override provided → planner uses it directly

4. **Integration test.** Real call from MCP (Claude Desktop) to `tutor_start_session` for Lilymay. Verify: returns plan with topic name, focus AOs, opening prompt. Plan is shaped by the Saturday-seeded state.

#### Morning track B (2 hours) — FEAT-PH1-004 corpus + retrieval + verifier

This track is the Phase-1 operationalisation of the 23 Apr empirical findings. All three sub-modules are small (~50 lines each) but load-bearing for PH1-003 Coach.

Prerequisites (do before starting): Standard Ebooks Macbeth + A Christmas Carol + Jekyll & Hyde downloaded to `domains/gcse-english/sources/primary_text/`; at least one study guide PDF moved to `domains/gcse-english/sources/secondary_study_guide/`.

1. **Implement `src/study_tutor/knowledge/corpus.py`.** `SourceType` enum (`primary_text`, `secondary_study_guide`, `secondary_critical`, `context_historical`). `CorpusChunk` Pydantic model with `text`, `source_type`, `source_path`, `text_name`, `citation_anchor` (act/scene/line for plays; chapter/paragraph for novels). Corpus loader infers `source_type` from the parent directory name; chunking reuses the pattern from `agentic-dataset-factory`.

2. **Implement `src/study_tutor/knowledge/retrieval.py`.** Three functions:
   - `has_primary_text(text_name: str) -> bool` — corpus lookup
   - `retrieve(query, text_name, focus_aos, top_k=6) -> list[CorpusChunk]` — source-filtered retrieval; returns `[]` for AO3-only queries (R3 retrieval-bypass) or when `has_primary_text` is False (R2 dynamic decision)
   - `should_retrieve(text_name, focus_aos) -> tuple[bool, str]` — the explicit decision function the Coach/Player loop calls; returns `(False, "analysis_mode:no_primary_text")` or `(False, "ao3_only:training_first")` with reason strings that surface in session metadata

3. **Implement `src/study_tutor/knowledge/quote_verifier.py`.** Functions:
   - `extract_quotes(response_text) -> list[Quote]` — finds `"…"` spans (≥4 words, to avoid false positives on short phrases)
   - `verify_quote(quote, corpus_chunks) -> VerifyResult` — returns `PrimaryMatch(citation)`, `SecondaryMatch(phrase)`, `FuzzyMatch(corrected, edit_distance)`, `NoMatch()`
   - `rewrite_response(response_text, verify_results) -> str` — applies the transformations from scope §4 (annotate primary, rewrite secondary as paraphrase, strip/correct unmatched)

4. **Unit tests.** One per module. Corpus loader: correct source-type inference from directory. Retrieval: decision function covers the four branches (primary present / absent, AO3 active / not). Verifier: four match types each produce the right rewrite.

5. **Integration smoke.** Load Macbeth + a Macbeth study guide into the corpus. Hand a response containing a genuine Shakespeare quote and a genuine study-guide phrase to the verifier. Confirm the first is annotated with citation, the second is rewritten as *"as one critic observes"*.

#### Afternoon (4 hours) — FEAT-PH1-003 Player-Coach loop

This is the critical-path feature. Front-load it on Sunday afternoon while energy is fresh.

5. **Implement the Coach agent.** Create `src/study_tutor/agents/coach.py`. Follows the agentic-dataset-factory Coach pattern: `create_deep_agent` with a system prompt from `roles/tutor/prompts/coach.md` (written in Phase 0 FEAT-PO-001 as skeleton; fill it out now), `tools=[]`, different provider than the Player (Gemini 2.5 Pro).

6. **Write the Coach prompt.** `roles/tutor/prompts/coach.md`. Structure:
   - Role description (educational tutoring quality evaluator, not a tutor)
   - Rubric with 6 criteria: 5 from scope doc + **`quote_fidelity`** (new, from FEAT-PH1-004) — each with specific evaluation guidance
   - Structured JSON output schema: `{decision: "accept"|"revise", score: float, criteria: {...}, reasoning: str, misconceptions_observed: list[str], quote_verification: {primary_matches: [...], secondary_rewrites: [...], stripped: [...]}}`
   - Constraints (never output for the student; max 200 words of reasoning)

7. **Implement the Player-Coach loop.** Update `_run_tutor_session` in MCP adapter. Per turn:
   - Call `should_retrieve(text_name, focus_aos)` (from FEAT-PH1-004). If True, retrieve context and attach to Player prompt. If False, attach `retrieval_skipped` reason to turn metadata and proceed without context.
   - Player generates response (grounded in plan + transcript + retrieved context if any)
   - Run Player response through `quote_verifier` before Coach sees it; rewrites applied in place, verification metadata passed to Coach
   - Coach evaluates against rubric (including `quote_fidelity` score derived from verifier output)
   - If score ≥ 0.7: emit verified+rewritten Player response to student, record turn
   - If score < 0.7 and retries remain: Player revises with Coach feedback, loop
   - If score < 0.7 and max retries exhausted: emit lowest-scoring reply with a silent log marker, flag for session-end review

8. **Implement `_end_tutor_session`.** On session end: generate session summary, write `session_completed` episode to Graphiti asynchronously per SR-08. Return summary to MCP caller immediately.

#### Evening (2 hours) — First end-to-end Phase 1 session

9. **Run a full session against Lilymay's seeded state via MCP.** From Claude Desktop:
   - `tutor_start_session` — verify planner returns a real topic (e.g. Macbeth witches if that's lowest-confidence)
   - 5–7 `tutor_turn` calls — have an actual tutoring conversation via the MCP tool
   - `tutor_session_end` — verify session summary returned, Graphiti episode written (check via Graphiti MCP tool or CLI)
   - Second `tutor_start_session` — verify the planner recommends a different topic informed by the first session

10. **Measure turn latencies.** Record p50 and p95 for `tutor_turn` across the session. Confirm within the 30s budget from scope doc. If over, note for Monday debugging.

11. **Commit Sunday work.** "Phase 1 Sunday: session planner + Player-Coach loop + end-to-end Phase 1 session runs."

**End-of-Sunday state:** Three-layer architecture runs end-to-end. Tutor turns invoke Coach. Graphiti episodes written. Next-session plans reflect prior session state. This is the minimum credible submission beyond Phase 0.

---

### Monday 28 April (evening, ~2 hours) — Coach tuning + Tech writeup section

Monday is the first chance to tune the Coach based on observed Sunday behaviour.

1. **Review Coach decisions from Sunday's session.** Check the session summary and Coach reasoning logs. Was Coach too strict? Too lenient? Were the rejection-revision loops genuinely improving the response?

2. **Tune rubric weights and threshold if needed.** The 0.7 threshold and weights in the scope doc are initial guesses. Based on real behaviour, adjust. Document any change in the Coach prompt with a dated comment.

3. **Write technical writeup content.** Open `docs/submission/technical-writeup.md`. Fill in the three-layer architecture section with real paragraphs referencing what was built Saturday+Sunday. Not polish yet — content first, edit later.

**End-of-Monday state:** Coach calibrated. Write-up has real content where stubs were.

---

### Tuesday 29 April (evening, ~2 hours) — Session quality review

Use Tuesday evening for an honest review of tutoring quality. The demo video depends on session quality; if it's weak, better to discover Tuesday than Thursday.

1. **Run 3 full sessions with Lilymay (real user).** If Lilymay is available, have her do real revision via the MCP path or OpenWebUI (whichever is wired to Phase 1 code — likely OpenWebUI once LiteLLM routes to the MCP session, which may be a later setup). Otherwise, Rich acts as student.

2. **Observe failure modes.** Specifically watch for:
   - Coach rejecting appropriate Player responses (over-strict)
   - Misconceptions-observed being wrong (Coach fabricating misconceptions)
   - Plans that don't reflect Graphiti state (query bug)
   - Session summaries that don't match what happened (summary prompt bug)

3. **File tightening tasks for Wednesday/Thursday.** Don't fix in-flight on Tuesday. Keep Tuesday observational; Wednesday does the fixes.

**End-of-Tuesday state:** Known failure modes catalogued.

---

### Wednesday 30 April (evening, ~2 hours) — Fix pass + Phase 1 validation evidence

1. **Fix the top 2–3 issues from Tuesday's review.** Time-box to 90 minutes. If a fix is looking like more than 60 minutes by itself, defer to Thursday or absorb into Phase 2.

2. **Run a clean session to verify fixes.** One end-to-end session; note that the fix resolved the issue without introducing new ones.

3. **Update Coach rubric documentation.** If weights or thresholds changed during the week, the scope doc's Coach rubric table needs updating — or a note added that the shipped values differ.

**End-of-Wednesday state:** Known issues fixed. Session quality acceptable for demo content capture next week.

---

### Thursday 1 May (evening, ~3 hours) — Phase 2 planning per hybrid cadence

Per the hybrid cadence approach doc, Thursday evening of a phase is when the *next* phase's build plan gets written. Phase 2 scope already sketched (before Phase 1 started). Phase 2 build plan writes now, informed by what Phase 1 actually shipped.

1. **Open `phase-2-scope.md`.** Re-read. Note which success criteria still apply vs which need adjustment given Phase 1 outcomes.

2. **Open `graphiti-latency-spike-results.md` and any Coach tuning notes.** These are the Phase 2 inputs that didn't exist when the Phase 2 scope was sketched.

3. **Write `phase-2-build-plan.md`.** Day-by-day for the weekend of 3–4 May and following weekday evenings through Friday 9 May. Mirror the shape of Phase 0 and Phase 1 build plans — prerequisites, wave structure, day-by-day, review gates, risk mitigation.

4. **Check the Reachy situation.** Has Scholar arrived? If yes, the 4 May go/no-go gate is on-schedule — Sunday is the day to spin up the Reachy conversation starter as a parallel thread. If no, continue as planned — the future-vision-segment fallback is in play.

**End-of-Thursday state:** Phase 2 plan written. Phase 1 code complete. Reachy status clarified.

---

### Friday 2 May (evening, ~1 hour) — Phase 1 close-out

Phase 1 ends. Phase 2 starts Saturday 3 May.

1. **Run Phase 1 success criteria check.** All ten items from the scope doc. Green/yellow/red each. If any red, decide before weekend whether to absorb into Phase 2 or defer.

2. **Commit final Phase 1 state.** Tag the repo `phase-1-complete` or equivalent.

3. **Write short `phase-1-validation.md` outline.** This is the input to Phase 2 Saturday morning's validation gate — seeded now so it's fast to finalise then.

**End-of-Friday state:** Phase 1 closed. Phase 2 weekend starts with full scope + build plan + validation seed in hand.

---

## GuardKit Command Sequence

Phase 1 follows the same GuardKit pattern as Phase 0 — front-load the system-level commands, then per-feature spec-and-plan. Differs from Phase 0 in that the ARCHITECTURE.md and DESIGN.md already exist from Phase 0 and are *updated* in Phase 1 rather than regenerated.

```bash
# Saturday 26 April morning, after spike + Phase 0 validation

# UPDATE (not regenerate) architecture and design to reflect Phase 1 scope
/system-arch \
  --from docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context docs/research/ideas/phase-0-validation.md \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  --context docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/decisions-log-2026-04-17.md \
  --context docs/research/ideas/deepagents-patterns-review.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_client.py \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_query.py

/system-design \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md

/system-plan \
  --from docs/design/DESIGN.md \
  --context docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md

# Then per-feature, in dependency order:

/feature-spec "Graphiti Student Model — entities, relationships, episodes, query helpers, seeding script, async write-back" \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  --context domains/gcse-english/GOAL.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_client.py

/feature-plan "Graphiti Student Model" \
  --context features/graphiti-student-model/graphiti-student-model_summary.md

/feature-spec "Deterministic Session Planner — SessionPlan type, rules 1/3/4 implemented, MCP integration" \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context src/study_tutor/knowledge/student_model.py \
  --context src/study_tutor/mcp/adapter.py

/feature-plan "Deterministic Session Planner" \
  --context features/deterministic-session-planner/deterministic-session-planner_summary.md

/feature-spec "DeepAgents Tutoring Loop with Coach — Player-Coach integration, Coach rubric, session-end summary, async Graphiti write-back" \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context roles/tutor/prompts/coach.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/agents/coach.py \
  --context src/study_tutor/mcp/adapter.py

/feature-plan "DeepAgents Tutoring Loop with Coach" \
  --context features/deepagents-tutoring-loop/deepagents-tutoring-loop_summary.md

# Autonomous build recommended for FEAT-PH1-001 (schema work, well-specified), reviewer-in-loop for FEAT-PH1-003 (critical path, quality-sensitive)
```

---

## Files That Will Change

### New files in study-tutor

| File | Feature | Change type |
|------|---------|-------------|
| `src/study_tutor/knowledge/student_model.py` | FEAT-PH1-001 | NEW (7 entity types, 6 relationships) |
| `src/study_tutor/knowledge/episodes.py` | FEAT-PH1-001 | NEW (3 episode types) |
| `src/study_tutor/knowledge/graphiti_client.py` | FEAT-PH1-001 | NEW (lazy-import wrapper) |
| `src/study_tutor/knowledge/corpus.py` | FEAT-PH1-004 | NEW (source-typed chunk model + loader) |
| `src/study_tutor/knowledge/retrieval.py` | FEAT-PH1-004 | NEW (dynamic retrieval decision + source-filtered search) |
| `src/study_tutor/knowledge/quote_verifier.py` | FEAT-PH1-004 | NEW (primary/secondary distinguisher + rewriter) |
| `domains/gcse-english/sources/primary_text/macbeth_shakespeare_1606.txt` | FEAT-PH1-004 | NEW (Standard Ebooks) |
| `domains/gcse-english/sources/primary_text/christmas_carol_dickens_1843.txt` | FEAT-PH1-004 | NEW (Standard Ebooks) |
| `domains/gcse-english/sources/primary_text/jekyll_hyde_stevenson_1886.txt` | FEAT-PH1-004 | NEW (Standard Ebooks) |
| `domains/gcse-english/sources/README.md` | FEAT-PH1-004 | REPLACE Phase 0 stub with source-type directory doc |
| `src/study_tutor/agents/session_planner.py` | FEAT-PH1-002 | NEW |
| `src/study_tutor/agents/coach.py` | FEAT-PH1-003 | NEW |
| `roles/tutor/prompts/coach.md` | FEAT-PH1-003 | EXTEND from Phase 0 skeleton |
| `scripts/seed_student_model.py` | FEAT-PH1-001 | NEW |
| `scripts/graphiti_latency_spike.py` | SPIKE | NEW (can be retained for repeated measurement) |
| `docs/research/ideas/phase-0-validation.md` | VALIDATION | NEW |
| `docs/research/ideas/graphiti-latency-spike-results.md` | SPIKE | NEW |
| `docs/research/ideas/phase-2-build-plan.md` | Thursday prep | NEW |
| `docs/research/ideas/phase-1-validation.md` (seed only) | Friday close-out | NEW stub |
| `tests/unit/knowledge/test_student_model.py` | FEAT-PH1-001 | NEW |
| `tests/unit/knowledge/test_corpus.py` | FEAT-PH1-004 | NEW |
| `tests/unit/knowledge/test_retrieval.py` | FEAT-PH1-004 | NEW (covers four-branch decision) |
| `tests/unit/knowledge/test_quote_verifier.py` | FEAT-PH1-004 | NEW (covers four match types) |
| `tests/unit/agents/test_session_planner.py` | FEAT-PH1-002 | NEW |
| `tests/integration/test_tutoring_loop.py` | FEAT-PH1-003 | NEW |
| `tests/integration/test_rag_end_to_end.py` | FEAT-PH1-004 | NEW (Shakespeare → retrieve+verify; Inspector Calls → skip+analysis-mode) |
| `tests/smoke/test_ollama_runtime_params.py` | SR-09 | NEW (asserts num_ctx and num_predict reach runner) |

### Modified files

| File | Change |
|------|--------|
| `src/study_tutor/mcp/adapter.py` | `_start_tutor_session` calls planner; `_run_tutor_session` becomes Player-Coach loop; `_end_tutor_session` writes Graphiti episode async |
| `src/study_tutor/llm/client.py` | Add dispatch for Gemini (Coach provider) if not already present from Phase 0 |
| `pyproject.toml` | Ensure `graphiti-core` is declared (may move out of `[providers]` into a separate `[knowledge-graph]` extra) |
| `docs/architecture/ARCHITECTURE.md` | Updated by `/system-arch` for Phase 1 |
| `docs/design/DESIGN.md` | Updated by `/system-design` for Phase 1 |
| `docs/submission/technical-writeup.md` | Real content replaces stubs (three-layer architecture, Graphiti, Coach) |

### No changes expected

- `.env.example` (Phase 0 already has the env vars Phase 1 needs)
- `scripts/mcp-wrapper.sh` (no transport changes)
- `roles/tutor/role.yaml` (structure set in Phase 0)

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Graphiti latency spike shows multi-second writes blocking tutoring | Medium | High | SR-08 makes write-back fire-and-forget; spike just informs which path within that |
| Gemini entity extraction unavailable or rate-limited | Low | Medium | Fall back to OpenAI gpt-5.4 for entity extraction temporarily; document the decision; re-enable Gemini when available |
| Coach over-strict, rejects too many Player responses | High | Medium | Monday evening is dedicated to Coach tuning; rubric weights and threshold adjustable |
| Coach under-strict, accepts bad responses | Medium | High | Tuesday session review catches this; Wednesday fixes |
| Saturday spike reveals three-hop latency > 10s | Low | High | Revisit DEC-02 topology — likely consequence is running Graphiti LLM locally on GB10 instead of Gemini, at cost of GB10 scheduling |
| Player latency > Coach + Player latency budget | Medium | Medium | Fall back to accept-first-revise-later pattern documented in scope doc |
| Student model schema needs changes once first session is seen | Medium | Low | Graphiti is schema-flexible; adding relationships post-seed is cheap |
| Lilymay unavailable for Tuesday session review | Medium | Low | Rich acts as student; observational mode not real teaching |
| Phase 0 validation surfaces a regression that needs immediate fix | Low | Medium | Saturday morning reserves 1h for this; if more is needed, absorb into Sunday morning |

---

## Review Gates

### End of Saturday

**Hard question:** Does `get_student_state("lilymay")` return a realistic baseline matching known state?

- Yes → Schema correct, helpers work. Sunday can proceed with planner confidently.
- No → Sunday morning absorbs the schema fix; planner slips to Sunday afternoon.

### End of Sunday

**Hard question:** Does a complete tutoring session (start → 5+ turns → end) run end-to-end via MCP, with Graphiti episode written?

- Yes → Phase 1 critical path done by end of weekend. Monday–Wednesday evenings are tuning, not build.
- No → Monday–Tuesday evenings absorb the slip. Coach quality work compressed.

### End of Wednesday

**Hard question:** Is tutoring quality acceptable for demo video capture starting 11 May?

- Yes → Phase 2 can start on time.
- No → Thursday absorbs final tuning; Phase 2 build plan still written.

### End of Friday

**Hard question:** Have the ten Phase 1 success criteria been evaluated?

- All green → Phase 2 weekend (3–4 May) starts with full momentum.
- Any red → Yellow/red items documented in `phase-1-validation.md`, inherited as Phase 2 constraints.

---

## YouTube Content from Phase 1

Not a deliverable, but worth capturing while it happens:

- "The three-hop Graphiti latency spike — what I measured"
- "Player-Coach tutoring: when the Coach rejects the response my 15-year-old was about to see"
- "Async write-back is not optional: why the MCP tutor must not wait for Graphiti"
- "Adaptive tutoring in practice: how last session shaped this session"

Sunday's end-to-end session is the best raw footage of the build. Capture the screen recording even if the final demo uses cleaner footage captured in Phase 2.

---

## Expected Timeline (summary)

| Day | Work | Hours | End-of-day state |
|-----|------|-------|------------------|
| Fri 25 Apr | Prereqs check | 1 | Ready for Phase 1 weekend |
| Sat 26 Apr | Spike + Phase 0 validation + student model | 9 | Graphiti latency known, schema done, Lilymay baseline seeded |
| Sun 27 Apr | Planner + Player-Coach loop + first end-to-end | 9 | Phase 1 critical path complete |
| Mon 28 Apr | Coach tuning + tech writeup | 2 | Coach calibrated |
| Tue 29 Apr | Session quality review | 2 | Failure modes catalogued |
| Wed 30 Apr | Fix pass | 2 | Known issues fixed |
| Thu 1 May | Phase 2 build plan | 3 | Phase 2 ready, Reachy status checked |
| Fri 2 May | Phase 1 close-out | 1 | Phase 1 tagged complete |

**Total: ~29 hours over 8 days**, weekend-weighted 18h vs weekday-evening 11h. Slightly heavier than Phase 0 because the code content is larger.

---

*Phase 1 build plan: 17 April 2026*
*Consuming: `phase-1-scope.md`, `decisions-log-2026-04-17.md`, `planning-cadence-hybrid-approach.md`, `cross-agent-lessons-from-specialist-agent.md`*
*Successor: `phase-2-scope.md` (build plan written Thu 1 May per hybrid cadence)*
*Target: three-layer architecture working end-to-end by 2 May; adaptive tutoring demonstrable*
