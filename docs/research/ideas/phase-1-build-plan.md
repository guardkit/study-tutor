# Phase 1 Build Plan — Three-Layer Architecture + Student Model

## For: Weekend build (26–27 April 2026) + weekday evenings 28 April – 1 May
## Date: 17 April 2026 (last updated 2026-04-30 AM — three of four Phase 1 features now in code on `main`. **FEAT-1773 (Graphiti student model) merged** at `f9fd700` — all 6 TASK-GSM-001..006 completed, `src/study_tutor/knowledge/` shipping (student_model, episodes, graphiti_client, async_write, queries). **FEAT-PH1-002 (planner) merged** at `1e37d7e` then `67ed32e` — all 7 TASK-DSP-001..007 completed, plus TASK-DSP-008 (smoke-gate failure post-mortem) and TASK-DSP-009 (smoke-test fix at `tests/smoke/test_session_planner.py`) closed at `62602a2`. Initial autobuild blocked at the Wave 5→6 smoke gate because the gate command used `feat-ph1-002` (hyphens parsed as Python subtraction in pytest's `-m` expression); fix re-aligned both the marker registration and the gate command to `feat_ph1_002` underscore form. **FEAT-PH1-003 (Player-Coach loop) merged** at `bb42a28` then `9804001` then `d93f153 (chore: mark feature passing)` — all 5 TASK-DTL-001..005 completed, `src/study_tutor/tutoring/` shipping (coach package + orchestrator + session_end). MCP adapter at `src/study_tutor/mcp/adapter.py` line 48 imports `PlayerCoachOrchestrator`; `tutor_turn` routes through the orchestrator when an `orchestrator_factory` is supplied (lines 261-263). The integration is wired.)
## Status: **Three of four core Phase 1 features SHIPPED and integrated into MCP adapter.** FEAT-PH1-004 (RAG + quote verifier) is the remaining critical-path feature and has not yet been spec'd. End-to-end demo session against Synology FalkorDB has not yet been run. Tech writeup empty. Graphiti latency spike DONE (2026-04-27) — `add_episode` median 78.98s, `search_nodes` 0.07s. Architecture cross-cutting concerns extended (ADR-ARCH-018 / ADR-ARCH-019). All three Phase-0-context design refreshes complete (MCP Transport with DDR-001; Tutoring with DDR-002 + DDR-003 + I-T7 + 8-component C4 L3; Inference Runtime with DDR-004 + I-IR7/I-IR8). FEAT-PH1-001 BDD spec generated 2026-04-27 (38 scenarios, 4 smoke / 8 key-example / 9 boundary / 7 negative / 14 edge-case across 5 implementation groups). FEAT-PH1-001 build plan generated 2026-04-29 as **FEAT-1773** (6 subtasks TASK-GSM-001..006, 4-wave structure with Conductor parallelism in Waves 1+2; CC-13 single-call-site invariant + DDR-002 ownership + DDR-003 event-emit-decoupling all expressed in IMPLEMENTATION-GUIDE.md and seam-test stubs; all 38 BDD scenarios @task: tagged for R2 oracle activation; smoke_gates wired between waves). **Schedule slip:** the original Saturday-afternoon FEAT-PH1-001 implementation slot (2026-04-26) did not run; week-1 burndown is now 2 days behind the optimistic plan. Recovery posture below ("Schedule recovery as of 2026-04-29").
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
7. Six parity surfaces still green (SR-01..SR-07); SR-08 (async write-back) and **SR-09 (runtime LLM param assertion)** established. _Architecture-level establishment DONE 2026-04-27_ via ADR-ARCH-018 (CC-13 / CC-14 promotion) and ADR-ARCH-019 (async write-back broadened to every Graphiti write point). _Design-level establishment DONE 2026-04-27_ across three focus runs: MCP Transport (I-MCP8 handler-latency invariant under Graphiti slowdowns; I-MCP9 no-Graphiti-enumeration substring rule); Tutoring (I-T7 fire-and-forget invariant + DDR-002 write ownership + DDR-003 event-emit-on-state-transition + 8-component C4 L3); Inference Runtime (DDR-004 `num_ctx` Modelfile-owned + I-IR7 / I-IR8 invariants + CC-14 two-part smoke test pattern). Phase 1 work that remains is **structural conformance in code**: (a) every Graphiti write site routed through a single fire-and-forget helper (CC-13 / DDR-002 — F1 owned by Coach AsyncSubAgent, F2 / F3 dispatched from Tutor handler); (b) **DDR-001 substring test** + **I-MCP8 handler-latency test** added to `tests/unit/mcp/`; (c) **DDR-003 event-emit-without-write test** added to `tests/integration/`; (d) **CC-14 Modelfile-parameter smoke test** + **CC-14 client-payload smoke test** (per DDR-004) added to `tests/smoke/` and `tests/unit/llm/`. All four test categories land alongside the FEAT-PH1-003 Player-Coach loop work.
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

## Status as of 2026-04-30 (Thursday)

### What has landed

**Pre-build phase (architecture + design + spec) is complete:**

- ✅ **Graphiti latency spike** (2026-04-27) — `add_episode` median 78.98s, `search_nodes` 0.07s. Decision statements recorded in [graphiti-latency-spike-results.md](./graphiti-latency-spike-results.md). SR-08 elevated to load-bearing.
- ✅ **Architecture cross-cutting concerns extended** — ADR-ARCH-018 (CC-13 / CC-14 promotion, fourteen parity surfaces); ADR-ARCH-019 (async write-back at every Graphiti write point, supersedes ADR-ARCH-003); ADR-ARCH-020 (LangChain 1.x pin + Py3.14 alignment).
- ✅ **Phase-0-context design refreshes** for all three focus areas:
  - MCP Transport — DDR-001 (no Graphiti enumeration in MCP descriptions), I-MCP8 / I-MCP9 invariants
  - Tutoring — DDR-002 (Coach AsyncSubAgent owns its own writes), DDR-003 (`session.completed` emits on state transition), I-T7 invariant, 8-component C4 L3 with F1/F2/F3 flush points
  - Inference Runtime — DDR-004 (`num_ctx` Modelfile-owned), I-IR7 / I-IR8 invariants
- ✅ **FEAT-PH1-001 BDD spec** (2026-04-27) — 38 scenarios in [features/graphiti-student-model/graphiti-student-model.feature](../../../features/graphiti-student-model/graphiti-student-model.feature), 8 assumptions in `_assumptions.yaml`, 4 smoke / 8 key-example / 9 boundary / 7 negative / 14 edge-case across 5 implementation groups.
- ✅ **FEAT-PH1-001 build plan** (2026-04-29) — `/feature-plan` produced [FEAT-1773](../../../.guardkit/features/FEAT-1773.yaml) with 6 subtasks ([tasks/backlog/graphiti-student-model/](../../../tasks/backlog/graphiti-student-model/)), IMPLEMENTATION-GUIDE.md (data-flow + sequence + dependency Mermaid diagrams + §4 Integration Contracts + risk register), seam-test stubs for every cross-task contract, smoke_gates between waves (including the **CC-13 single-call-site grep audit** between Wave 2 and Wave 3), and all 38 BDD scenarios `@task:` tagged for R2 oracle activation. TASK-REV-7DC0 in `tasks/in_review/` records the decision rationale.
- ✅ **FEAT-PH1-002 BDD spec** (2026-04-29) — 29 scenarios in [features/deterministic-session-planner/deterministic-session-planner.feature](../../../features/deterministic-session-planner/deterministic-session-planner.feature), 8 assumptions in `_assumptions.yaml` (all confirmed; ASSUM-006/007/008 signed off with measured spike data and FEAT-PH1-001 contract evidence), 4 smoke / 7 key-example / 6 boundary / 6 negative / 11 edge-case across 5 groups (rule-1 override, rule-3 weakest-stale, rule-4 misconception, rule-6 fallback, MCP integration). Scenarios already `@task:`-tagged to TASK-DSP-003..006 for R2 oracle activation.
- ✅ **FEAT-PH1-002 build plan** (2026-04-29) — `/feature-plan` produced [.guardkit/features/FEAT-PH1-002.yaml](../../../.guardkit/features/FEAT-PH1-002.yaml) with 7 subtasks ([tasks/backlog/deterministic-session-planner/](../../../tasks/backlog/deterministic-session-planner/)), 6-wave structure with auto-detected parallelism in Wave 3 (TASK-DSP-003 + TASK-DSP-004), IMPLEMENTATION-GUIDE.md (data-flow + sequence + dependency Mermaid diagrams + §4 Integration Contracts table + Phase 2 stub migration path + Resolved Assumptions sign-off block reproducing the verbatim ASSUM-006/007/008 wordings), seam-test stubs for the FEAT-PH1-001 → FEAT-PH1-002 contract on `SessionCompletedEpisode.topics_covered: list[str]` (TASK-DSP-004) and the TASK-DSP-005 → TASK-DSP-006 contract on the `plan_session` async signature (TASK-DSP-006), smoke_gates wired after waves 5 + 6 (`pytest -m "feat-ph1-002 and smoke"`), and all 29 BDD scenarios `@task:`-tagged via `bdd-linker` at confidence 0.83–0.93 (zero below threshold). Recommended approach: **Option A — Sequential short-circuit pipeline of typed Rule objects** (rules 1/3/4 active, rules 2/5 stubs with `# TODO(phase-2)` source-grep assertion, rule-6 random fallback from developing band, baseline plan when even developing band is empty); determinism enforced structurally via injected `clock` + seeded `random.Random` on `PlannerContext`. Two coverage gaps from review identified and folded into TASK-DSP-007: `test_all_bands_empty_returns_baseline` and `test_post_write_read_consistency_does_not_block`. TASK-REV-DA72 in `tasks/in_review/` records the decision rationale and the 4-option analysis (B inline functions / C scorer-ranker / D feature-flag stubs all rejected on quality/correctness grounds).
- ✅ **FEAT-PH1-003 BDD spec** (2026-04-29) — 39 scenarios in [features/deepagents-tutoring-loop/deepagents-tutoring-loop.feature](../../../features/deepagents-tutoring-loop/deepagents-tutoring-loop.feature), 11 assumptions in `_assumptions.yaml` (5 high / 4 medium / 2 low — ASSUM-006 over-cap reasoning behaviour, ASSUM-011 5s shutdown grace window flagged for verification), 5 smoke / 8 key-example / 8 boundary / 7 negative / 16 edge-case across 5 groups (Coach factory invariants, rubric+quote-fidelity, Player-Coach loop+revision+latency, async write helper+misconception writes+drain, session-end summary+`session.completed` emit). Honours DDR-002 (Coach AsyncSubAgent owns F1), DDR-003 (`session.completed` emits on state transition before F3 dispatch), CC-13/ARCH-019 (every write fire-and-forget), D5 (Coach `tools=[]`), and the two-provider invariant (enforced at factory construction). Scenarios `@task:`-tagged with placeholder TASK-DTL-001..005 to be replaced by `bdd-linker` during `/feature-plan` Step 11.
- ✅ **FEAT-PH1-003 build plan** (2026-04-29 PM late) — `/feature-plan` produced [.guardkit/features/FEAT-PH1-003.yaml](../../../.guardkit/features/FEAT-PH1-003.yaml) with 5 subtasks ([tasks/backlog/deepagents-tutoring-loop/](../../../tasks/backlog/deepagents-tutoring-loop/)), 3-wave structure with parallel-when-safe execution in Waves 1 + 2 (TASK-DTL-001 ‖ TASK-DTL-004 in Wave 1; TASK-DTL-002 ‖ TASK-DTL-003 in Wave 2; TASK-DTL-005 sequential in Wave 3), IMPLEMENTATION-GUIDE.md with all 4 mandatory Mermaid diagrams (data flow, integration-contract sequence, task-dependency graph, §4 cross-feature integration contracts) + constraint-coverage matrix asserting DDR-002 / DDR-003 / CC-13 / D5 / two-provider invariant conformance, three §4 Integration Contracts on the TASK-GSM-004 helper surface (`write_misconception`, `write_session_episode`, `drain(timeout=GRAPHITI_DRAIN_WINDOW)`), seam-test stubs for the per-observation dispatch rule and the `session.completed`-before-F3 ordering, smoke_gates wired after wave 3 (`pytest -m "feat-ph1-003 and smoke"` — exercises the 5 @smoke scenarios spanning the four load-bearing seams), AC-quality linter clean (0 unverifiable criteria), and the `bdd-linker` Step 11 returned `skipped: all_tagged` (the spec's placeholder `@task:TASK-DTL-NNN` tags were already aligned with the canonical task IDs we generated, so no `.feature` rewrite was needed). Recommended approach: **Option A — Deterministic `PlayerCoachOrchestrator` class + Coach AsyncSubAgent + shared Graphiti write helper** (4 options evaluated; B = deepagents task graph, C = sync Coach contradicting ADR-ARCH-012, D = handler-aggregated batched flush explicitly forbidden by DDR-002 — all rejected on architectural conformance grounds). Two low-confidence assumptions resolved: **ASSUM-006** (Coach reasoning > 200 words: recorded in full + `reasoning_long: bool = True` flag, no truncation, no rejection — encoded as Pydantic validator, no spec change), **ASSUM-011** (`GRAPHITI_DRAIN_WINDOW = 5.0` constant exposed by TASK-GSM-004's helper, consumed by TASK-DTL-005's runtime shutdown hook with no per-call override). [TASK-REV-DTL3](../../../tasks/in_review/TASK-REV-DTL3-plan-deepagents-tutoring-loop-with-coach.md) in `tasks/in_review/` records the decision rationale, the 4-option analysis, the constraint-coverage check, and the partial slice-sequencing risk assessment (3 risks: hard dep TASK-DTL-001 → TASK-DTL-003; soft deps TASK-DTL-004 producer-of-protocol-for-TASK-DTL-001 mitigated by co-shipping the helper protocol with TASK-DTL-001; TASK-DTL-005 → TASK-DTL-004 drain surface).
- ✅ **FEAT-1773 (Graphiti student model) MERGED** (commit `f9fd700`) — All 6 TASK-GSM-001..006 completed under `tasks/completed/graphiti-student-model/` (TASK-GSM-006 still in `tasks/backlog/graphiti-student-model/` as the seeding script which runs once per environment). `src/study_tutor/knowledge/` ships: `student_model.py` (7 entities + 6 relationships per scope doc), `episodes.py` (3 episode types F1/F2/F3), `graphiti_client.py` (lazy-import wrapper), `async_write.py` (TASK-GSM-004 single-call-site write helper — the CC-13 / DDR-002 dispatch surface, including `write_misconception`, `write_session_episode`, `write_planner_topic_confidence`, `drain(timeout=GRAPHITI_DRAIN_WINDOW)`), `queries.py` (TASK-GSM-005 query helpers). Tests at `tests/unit/knowledge/` cover all five modules plus a seam test. `scripts/seed_student_model.py` exists; **execution against Synology FalkorDB has not been verified** (next-action item).
- ✅ **FEAT-PH1-002 (deterministic session planner) MERGED** (commits `1e37d7e` → `67ed32e` → `62602a2`) — All 7 TASK-DSP-001..007 completed, plus the post-mortem cycle: **TASK-DSP-008** (root-cause review of the autobuild Wave 5→6 smoke-gate exit-5) and **TASK-DSP-009** (smoke-test wiring fix). The autobuild history file [autobuild-FEAT-PH1-002-history.md](../../history/autobuild-FEAT-PH1-002-history.md) captures the original 2026-04-29 19:17→21:01 ~1h44m run that hit the gate failure; the post-mortem found the gate command used `feat-ph1-002` (hyphens parsed as Python subtraction by pytest's `-m` expression evaluator → silent zero-match → exit 5). TASK-DSP-009's fix: register the marker as `feat_ph1_002` (underscore) in `pyproject.toml`, align the gate command, and write the actual smoke tests at `tests/smoke/test_session_planner.py` (Rule 1 short-circuit + baseline fallback). `src/study_tutor/planner/` ships: `types.py`, `protocols.py`, `rules.py`, `pipeline.py`. MCP integration at `src/study_tutor/mcp/adapter.py` line 40 imports `plan_session`; `_start_tutor_session` routes through it.
- ✅ **FEAT-PH1-003 (Player-Coach loop) MERGED** (commits `bb42a28` → `9804001` → `d93f153 chore: mark feature passing`) — All 5 TASK-DTL-001..005 completed (autobuild ran 2026-04-30 05:53→07:01, ~1h08m elapsed; see [autobuild-FEAT-PH1-003-history.md](../../history/autobuild-FEAT-PH1-003-history.md)); all Coach-approved within 1-2 turns. `src/study_tutor/tutoring/` ships: `coach/__init__.py`, `coach/factory.py` (D5 + two-provider invariants enforced at construction), `coach/sanitise.py` (per-misconception sanitiser), `coach/rubric.py` (six-criterion weighted scoring), `orchestrator.py` (`PlayerCoachOrchestrator` with bounded revision loop), `session_end.py` (DDR-003-ordered emit + F3 dispatch + drain wiring). MCP integration confirmed at `src/study_tutor/mcp/adapter.py` line 48 (`from study_tutor.tutoring.orchestrator import PlayerCoachOrchestrator`); `tutor_turn` routes through `orchestrator.run_turn()` when an `orchestrator_factory` is supplied (lines 261-263) — per-turn instance, no shared state, two concurrent sessions get two independent orchestrators per the @concurrency scenarios. Tests at `tests/unit/tutoring/`. Smoke gate marker fix from TASK-DSP-009 is symmetric for FEAT-PH1-003; the `chore: mark feature passing` commit confirms it now passes.

### What has NOT landed (the build itself)

| Feature | State | Notes |
|---|---|---|
| FEAT-PH1-001 (Graphiti student model) | ✅ **MERGED** | FEAT-1773 at `f9fd700`. `src/study_tutor/knowledge/` (5 modules + async write helper) + `tests/unit/knowledge/` + `scripts/seed_student_model.py`. CC-13 single-call-site invariant honoured by `async_write.py`. |
| FEAT-PH1-002 (session planner) | ✅ **MERGED** | All 7 TASK-DSP-001..007 + TASK-DSP-008 (post-mortem) + TASK-DSP-009 (smoke fix). Marker is `feat_ph1_002` (underscore). MCP `_start_tutor_session` calls `plan_session`. |
| FEAT-PH1-004 (RAG + quote verifier) | ⏳ **Not yet spec'd** — **the only remaining critical-path gap** | Coach's `quote_fidelity` rubric arm currently has no verifier to call. Either spec + plan + build, OR ship a 5-criterion Coach for the demo and defer to Phase 2. |
| FEAT-PH1-003 (Player-Coach loop) | ✅ **MERGED + INTEGRATED** | All 5 TASK-DTL-001..005 + smoke gate passing. `tutor_turn` routes through `PlayerCoachOrchestrator` per-turn instance (DDR-002 + DDR-003 conformance). |
| Seeding executed against Synology | ⏳ Script exists; execution unverified | `scripts/seed_student_model.py` shipped with FEAT-1773. Run once + verify with `get_student_state("lilymay")`. |
| End-to-end demo session via MCP | ⏳ Never run | First chance to see start → 5-7 turns → end with Graphiti episodes written. Demo-readiness checkpoint. |
| Tech writeup Phase 1 section | Empty | Originally Monday work, content-first not polish. |

### Schedule recovery as of 2026-04-30 (Thursday)

**Material progress since 2026-04-29:** Three of the four core Phase 1 features are now in code on `main`. FEAT-1773 (Graphiti student model) merged, FEAT-PH1-002 (planner) merged with its post-mortem cycle (TASK-DSP-008/009 fixed the `feat-ph1-002` hyphen-vs-underscore marker bug), FEAT-PH1-003 (Player-Coach loop) merged and integrated into the MCP adapter. The autobuild runs were faster than the planning estimates (PH1-002 ~1h44m end-to-end including the post-mortem; PH1-003 ~1h08m clean run) — both the GuardKit AutoBuild Coach and the FEAT-PH1-003 tutoring Coach proved load-bearing, with most tasks approved in 1-2 turns.

**Days remaining before Friday 2 May close-out:** 3 (Thu evening 30 Apr, Fri 1 May, Sat 2 May was reserved for Phase 2 plan write-up by original cadence).

**Outstanding gaps to close before end-of-Phase-1:**

| # | Gap | Severity | Estimated work |
|---|-----|----------|---------------|
| G1 | **FEAT-PH1-004 — RAG + source-typed quote verifier — never spec'd or planned** | **Critical-path** — Coach's `quote_fidelity` rubric arm has nothing to call. Two viable resolutions: (a) ship FEAT-PH1-004 in full; (b) ship a 5-criterion Coach for the demo and defer the verifier to Phase 2 with the rubric weight redistributed across the remaining 5 criteria. | (a) Spec ~30 min + plan ~30 min + build ~3h via `/feature-build`; (b) ~30 min code change in `coach/rubric.py` + decision recorded in `phase-1-validation.md` |
| G2 | **Lilymay seeded against Synology FalkorDB** | High — without this, end-to-end demo can't run | ~15 min: `python scripts/seed_student_model.py --student lilymay`, then verify with `get_student_state("lilymay")` returning the expected baseline |
| G3 | **End-to-end demo session via MCP** — never run | High — demo-readiness checkpoint; first chance to see all three layers compose | ~2h: 1× `tutor_start_session` → 5-7× `tutor_turn` → 1× `tutor_session_end` from Claude Desktop, then second `tutor_start_session` to verify the planner reflects state from the first session |
| G4 | **Coach behaviour observation + tuning pass** (rubric weights, threshold) | Medium — Monday/Tuesday work in original plan | ~2h after G3 |
| G5 | **Phase 1 tech-writeup content** | Low (deferrable into Phase 2) | ~2h |
| G6 | **`phase-1-validation.md` close-out + repo tag `phase-1-complete`** | Low | ~30 min on Friday |
| G7 | **Phase 2 build plan write-up** (slipped from original Thu 1 May) | Low (Phase 2 build doesn't start until Sat 4 May) | ~3h on Sat 2 May evening |

**Posture:**

1. **Thu 30 Apr evening (now):** Close G2 first (~15 min) — seed Lilymay against Synology, verify with a query call. This unblocks G3. Decide G1(a) vs G1(b) before kicking off Friday work.
2. **Fri 1 May evening:** Close G1. If choosing (a), run `/feature-spec "Primary-text RAG + source-typed quote verifier"` → `/feature-plan` → `/feature-build`. If choosing (b), edit `coach/rubric.py` to remove the `quote_fidelity` criterion and re-balance the five remaining weights to sum to 1.0; re-run the FEAT-PH1-003 smoke gate.
3. **Sat 2 May morning:** Close G3 — first end-to-end Phase 1 session via MCP. **Demo-readiness checkpoint.** If anything's broken, Sat afternoon absorbs the fix; otherwise proceed to G4.
4. **Sat 2 May afternoon:** Close G4 (Coach tuning pass) if there's signal worth tuning on; otherwise hold for early Phase 2.
5. **Sat 2 May evening:** Close G6 + G7 (Phase 1 close-out + Phase 2 plan write-up). Tag `phase-1-complete`.
6. **G5 (tech writeup) is deferrable** — content-first per the original plan; if compressed timeline matters, write it during Phase 2 evenings using the actual demo session as material.

### Immediate next action

The build is in better shape than the autobuild histories alone suggested — the post-merge state is significantly ahead. Two short steps to confirm and one substantive decision:

```bash
# 1. Verify the smoke gate is actually green for both shipped features (~5 min)
pytest -m "feat_ph1_002 and smoke" -x --no-cov
pytest -m "feat_ph1_003 and smoke" -x --no-cov  # may need marker registration check

# 2. Seed Lilymay's baseline state against Synology FalkorDB (~15 min)
python scripts/seed_student_model.py --student lilymay
# Then verify:
python -c "import asyncio; from study_tutor.knowledge.queries import get_student_state; \
           from study_tutor.knowledge.graphiti_client import GraphitiClient; \
           print(asyncio.run(get_student_state(GraphitiClient(), 'lilymay')))"
```

Then the substantive decision: **FEAT-PH1-004 (a) build it, or (b) defer to Phase 2 + ship a 5-criterion Coach for the demo?** The 6-criterion Coach is the differentiating story (source-typed RAG + quote verification is genuinely novel for GCSE-tutoring); the 5-criterion fallback is honest about what shipped. Recommend (a) if Friday energy permits; (b) is a clean fallback if it doesn't. Either way, document the decision in `phase-1-validation.md`.

---

## Feature Summary

| # | Feature | Depends On | Complexity | Wave | Status (2026-04-29) |
|---|---------|------------|------------|------|---------------------|
| SPIKE | Graphiti three-hop latency measurement | Prereqs green | 2/10 (measurement, no code) | 1 | ✅ DONE 2026-04-27 |
| VALIDATION | Phase 0 validation gate | Phase 0 complete | 1/10 (document) | 1 | ✅ DONE — `phase-0-validation.md` |
| FEAT-PH1-001 | Graphiti student model (schema, helpers, seeding) | SPIKE | 6/10 | 2 | ✅ **MERGED** (FEAT-1773 at `f9fd700`) — `src/study_tutor/knowledge/` shipping, including the CC-13 single-call-site `async_write.py` |
| FEAT-PH1-002 | Deterministic session planner | FEAT-PH1-001 | 4/10 | 3 | ✅ **MERGED** (commits `1e37d7e` → `62602a2`) — TASK-DSP-001..007 + TASK-DSP-008/009 post-mortem cycle landed; smoke gate passing |
| FEAT-PH1-004 | Primary-text RAG + source-typed quote verifier | FEAT-PH1-001 (Text entity), FEAT-PH1-002 (focus_aos) | 5/10 | 3 (parallel with PH1-002) | ⏳ **Not yet spec'd / planned — sole remaining critical-path feature** for PH1-003 quote-fidelity rubric arm |
| FEAT-PH1-003 | DeepAgents tutoring loop + Coach (Coach integrates verifier from PH1-004) | FEAT-PH1-001, FEAT-PH1-002, FEAT-PH1-004 | 8/10 | 4 | ✅ **MERGED + INTEGRATED** (commits `bb42a28` → `d93f153`) — `src/study_tutor/tutoring/` shipping; `tutor_turn` routes through `PlayerCoachOrchestrator` (adapter line 261-263) |
| TECH-WRITEUP | Phase 1 content in technical-writeup.md | Each FEAT as it lands | 2/10 | continuous | ⏳ empty — content-first per original plan |

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

> **2026-04-29 update:** This section is **superseded by FEAT-1773**. The /feature-plan run on 2026-04-29 produced a 6-subtask AutoBuild-ready plan that decomposes this work into TASK-GSM-001..006 across 4 waves with smoke-gate checks (including the CC-13 single-call-site grep audit). See [tasks/backlog/graphiti-student-model/IMPLEMENTATION-GUIDE.md](../../../tasks/backlog/graphiti-student-model/IMPLEMENTATION-GUIDE.md) and run `/feature-build FEAT-1773` to execute. The numbered prose below is preserved as the original sketch — it remains accurate but the FEAT-1773 plan is the canonical source of truth for what to build and in what order.

Switch to Claude Code for implementation.

4. **Define the Pydantic entities.** Create `src/study_tutor/knowledge/student_model.py`. Seven entity types (Student, Subject, Text, Topic, AssessmentObjective, Misconception, TopicConfidence). Six relationship types. Follow the scope doc's tables exactly — don't invent new types. *(→ TASK-GSM-001)*

5. **Define the episode types.** Create `src/study_tutor/knowledge/episodes.py`. Three types (`session_completed`, `topic_confidence_updated`, `misconception_observed`). Each a Pydantic model with the payload fields from the scope doc. *(→ TASK-GSM-002)*

6. **Implement the Graphiti client wrapper.** Create `src/study_tutor/knowledge/graphiti_client.py`. Follow the specialist-agent pattern: lazy import of graphiti-core, fail gracefully if unavailable (logged warning, return None from queries), typed exception surface. Copy the lazy-import shape from `specialist-agent/src/specialist_agent/tools/graphiti_client.py`. *(→ TASK-GSM-003)*

   **Promoted to its own slice in FEAT-1773:** the **shared async fire-and-forget write helper** (CC-13 / DDR-002 single call site) is TASK-GSM-004. The original sketch implicitly bundled this with the query helpers; the planned decomposition makes it auditable on its own (one greppable `add_episode` call site, prompt-injection sanitisation for misconception text, shutdown-grace `drain()`).

7. **Implement the query helpers.** Three functions per the scope doc: `get_student_state`, `get_topic_recommendations`, `record_session_completion`. Each ≤50 lines. Unit tests mock Graphiti responses; integration tests hit the real Synology FalkorDB. *(→ TASK-GSM-005)*

8. **First commit of the day.** "Phase 1 Saturday: latency spike + Phase 0 validation + student model schema + Graphiti client wrapper." *(commits will land per-task as `/feature-build` advances each wave)*

#### Evening (2 hours) — Seeding

9. **Write `scripts/seed_student_model.py`.** Creates Lilymay's Student entity, her Subject/Text/Topic entities for AQA 8700 + 8702, initial TopicConfidence entries (human-estimated), AO1–AO6 AssessmentObjective entities. *(→ TASK-GSM-006, Wave 4)*

10. **Run the seeding script against Synology FalkorDB.** Verify with a direct query (via Graphiti MCP tool in Claude Desktop or a CLI): `search_nodes(query="Lilymay", group_ids=["student:lilymay"])` returns the Student entity with expected attributes. *(seeding script's post-seed verification gate calls `get_student_state(client, "lilymay")` and exits non-zero if the seed didn't land)*

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

8. **Implement `_end_tutor_session`.** On session end: generate session summary, write `session_completed` episode to Graphiti via the fire-and-forget helper per CC-13 / ADR-ARCH-019 (every Graphiti write point is async-from-caller; failures logged-only). Return summary to MCP caller immediately. Note: under ADR-ARCH-019 the same helper is used by mid-session writes (e.g. `misconception_observed` from the Coach loop, planner topic-confidence updates) — not just here.

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

4. **Bedrock validation go/no-go decision** (per [phase-0-validation.md §"What this changes in Phase 1" item 4](./phase-0-validation.md)). Phase 0 success criterion #3 is falsified-but-deferred under TASK-CDR-005. Decide tonight based on GB10's training schedule for the demo-capture window (11–17 May): if GB10 will be free, Bedrock can ride into Phase 2 as scope; if GB10 will be busy mid-demo-week, sequence FEAT-PO-004 (S3 upload + Bedrock import + LLM-client wiring) into a Wednesday or Thursday Phase 1 evening before the 4 May Phase 2 build-plan write-up. ~5 minutes of decision-making; outcome recorded in `phase-1-validation.md` seed on Friday.

**End-of-Tuesday state:** Known failure modes catalogued; Bedrock timing decided.

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

### Pre-execution invocations already run (2026-04-27)

The following commands ran ahead of the Saturday wave to absorb Phase 0 design drift into the post-latency-spike picture. Captured here so Saturday morning starts with the picture aligned, not with re-runs.

| Date | Command | Outcome |
|---|---|---|
| 2026-04-27 | `/arch-refine --adr=ADR-ARCH-009` (SR-08 → CC-13, SR-09 → CC-14) | ADR-ARCH-018 accepted; supersedes ADR-ARCH-009. Six → fourteen parity surfaces. |
| 2026-04-27 | `/arch-refine --adr=ADR-ARCH-003` (broaden async write-back) | ADR-ARCH-019 accepted; supersedes ADR-ARCH-003. Async Graphiti write-back applies at every write point. |
| 2026-04-27 AM | `/system-design --focus="MCP Transport"` | `API-mcp-transport.md`, `DM-mcp-transport.md`, `mcp-tools.json`, `design/README.md` refreshed. New: [`DDR-001`](../../design/decisions/DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md). New invariants I-MCP8 / I-MCP9. Contradiction detection ✓ against 19 ADRs. |
| 2026-04-27 PM | `/system-design --focus="Tutoring"` | `API-tutoring.md`, `DM-tutoring.md`, `events-schema.yaml`, `design/README.md` refreshed (10 deltas). New: [`DDR-002`](../../design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md) (Coach owns own writes; F1/F2/F3 ownership pinned), [`DDR-003`](../../design/decisions/DDR-003-session-completed-emits-on-state-transition.md) (events decoupled from Graphiti write success). New: [`tutoring-c4-l3.md`](../../design/diagrams/tutoring-c4-l3.md) — 8-component diagram approved at mandatory review gate. New invariant I-T7. Contradiction detection ✓ against 19 ADRs. |
| 2026-04-27 PM late | `/system-design --focus="Inference Runtime"` | `API-inference-runtime.md`, `DM-inference-runtime.md`, `design/README.md` refreshed (10 deltas; §4 client/Modelfile split). New: [`DDR-004`](../../design/decisions/DDR-004-num-ctx-modelfile-owned-not-client.md) (`num_ctx` Modelfile-owned not client-owned; CC-14 conformance via two-part smoke test — `ollama show … \| grep PARAMETER` + runner-log line `llama_new_context_with_model: n_ctx = N`). New invariants I-IR7 / I-IR8. C4 L3 skipped (≤ 3 components). Contradiction detection ✓ against 19 ADRs + 3 prior DDRs. **Closes the last outstanding ADR-018/019 stale-reference item.** |
| 2026-04-27 | Graphiti seeding (complete for all three runs) | All ADRs + DDRs + design artefacts seeded sequentially across `architecture_decisions`, `project_design`, and `project_knowledge` groups. Tally: 4 DDRs (1 episode each) → `architecture_decisions`; 6 contracts/data-models (chunked: API-mcp-transport 11, API-tutoring 9, DM-tutoring 12, API-inference-runtime 10, plus single-episode DM-mcp-transport / DM-inference-runtime) + tutoring C4 L3 diagram + design README → `project_design` / `project_knowledge`. ~50 episodes total at ~79s each (~10 min wall-clock per batch with concurrency 3). YAML / JSON files (`events-schema.yaml`, `mcp-tools.json`) not directly seeded — no parser in `guardkit graphiti add-context`; content is referenced via the seeded `.md` artefacts. |

### Outstanding pre-FEAT-PH1-001 items

- **`/system-arch` Phase 1 update.** Not yet run — the architecture summary still describes Phase 1 in pre-spike terms (some Phase 1 row text refreshed in-place by ARCH-019 in `ARCHITECTURE.md` / `container.md` / `domain-model.md`, but the full `/system-arch` re-grounding hasn't been invoked). Lower priority now that all three Phase-0-context design refreshes have landed against the new ADRs without contradictions — the architectural foundation is consistent; the `/system-arch` re-run mostly produces narrative + assumption updates rather than substantive structural changes.
- ~~**`/system-design` for Tutoring + Inference Runtime contexts.**~~ ✅ **DONE 2026-04-27 PM and PM late.** Tutoring closed via `/system-design --focus="Tutoring"` (DDR-002, DDR-003, I-T7, C4 L3 — see Pre-execution table above); Inference Runtime closed via `/system-design --focus="Inference Runtime"` (DDR-004, I-IR7, I-IR8 — see Pre-execution table above). FEAT-PH1-003 Coach loop spec can now land against fresh contracts; the structural conformance items (DDR-001 substring test, I-MCP8 / I-T7 handler-latency tests, DDR-003 event-emit-without-write test, CC-14 Modelfile + client-payload smoke tests per DDR-004) are listed as code work in success criterion #7.
- **Phase 0 validation gate write-up.** Still owed (Saturday morning step 1 of the original plan).

### Original Saturday-morning sequence (still applies for the Phase 1 system-level re-grounding)

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
| `tests/unit/mcp/test_descriptions_no_graphiti_terms.py` | DDR-001 / I-MCP9 | NEW (substring test: no registered MCP tool description mentions graphiti / falkor / episode / write-back, case-insensitive) |
| `tests/unit/mcp/test_handler_latency_under_graphiti_slowdown.py` | I-MCP8 / CC-13 | NEW (`tutor_turn` and `tutor_session_end` return within budget when the Graphiti write helper is patched to sleep ≥ 30s) |

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
