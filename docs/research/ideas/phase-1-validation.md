# Phase 1 Validation Gate

## Date written: 2026-05-02 (Saturday — Phase 1→Phase 2 boundary, slipped one day from the planned Friday-evening seeding per the Phase-2 build plan §"Must be green by Friday 1 May evening" checklist)
## Status: **Drafted as a working seed.** Final marks against each Phase 1 success criterion (1–14) and each `phase-1-scope.md §Do-Not-Change` item are filled in below; the load-bearing finding is the **falsification of G2 + G3** (live runtime against graphiti — the integration was tests-only-green, never runtime-green) which redirects Phase 2's first day from "FEAT-PH2-001 spec + plan" to "Graphiti runtime integration repair → FEAT-PH2-001 spec + plan".
## Successor / consumer: `phase-2-build-plan.md` Day 1 entry (Saturday 2 May — section to be amended in lockstep with this doc).

---

## Held — Phase 1 commitments that shipped intact

These items match the spec and survived integration into the codebase. Cited via the commit or the merged module so future-me can audit at a glance.

- **G1 — Graphiti latency spike published.** `docs/research/ideas/graphiti-latency-spike-results.md` exists with real measurements (`add_episode` median 78.98s; `search_nodes` 0.07s, 2026-04-27). Informed `SR-08` elevation to load-bearing and `ADR-ARCH-019`'s broadening of async write-back to every flush point. Held.
- **G4 (partial) — Player-Coach tutoring loop architecture.** FEAT-PH1-003 merged at commit `bb42a28` (`feat(FEAT-PH1-003): land DeepAgents tutoring loop with Coach`). The orchestrator at [src/study_tutor/tutoring/orchestrator.py](src/study_tutor/tutoring/orchestrator.py) wires Player + Coach + QuoteVerifier behind clean Protocol seams; Coach runs on a different provider than Player; the misconfigured-loop guard rejects same-provider configurations. Architecture held; **runtime end-to-end execution unverified — see G3/G4/G6 falsifications below.**
- **G7 — Six parity surfaces SR-01..SR-07 still green.** No regression introduced by FEAT-PH1-001..004 work. Live unit + smoke + integration suite is **695/696** with the venv on PATH; the single failure (`tests/unit/planner/test_protocols.py::test_mypy_strict_accepts_structurally_conforming_rule`) is a pre-existing dev-machine env issue (mypy installed at the system Python 3.14, not in `.venv`, so its subprocess can't resolve the editable `study_tutor` install) — last touched in commit `1e37d7e` (FEAT-PH1-002) and not introduced by Phase 1 close-out work. SR-08 (async write-back) and SR-09 (runtime LLM param assertion) honoured at the architecture and design layers per ADR-ARCH-018 / ADR-ARCH-019.
- **G9 — Phase 2 build plan drafted.** `phase-2-build-plan.md` written 2026-04-30 and revised the same day for confirmed Reachy delivery (commits `ea28ee2` and `f426aa8`). Held.
- **G10 — Phase 0 validation gate run.** `phase-0-validation.md` produced early in Phase 1; cadence honoured.
- **G11 (architecturally) — Source-typed corpus ingested.** `src/study_tutor/knowledge/{corpus_models.py,corpus.py,retrieval.py}` shipped via FEAT-PH1-004 (PRV-002 / PRV-003 / PRV-004 in `tasks/completed/`). The four-way source-type structure exists in [domains/gcse-english/sources/](domains/gcse-english/sources/). Pydantic source-type discriminator is present at [src/study_tutor/knowledge/corpus_models.py](src/study_tutor/knowledge/corpus_models.py). **Live ingestion against real text payloads not exercised in Phase 1 — would surface the same LLM-wiring gap as G2 if attempted; see falsification cluster.**
- **G12 (architecturally) — Quote verifier operational in Coach loop.** Verifier integrated into orchestrator at [src/study_tutor/tutoring/orchestrator.py:460-461](src/study_tutor/tutoring/orchestrator.py#L460-L461) (`QuoteVerifierLike` Protocol; `_apply_coach_handover`). Six-criterion rubric at [src/study_tutor/tutoring/coach/rubric.py:200](src/study_tutor/tutoring/coach/rubric.py#L200) carries `quote_fidelity=0.20`. **Demo-session evidence not captured — see G3 falsification.**
- **DNC: Single student.** Lilymay is the only `student_id` referenced. Held.
- **DNC: Coach uses a different provider than Player.** Misconfigured-loop guard at orchestrator init enforces this at runtime. Held.
- **DNC: No gamification state in Phase 1.** No gamification code in `src/`. Held.
- **DNC: No Reachy integration in Phase 1.** Confirmed; Reachy delivery moved to 8 May, integration thread runs Phase 2-or-later. Held.
- **DNC: In-memory session state only.** No persistent session-state code in Phase 1. Held.
- **DNC: Retrieval is selective.** Dynamic-retrieval-decision module exists at [src/study_tutor/knowledge/retrieval.py](src/study_tutor/knowledge/retrieval.py). Held architecturally; live behavioural validation pending (G13 falsified by the same root cause as G2/G3).
- **DNC: In-copyright primary texts are not in the corpus.** No copyrighted text payloads checked into `domains/`. Held.
- **DNC: Quote verification is post-hoc, not pre-generation.** The verifier runs after Player generation in the orchestrator, before Coach handover. Held.

---

## Drifted — items that shipped but with material deviations from the Phase 1 spec

These changes are real but small enough that downstream Phase-2 plans don't need to be redrawn around them — they just need to be acknowledged so the spec and the code stop disagreeing.

- **DNC drift: Group-id format moved from colon to dash during close-out.** `phase-1-scope.md §FEAT-PH1-001` and `student_model.py` originally specified `student:<student_id>`, `subject:<subject_slug>`, `fleet:appmilla`. graphiti-core 0.29's `GroupIdValidationError` rejects characters outside `[A-Za-z0-9_-]`, so the runtime constants migrated to `student-<student_id>`, `subject-<subject_slug>`, `fleet-appmilla` during the Phase-1 close-out repair sweep (2026-05-02). Module docstring and three test files updated; cross-repo divergence note (specialist-agent uses `appmilla-fleet`) preserved. **Consequence for Phase 2:** none structurally — gamification group ids will use the dash form from day one. Update `phase-2-scope.md` if it cites the colon form anywhere.
- **G14 partial drift — SR-09 smoke assertion lives at the design layer, not as live runner output.** ADR-ARCH-018 promotes SR-09 to `CC-14` and the two-part smoke test pattern is documented; the architectural establishment is held. Live `ollama show` walkthrough against a running instance is not in the captured evidence; that's a "complete the test, don't redesign it" item rather than a structural drift.
- **Stale task-state hygiene.** `tasks/in_review/TASK-REV-AB7A-analyze-failed-autobuild-feat-70a4.md` is `status: review_complete` but still in `in_review/`. Move-to-`completed/` sweep needed. `tasks/backlog/primary-text-rag-and-quote-verifier/` still contains stub `IMPLEMENTATION-GUIDE.md` and `README.md` after the seven PRV tasks shipped; stub directory can be deleted. Cosmetic; not blocking.

---

## Falsified — Phase 1 commitments that did not actually ship at runtime

The cluster below was the load-bearing finding of the close-out gate run. Each item ships **at the architecture and unit-test layers** but **fails when exercised against a live graphiti-core 0.29 client.** The autobuild gate stayed green throughout Phase 1 because the entire graphiti integration is tested behind mocks — no test in `tests/` ever talks to a real `Graphiti` instance. The drift surfaces only at runtime, which is exactly what the close-out gates are designed to detect.

### Root cause: `src/study_tutor/knowledge/graphiti_client.py:get_client` is structurally incomplete.

`get_client(config)` constructs `Graphiti(graph_driver=driver)` with **no `llm_client`, no `embedder`, and no `cross_encoder`** — graphiti-core 0.29 then defaults all three to OpenAI clients keyed off `OPENAI_API_KEY`, which in this project is the placeholder `not_needed`. The `GraphitiConnectionConfig` fields `llm_provider="gemini"`, `llm_model="gemini-2.5-pro"`, and `embedder_url="http://promaxgb10-41b1:8001/v1"` exist but are never consumed during Graphiti construction. Result: every `add_episode` call (which graphiti-core 0.29 implements as an LLM-driven entity-extraction round-trip) hits OpenAI's `responses.parse` endpoint and 401s with `Incorrect API key provided: not_needed`.

### Falsified items

- **G2 — Student model populated for Lilymay.** `python scripts/seed_student_model.py` runs to exit code 0 but **0 of 25 entity writes persist** (all fail in `_perform_write` with `openai.AuthenticationError` once the LLM/embedder root cause is reached). The `seeded Lilymay baseline (subjects=0, confidences=0, succeeded_writes=25)` log line is misleading: `succeeded_writes` counts tasks that completed without abandonment in the drain window — it does not count tasks that actually wrote to FalkorDB. Verified empty: `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns `{"message":"No relevant nodes found","nodes":[]}` and `mcp__graphiti__get_episodes(group_ids=["student-lilymay"])` returns `{"message":"No episodes found","episodes":[]}`. **Falsified.**
- **G3 — Session planner produces explainable plans, exercised against live state.** `get_topic_recommendations("lilymay", count=3)` reads via the same broken client path. Cannot be exercised end-to-end until G2's blocker is cleared. Pure-functional ranking module ([src/study_tutor/planner/](src/study_tutor/planner/)) is correct; it just has nothing to read. **Falsified at the runtime layer; held at the unit-test layer.**
- **G4 (runtime) — Player-Coach tutoring loop runs end-to-end.** `tutor_start_session` calls `get_student_state` which hits the same client path. The orchestrator architecture is sound (see Held above); the runtime hop into graphiti will fail with the same `AuthenticationError` until the LLM/embedder are wired. **Falsified at the runtime layer.**
- **G5 — Session completion writes to Graphiti.** F3 `record_session_completion` dispatches via `GraphitiWriteHelper.schedule_write` → `_perform_write` → `add_episode`. Same OpenAI default; same 401. **Falsified at the runtime layer.**
- **G6 — End-to-end demo flow works.** Cannot run without G2/G4/G5. **Falsified.**
- **G8 — Technical write-up has content, not stubs.** `docs/submission/technical-writeup.md` not yet drafted with real content. Not blocking but acknowledged. **Falsified for now; defer-into-Phase-2 acceptable per Phase 1 G5's allowance and per the Phase-2 build plan's "POLISH-WRITEUP" continuous track.**
- **G13 — Dynamic retrieval decision observable in a session.** Cannot be observed without a running session. **Falsified at the runtime layer; module logic correct in unit tests.**

### Secondary findings discovered during the close-out repair sweep (2026-05-02)

These were also broken and have been fixed in-flight; they would have surfaced as the next blockers behind the LLM-wiring root cause regardless. Capturing them here so the audit trail is complete.

- **Read API mismatch.** `queries.py:get_student_state` called `inner.search_nodes(group_ids, "")` and `inner.search_memory_facts(group_ids, "")` — neither exists on graphiti-core 0.29's `Graphiti` class (those are graphiti **MCP server** tool names, not library methods). **Patched 2026-05-02:** new `_read_student_partition` seam in [src/study_tutor/knowledge/queries.py](src/study_tutor/knowledge/queries.py) calls `EntityNode.get_by_group_ids(driver, group_ids, limit=...)` / `EntityEdge.get_by_group_ids(...)` and swallows graphiti-core 0.29's `GroupsNodesNotFoundError` / `GroupsEdgesNotFoundError` (raised on empty partitions, which is the bootstrap case). Legacy `search_nodes`/`search_memory_facts` duck-type still recognised by the seam for backwards-compatible test mocks. Tests green.
- **Write API mismatch.** `async_write.py:_perform_write` called `add_episode(name=..., episode_body=..., group_ids=..., flush_id=...)` — graphiti-core 0.29 takes `group_id` (singular), and has no `flush_id` parameter. **Patched 2026-05-02:** new `_add_episode_kwargs(...)` helper at [src/study_tutor/knowledge/async_write.py](src/study_tutor/knowledge/async_write.py) builds the right kwargs (`source=EpisodeType.json`, `source_description=f"flush:{flush_id}:{name}"`, `reference_time=now()`, `group_id=group_ids[0]`). The flush-id audit string still rides into structured logs unchanged; the CC-13 single-call-site invariant is preserved (greppable; AST lint still passes).
- **Group-id format mismatch.** Documented under Drifted above; tracked here too because the same close-out commit migrated the live constants.

### Why the autobuild stayed green

Three interlocking reasons. None of them are individually wrong; together they were enough to mask the runtime gap for the entire Phase 1 sprint:

1. `tests/unit/knowledge/test_queries.py:_FakeInner` and `tests/unit/knowledge/test_async_write.py:FakeClient` duck-type the *intended* graphiti API, not the real one. The mock's `search_nodes(group_ids, query)` and `add_episode(*args, **kwargs)` look right against the spec but never run against `graphiti-core 0.29`'s actual surface.
2. `tests/integration/test_rag_end_to_end.py` covers RAG/quote-verifier integration — corpus loader, retrieval, verifier, coach handover — but does **not** boot a live `Graphiti` client. RAG and verifier are graphiti-independent.
3. There is no smoke test that imports `graphiti-core` and exercises a one-shot `add_episode` against a stubbed driver. Such a test would have caught the kwargs/group-id/LLM-wiring drift before Phase 1 closed.

---

## Changes-current-phase — what this gate forces in Phase 2

This section is the consumer-facing payload for `phase-2-build-plan.md` Day 1. The gate findings change Saturday 2 May's plan in three concrete ways.

1. **New leading task before FEAT-PH2-001: "Graphiti runtime integration repair."** Spec'd as `tasks/backlog/graphiti-runtime-integration-repair/` (new). Scope: wire Gemini LLM client + GB10 embedder + cross-encoder into `get_client(config)`, install whatever `graphiti-core[<extra>]` packages are needed for the Gemini client class, add a one-shot smoke test that boots a real Graphiti instance and round-trips a single `add_episode` + `EntityNode.get_by_group_ids` against a stub or live driver, then re-run `scripts/seed_student_model.py` and verify Lilymay baseline persists. Acceptance: G2 green (live), G3/G4/G5/G6 unblocked. **Estimated complexity 6/10, ~half a day with autobuild.** Lands ahead of FEAT-PH2-001's spec + plan because gamification reads the same `get_student_state` seam that G2 needs.
2. **FEAT-PH2-001 timing slips by the integration-repair duration.** The Phase-2 build plan §"Day 1" §Morning point 3 (`/feature-spec` + `/feature-plan` for FEAT-PH2-001) waits for the new leading task. If the repair lands Saturday morning, FEAT-PH2-001 spec + plan still ship Saturday afternoon and Wave 1 still ships Saturday evening — the original Day 1 plan compresses by ~2h but stays inside Saturday. If the repair slips into Sunday, FEAT-PH2-001 Wave 1 slips one day and the Reachy/dashboard track rolls in unchanged.
3. **Three close-out-repair patches already in flight, awaiting commit.** Read-API patch ([queries.py](src/study_tutor/knowledge/queries.py)), write-API patch ([async_write.py](src/study_tutor/knowledge/async_write.py)), group-id colon→dash migration ([student_model.py](src/study_tutor/knowledge/student_model.py) + 4 test files). Tests at 695/696. These should commit ahead of the integration-repair task — both because they're on the path to G2 and because they're standalone API-correctness wins regardless of the LLM-wiring decision.

---

## Status of the close-out gate checklist (`phase-2-build-plan.md §"Must be green by Friday 1 May evening"`)

Captured here for the audit trail; this is a snapshot of where the five items landed when the gate was actually run on Saturday 2 May:

| Gate | Status | Notes |
|---|---|---|
| FEAT-PH1-004 status decided | ✅ Path A (shipped) | Verifier at orchestrator.py:460-461; six-criterion rubric live; PRV-001..007 all in `tasks/completed/`; merge commit `6eb41a7`. |
| Lilymay seeded against Synology FalkorDB | ❌ Falsified | See G2 above. Three API drifts patched in-flight; LLM-wiring root cause defers to "Graphiti runtime integration repair" task. |
| End-to-end demo session via MCP run at least once | ❌ Falsified | See G6. Same root cause as G2. |
| Six parity surfaces SR-01..SR-07 still green; SR-08 + SR-09 honoured | ✅ Green | 695/696 tests; the one failure is a pre-existing dev-env mypy-on-system-Python issue, not a regression. SR-08 / SR-09 honoured at architecture + design layers (ADR-ARCH-018 / ADR-ARCH-019). |
| `phase-1-validation.md` seeded | ✅ Done (this file) | Slipped by one day relative to the build plan but landed ahead of FEAT-PH2-001 spec work. |

---

*Doc lives at `docs/research/ideas/phase-1-validation.md`. Revisit at the close of the "Graphiti runtime integration repair" task to flip the falsified G2/G3/G4/G5/G6 entries to held — at which point Phase 1 is structurally complete on its own terms, even though the close-out exercise crossed the calendar boundary.*
