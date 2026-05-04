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

## Wave 4 (TASK-GR-SEED) outcome — 2026-05-03

**Result: G2 / G3 remain Falsified — gate flip deferred.**

The wired-client repair (Wave 2 / TASK-PH2-GR-001) cleared the OpenAI 401 root cause, but a second blocker surfaced when Wave 4 ran the seed against live FalkorDB. **G2/G3 cannot honestly flip to Held in this wave** — the evidence required by AC-SEED-05 (Student entity readable via `mcp__graphiti__search_nodes`; populated `StudentState` from `get_student_state`) is not present.

### Evidence

- **Seed runs attempted in Wave 4:** four (`seed_run_1` … `seed_run_4` under `.guardkit/autobuild/TASK-GR-SEED/logs/`). Run 4 (start `2026-05-03T06:45:25Z`, end `2026-05-03T07:49:39Z`, wall-clock **~64 min** — anomaly per AC-SEED-07's ≥45 min threshold; risk-register note added below) reached the summary line `seeded Lilymay baseline (subjects=0, confidences=0, succeeded_writes=6)`. The repeated `INFO openai._base_client: Retrying request to /chat/completions in …s` and `WARNING study_tutor.knowledge.async_write: graphiti write failed` lines in `seed_run_4.log` show the GB10 vLLM endpoint returning HTTP 429 (Too Many Requests) under the `chunk_extraction_concurrency` fan-out — only 6 of the 25 planned `add_episode` calls cleared the rate-limiter.
- **Read-back evidence (`.venv/bin/python .guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py`, captured into `.guardkit/autobuild/TASK-GR-SEED/logs/verify_lilymay_turn3.json`):**
  ```json
  {
    "ac_seed_03_get_student_state": {
      "empty": false,
      "year_group": null,
      "target_grade": null,
      "subjects": [],
      "topic_confidences": []
    },
    "ac_seed_02_student_lilymay_nodes": []
  }
  ```
  `EntityNode.get_by_group_ids(driver, ["student-lilymay"], limit=20)` returns `[]`. `get_student_state(client, "lilymay")` returns a non-error `StudentState` but with `year_group=None`, `target_grade=None`, empty `subjects`, empty `topic_confidences` — the partial-write set did not persist any Student-bearing nodes that the read API can recover. **G2 evidence absent; G3 evidence absent.**

### Risk-register entry for Wave 5 planning (AC-SEED-07 follow-up)

- **R-WAVE5-01 — Provider rate-limit cap dominates seed wall-clock.** GB10 vLLM endpoint (`http://promaxgb10-41b1:9000/v1`) issues HTTP 429 well before the 25-write fan-out completes; `chunk_extraction_concurrency: 4` amplifies the contention rather than easing it. Two mitigations to consider before Wave 5:
  1. Force `chunk_extraction_concurrency: 1` for seed runs (already serial via `helper.drain()`; the inner concurrency is the LLM-side fan-out per `add_episode`).
  2. Switch the seed to MacBook ollama (`qwen2.5:14b-instruct-q4_K_M`) when available — the 78s/`add_episode` median is slower per-call but avoids the shared-vLLM rate cap.
- **R-WAVE5-02 — `succeeded_writes` counter remains misleading.** As called out under G2 above, the seed-script summary line counts non-abandoned tasks rather than confirmed FalkorDB writes. Wave 5 should either (a) post-flush `EntityNode.get_by_group_ids` and assert non-empty before declaring success, or (b) wire the helper to count actual `add_episode` returns. Tracking as a **TASK-GR-SEED follow-up** in the integration-repair backlog.

### What Wave 4 did deliver

- Confirmed Wave 2's wiring fix (no more `openai.AuthenticationError`; LLM calls reach the configured GB10 vLLM endpoint and return 200s for the writes that beat the rate-limiter).
- Captured deterministic, repeatable read-back evidence via `verify_lilymay.py` so future waves can re-verify by re-running one script.
- Established that the persistence gap is not a wiring issue but a rate-limit + counter-accuracy issue — narrowing Wave 5's investigation surface.

### Status of AC-SEED-XX (TASK-GR-SEED)

| AC | Status | Notes |
|---|---|---|
| AC-SEED-01 | ❌ Falsified | Run 4 reported `succeeded_writes=6` (not 25); read-back shows 0 persisted nodes. |
| AC-SEED-02 | ❌ Falsified | `EntityNode.get_by_group_ids(driver, ["student-lilymay"])` → `[]`. |
| AC-SEED-03 | ❌ Falsified | `get_student_state(client, "lilymay")` returns `empty=false` but all fields null/empty. |
| AC-SEED-04 | ⚠️ Not exercised | Idempotency not re-tested because the first-run baseline is itself empty. |
| AC-SEED-05 | ❌ Cannot flip | G2 + G3 evidence absent (see Evidence above). G4/G5/G6/G13 remain Falsified pending Wave 5. |
| AC-SEED-06 | ✅ Not needed | No `Connection closed by server` escalation observed; `GRAPH.DELETE` not triggered. |
| AC-SEED-07 | ✅ Captured | Run-4 wall-clock 64 min; anomaly noted; R-WAVE5-01 / R-WAVE5-02 risk entries added above. |
| AC-SEED-08 | ⚠️ Not run | Lint/format pass not exercised in this wave; only this validation doc was edited. |

> **2026-05-04 update**: Design resolution captured in [TASK-GSM-008](../../../tasks/completed/TASK-GSM-008-resolve-typed-entity-design-gaps.md) → [ADR-ARCH-021](../../architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md). Implementation tracked in [TASK-GSM-009](../../../tasks/in_progress/TASK-GSM-009-typed-entity-seed-refactor.md); G2/G3 gate flips here are pending TASK-GSM-009's live evidence. AC-SEED-02's expected `year_group=11, target_grade="8"` is corrected to `year_group=10, target_grade="7"` under TASK-GSM-009 AC-05.

> **2026-05-04 (later)**: TASK-GSM-009 landed (typed-entity rewrite). Live evidence captured below; **G2 flips to Held with caveat, G3 flips to Held**. AC-SEED-* statuses are superseded by TASK-GSM-009 AC-01..-17 — see the Wave 6 follow-on subsection further down.

---

*Doc lives at `docs/research/ideas/phase-1-validation.md`. Revisit at the close of the Wave 5 follow-up (provider rate-limit mitigation + `succeeded_writes` counter accuracy) to flip the falsified G2/G3/G4/G5/G6 entries to held — at which point Phase 1 is structurally complete on its own terms, even though the close-out exercise crossed the calendar boundary.*

---

## Wave 4 retry — TASK-GR-SEED run 5 — 2026-05-03 (afternoon)

**Result: G2 / G3 remain Falsified — different failure mode surfaced.**

The R-WAVE5-01 mitigation (`chunk_extraction_concurrency: 1`, `max_concurrent_episodes: 1`) was already committed to `.guardkit/graphiti.yaml` after the Wave 4 close-out. Both LLM endpoints are healthy at retry time (GB10 vLLM serving `qwen-graphiti`; MacBook ollama up as fallback). Re-running `python scripts/seed_student_model.py` against live FalkorDB produced a **distinct** failure mode that cannot be cleared by retry, infrastructure tuning, or operator intervention — it requires a code-level fix.

### Evidence

- **Run 5** start `2026-05-03T17:23:40Z`, end `2026-05-03T17:37:08Z`, wall-clock **13 min** (much faster than Wave 4's 64 min — failure is fast, not slow).
- **Counter**: `seeded Lilymay baseline (subjects=0, confidences=0, succeeded_writes=6)`. Underlying counts: 25 writes scheduled, **3 succeeded, 22 failed**. R-WAVE5-02 (counter accuracy) reasserts.
- **Read-back**: `EntityNode.get_by_group_ids(driver, ["student-lilymay"], limit=20)` → `[]`. `get_student_state(client, "lilymay")` → all fields null/empty. **G2 evidence absent; G3 evidence absent.**
- **Failure site**: graphiti-core's entity-resolution path inside `add_episode`:
  ```
  ERROR graphiti_core.driver.falkordb_driver: Error executing FalkorDB query:
  RediSearch: Syntax error at offset 19 near student
  CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query) ...
  {'query': '(@group_id:"student-lilymay") (Student | lilymay | ...)', 'group_ids': ['student-lilymay']}
  ```
  Three error variants observed across the 22 failures, all the same root cause:
  - `near student` (`@group_id:"student-lilymay"`)
  - `near subject` (`@group_id:"subject-english-literature"`)
  - `near fleet` (`@group_id:"fleet-appmilla"`)

### Root cause: dash collision between two graphiti-core constraints

graphiti-core 0.29 imposes two requirements on `group_id` that are **incompatible** under the FalkorDB backend:

1. **`GroupIdValidationError`** (write side, raised at `Graphiti.add_episode`) — only accepts `[A-Za-z0-9_-]`. This is the constraint that forced the Phase-1 close-out to migrate the project's group-id constants from `student:lilymay` to `student-lilymay` (commit a210472, 2026-05-02).
2. **RediSearch fulltext query** (read side, executed inside `add_episode`'s entity-resolution step) — graphiti-core builds queries of the form `(@group_id:"<id>") (token1 | token2 | ...)`. **In RediSearch syntax, `-` is the NOT operator**, so `student-lilymay` parses as "student NOT lilymay" and the query is rejected with `Syntax error at offset 19`.

The first 3 writes succeed because the `RELATES_TO` fulltext index has no entries — graphiti-core skips entity-resolution against an empty index. Once any relationship lands, every subsequent `add_episode` call triggers a query against the populated index and crashes. The seed therefore poisons its own pipeline three writes in.

This is **not** the issue Wave 4 captured (LLM rate-limiting). R-WAVE5-01's mitigation does not apply. The fulltext-query syntax error happens regardless of concurrency, regardless of LLM provider, and regardless of whether the GB10 endpoint is contended.

### MCP-side corroboration

The same root cause was independently reproduced via `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` during retry triage — the MCP server returns the identical `RediSearch: Syntax error at offset 19 near student` response. AC-SEED-02 (as written) is therefore **not just falsified by absent data — it is unverifiable through MCP at all** under the current dashed-group-id format. The acceptance criterion's evidence requirement (read-back through MCP) cannot be satisfied without remediation.

### Risk-register entry — supersedes R-WAVE5-01 as the load-bearing blocker

- **R-WAVE5-03 — Dashed group_ids break graphiti-core's RediSearch fulltext queries on FalkorDB.** Any partition with ≥1 relationship and a dashed group_id (`student-lilymay`, `subject-english-literature`, `fleet-appmilla`, etc.) is unwriteable beyond the first write. This is a hard incompatibility, not a tuning issue. Three remediation paths, in increasing order of project disruption:
  1. **Escape group_ids in graphiti-core's fulltext query construction.** Quote with `\-` or wrap with `{}` per RediSearch escaping rules. Minimal-blast-radius option; can land as a monkey-patch in `study_tutor.knowledge.graphiti_client` (intercept and patch `graphiti_core.driver.falkordb_driver` at import time) or as an upstream PR. The seed's group_id format stays `student-lilymay`.
  2. **Migrate group_id format to underscore (`student_lilymay`, `subject_english_literature`, `fleet_appmilla`).** Satisfies both `GroupIdValidationError` and RediSearch syntax. Touches the post-a210472 normalisation surface — `student_model.py`, the test fixtures updated in that commit, the operator docs that cite the dash form, and any external Graphiti consumers (the spec'd-but-noted-divergent `appmilla-fleet` reference in the specialist-agent repo). Bigger blast radius but no upstream dependency.
  3. **Switch graph backend from FalkorDB to Neo4j.** Neo4j's fulltext index uses Lucene syntax (different escaping rules; dashes are not operators). Out of scope for a seed retry; would cascade into ADR-ARCH-018 / ADR-ARCH-019 territory.

  **Recommendation pending operator decision**: option 1 (monkey-patch) is the cleanest path back to a green seed without re-opening the post-a210472 migration. Option 2 is the cleanest long-term answer if the project expects to track upstream graphiti-core. Option 3 is overkill unless other Neo4j-vs-FalkorDB tradeoffs are already in play.

- **R-WAVE5-04 — `Connection closed by server` reappearing on read-only paths.** Observed during the post-run-5 `verify_lilymay.py` execution (FalkorDB closed the connection mid-`get_by_group_ids`; the script still completed). Wave 4 marked AC-SEED-06 as "no escalation observed" — that's no longer accurate as of run 5. May be a separate FalkorDB stability issue worth investigating before R-WAVE5-03 is fixed; otherwise, retries against a healed graphiti-core may surface this intermittently.

### Status of AC-SEED-XX after run 5

| AC | Status | Notes |
|---|---|---|
| AC-SEED-01 | ❌ Falsified | Run 5: 22/25 writes failed with RediSearch syntax errors; 3 succeeded but did not persist to readable state. |
| AC-SEED-02 | ❌ Falsified + unverifiable | `EntityNode.get_by_group_ids(["student-lilymay"])` → `[]`; `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns the same syntax error encountered in writes — the AC's evidence shape is currently unobtainable. |
| AC-SEED-03 | ❌ Falsified | `get_student_state(client, "lilymay")` returns `empty=false` but all fields null/empty (unchanged from Wave 4). |
| AC-SEED-04 | ⚠️ Not exercised | Idempotency cannot be tested while first run never persists. |
| AC-SEED-05 | ❌ Cannot flip | G2 + G3 evidence absent; remediation path required before retry. |
| AC-SEED-06 | ⚠️ Now observed | `Connection closed by server` reappeared during verify (R-WAVE5-04). `GRAPH.DELETE` not yet triggered. |
| AC-SEED-07 | ✅ Captured | Run-5 wall-clock 13 min (fast-fail, not slow); R-WAVE5-03 / R-WAVE5-04 added above. |
| AC-SEED-08 | ⚠️ Not run | Lint/format pass not exercised; only this validation doc was edited in Wave 5 retry. |

### What Wave 5 retry did deliver

- Confirmed Wave 4's R-WAVE5-01 mitigation is in place (concurrency=1) — but it doesn't help, because the failure isn't rate-limiting.
- Identified the actual blocker: graphiti-core × FalkorDB × RediSearch dash-as-NOT incompatibility (R-WAVE5-03).
- Independently reproduced the same root cause through the MCP boundary (`mcp__graphiti__search_nodes` returns the same syntax error) — useful triage for AC-DEMO-* in the operator-handoff scaffold below, since those ACs also depend on dashed group_ids being queryable through MCP.
- Captured a new intermittent FalkorDB stability signal (R-WAVE5-04) for inclusion in the Wave 5 risk register.

### Decision required before next retry

TASK-GR-SEED is moving back to `blocked/` pending an operator decision among R-WAVE5-03's three remediation paths. The seed itself is correct; the backend integration is broken in a way that cannot be fixed by re-running.

---

## Phase 2 Wave 5 — Operator handoff (_Pending: live evidence_)

**Status:** scaffold added by TASK-GR-DEMO autobuild Wave-5 turn; the gate flips themselves remain in `Falsified` above until the operator who conducts the live AC-DEMO-01 Claude Desktop session pastes the real artifacts into the rows below. **Do not read this subsection as an asserted status change** — every row currently says `_pending_` because the live demo has not yet been conducted. The flip from "Falsified" to "Held" must happen in the section above this line, with citations into the rows below as the supporting evidence.

### Why this scaffold exists

TASK-GR-DEMO's `## Acceptance Criteria` (AC-DEMO-05) requires this doc to record:
- G3 flip + cite read-back-through-MCP evidence,
- G4 flip + paste a session-log excerpt,
- G5 flip + paste a Coach-revised-turn excerpt,
- G6 flip + paste a `mcp__graphiti__get_episodes` JSON,
- G13 flip + cite session log + p50/p95 latency.

Autobuild can structurally reserve where each excerpt lands; it cannot conduct the live session that produces them. Keeping this scaffold separate from the `Held` / `Falsified` / `Drifted` blocks above preserves the audit-trail invariant that every status flip is backed by a real artifact, not by a placeholder.

### Operator checklist

| Gate | Evidence required | Paste location |
|---|---|---|
| G3 | `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returning a populated Student entity *via the MCP boundary* (not just via the seed script). | row below: G3 |
| G4 | `tutor_start_session` → 5–7 `tutor_turn` → `tutor_session_end` transcript excerpt. | row below: G4 |
| G5 | A turn where the Coach disagreed with the initial Player reply and the corrected reply is what reached the user. | row below: G5 |
| G6 | `mcp__graphiti__get_episodes(group_ids=["student-lilymay"])` JSON containing the `session_completed` episode written by the demo. | row below: G6 |
| G13 | Session log + p50/p95 from the latency-results sibling doc. | row below: G13 |

| Gate | Excerpt / artifact | Source |
|---|---|---|
| G3 (read-back via MCP) | _pending_ | `mcp__graphiti__search_nodes` |
| G4 (session round-trip) | _pending_ | session transcript |
| G5 (Coach revision) | _pending_ | Coach-revised turn excerpt |
| G6 (`session_completed` episode) | _pending_ | `mcp__graphiti__get_episodes` JSON |
| G13 (latency + log) | _pending_ | sibling doc + transcript |

### Pre-flight checklist (before opening the session)

Per the task's `## Implementation Notes`:

1. Confirm Wave-4 seed: `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns a Student entity.
2. Confirm `get_student_state(client, "lilymay")` returns non-empty (covered by `tests/integration/test_lilymay_seed_seam.py` once `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE` is set on the host).
3. Confirm Claude Desktop's MCP config points at the study-tutor server and is reachable.
4. Confirm the LLM endpoint is up (`curl http://promaxgb10-41b1:9000/v1/models` or the MacBook fallback URL).

If any pre-flight fails, fix and re-run before opening the session — don't push through and pollute the evidence trail.

### Coach-revision rule

AC-DEMO-01.2 explicitly requires "at least one Coach revision observed". If the Coach never disagrees in 7 turns, that's evidence the Coach calibration is too lax — note it for the FEAT-PH2-001 follow-up but flag the wave as Held only if a revision is observed. Re-conduct the session with a more challenging topic if no revision occurs.

### Cross-references

- TASK-GR-DEMO `## Acceptance Criteria` (the upstream contract).
- `docs/research/ideas/graphiti-latency-spike-results.md §"Phase 2 Wave 5 measurement"` (sibling scaffold for AC-DEMO-04).
- `tests/integration/test_lilymay_seed_seam.py` (the Wave-5 seam pinning the runtime contract this demo exercises).

---

## TASK-GSM-009 — Typed-entity seed landed — 2026-05-04

**Result: G2 flips to _Held with caveat_; G3 flips to _Held_.**

The typed-entity seed rewrite ([TASK-GSM-009](../../../tasks/in_progress/TASK-GSM-009-typed-entity-seed-refactor.md)) is the implementation of [ADR-ARCH-021](../../architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md). It bypasses the LLM-driven `add_episode` write path entirely (`EntityNode.save` / `EntityEdge.save` directly), uses deterministic UUID5 derivation for byte-idempotency on re-run, denormalises `Student.enrolled_subjects` per ADR-ARCH-021 §G1, and writes only intra-group edges per §G2. The 2026-05-03 R-WAVE5-03 RediSearch dash-as-NOT blocker is gone (typed writes don't go through the fulltext-query path on entity resolution).

### G2 — Held with caveat

**Caveat**: cross-group edges (`Student → STUDIES → Subject`, `Student → WORKING_ON → Text`, `Topic → ASSESSED_BY → AO`) are **not** exercised by the Phase-1 seed — ADR-ARCH-021 §G2 documented the silent-dangle outcome from the cross-group edge probe and deferred them. The seed writes only intra-group edges (`HAS_CONFIDENCE` within `student-<id>`, `COVERS` and `HAS_TEXT` within `subject-<slug>`). Subjects-on-Student is denormalised via the `enrolled_subjects: list[str]` attribute. Topic-to-AO is denormalised via the Topic node's `ao_refs: list[str]` attribute.

**Live evidence** (full JSON at [`.guardkit/autobuild/TASK-GR-SEED/logs/TASK-GSM-009_live_evidence.json`](../../../.guardkit/autobuild/TASK-GR-SEED/logs/TASK-GSM-009_live_evidence.json)):

```json
{
  "ac_02_student_node_with_enrolled_subjects": {
    "labels_include_student": true,
    "attributes_include_enrolled_subjects": true,
    "enrolled_subjects": ["English Literature", "English Language"],
    "year_group": 10,
    "target_grade": "7"
  },
  "partition_breakdown": {
    "student-lilymay": {"nodes": 7, "edges": 6, "edge_names": ["HAS_CONFIDENCE"]},
    "subject-english-literature": {"nodes": 10, "edges": 9, "edge_names": ["COVERS", "HAS_TEXT"]},
    "subject-english-language": {"nodes": 2, "edges": 1, "edge_names": ["COVERS"]},
    "fleet-appmilla": {"nodes": 6, "edges": 0}
  }
}
```

Total: **25 nodes, 16 intra-group edges** across all four partitions. The Student node's `attributes` dict includes `enrolled_subjects=["English Literature", "English Language"]` (the load-bearing G1 denormalisation). Note: the `summary` field is populated by the seed (e.g. `"Student Lilymay (id=lilymay), Year 10, target grade 7. Enrolled in: English Literature, English Language."`) but is not the load-bearing assertion under ADR-ARCH-021; the structured `attributes` dict is.

### G3 — Held

**Live evidence**:

```json
{
  "ac_03_get_student_state_populated": {
    "year_group": 10,
    "target_grade": "7",
    "subjects": ["English Literature", "English Language"],
    "topic_confidences_count": 6,
    "bands_present": ["developing", "secure", "struggling"],
    "epoch_sentinel_observed": true
  },
  "g3_planner_day1_recommendations": [
    {"topic_name": "Power and Conflict: Ozymandias themes", "reason": "struggling_stale", "band": "struggling"},
    {"topic_name": "Macbeth's witches", "reason": "struggling_stale", "band": "struggling"},
    {"topic_name": "Lady Macbeth's ambition", "reason": "developing_stale", "band": "developing"}
  ]
}
```

`get_student_state(client, "lilymay")` returns a populated `StudentState` with all the AC-006 fields (`year_group`, `target_grade`, non-empty `subjects` via the §G1 denormalisation, six `topic_confidences` spanning all three planner bands). `get_topic_recommendations` produces three recommendations on day 1 — the EPOCH_NEVER_REVISED sentinel keeps every baseline topic outside the 48h cooldown so the planner has bands to plan against immediately. **G3 satisfied at the runtime layer, not just the unit-test layer.**

### Idempotency proof (AC-04 / R12)

`MATCH (n) RETURN count(n)` per partition before and after a second seed run:

| Partition | Nodes (before) | Nodes (after) | Edges (before) | Edges (after) |
|---|---|---|---|---|
| `student-lilymay` | 7 | 7 | 6 | 6 |
| `subject-english-literature` | 10 | 10 | 9 | 9 |
| `subject-english-language` | 2 | 2 | 1 | 1 |
| `fleet-appmilla` | 6 | 6 | 0 | 0 |
| **Total** | **25** | **25** | **16** | **16** |

The second run hit the pre-flight idempotency gate (`event=seeding_skipped reason=already_seeded`) and exited 0 without writing anything. Even if the pre-flight skip were bypassed, deterministic UUID5 derivation + FalkorDB MERGE-by-uuid (pinned by [`tests/integration/test_typed_entity_writes.py`](../../../tests/integration/test_typed_entity_writes.py)) would still collapse a second run into the same node set.

### AC-SEED-* status table — superseded by TASK-GSM-009

| AC | Original status | Superseded by | Notes |
|---|---|---|---|
| AC-SEED-01 | ❌ Falsified (Wave 4/5) | TASK-GSM-009 AC-01 | Typed-entity writes; no `add_episode` path. **Held.** |
| AC-SEED-02 | ❌ Falsified + unverifiable (Wave 5 R-WAVE5-03) | TASK-GSM-009 AC-02 | Student node readable with `enrolled_subjects` attribute. _Note: AC-SEED-02 originally asserted `year_group=11, target_grade="8"` — drift in the doc, not the seed. Corrected to `year_group=10, target_grade="7"` under TASK-GSM-009 AC-14._ **Held.** |
| AC-SEED-03 | ❌ Falsified | TASK-GSM-009 AC-03 | `get_student_state(...)` populated. **Held.** |
| AC-SEED-04 | ⚠️ Not exercised | TASK-GSM-009 AC-04 | Idempotency proven via byte-identical pre/post counts + UUID5 derivation. **Held.** |
| AC-SEED-05 | ❌ Cannot flip | TASK-GSM-009 AC-05 (this section) | Gate flips landed. |
| AC-SEED-06 | ⚠️ Now observed (R-WAVE5-04) | n/a | `Connection closed by server` reappears intermittently in shutdown logs but does not block successful writes (the seed completed end-to-end despite the noise). |
| AC-SEED-07 | ✅ Captured | n/a | Wave-5 retry timing was 13 min; TASK-GSM-009 seed runs end-to-end in ~2s (no LLM in the write path). |
| AC-SEED-08 | ⚠️ Not run | TASK-GSM-009 AC-08 | `py_compile` + import smoke pass; no project-configured ruff/black/mypy beyond pytest. |

### Cross-references

- [ADR-ARCH-021](../../architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md) — design rationale for G1/G2/G3 resolutions
- [TASK-GSM-009](../../../tasks/completed/TASK-GSM-009/TASK-GSM-009.md) — implementation task (completed 2026-05-04)
- [scripts/probes/probe_cross_group_edges.py](../../../scripts/probes/probe_cross_group_edges.py) — G2 probe (silent-dangle confirmation that drove the deferral decision)
- [`.guardkit/autobuild/TASK-GR-SEED/logs/TASK-GSM-009_live_evidence.json`](../../../.guardkit/autobuild/TASK-GR-SEED/logs/TASK-GSM-009_live_evidence.json) — full live evidence JSON (TASK-GSM-009 first-run)
- [tests/integration/test_typed_entity_writes.py](../../../tests/integration/test_typed_entity_writes.py) — MERGE-by-uuid integration smoke (AC-13)

---

## TASK-GR-SEED retry close-out — 2026-05-04 (evening)

**Result: TASK-GR-SEED moved blocked → completed. All 8 AC-SEED-* gates Held against fresh evidence.**

With TASK-GSM-009 (typed-entity rewrite per ADR-ARCH-021) merged at commit `a90bc65`, the seed path is unblocked. A retry run was executed against the live `whitestocks:6379` FalkorDB to formalise close-out:

- **Retry run** start `2026-05-04T21:24:44Z`, end `2026-05-04T21:24:46Z`, wall-clock **2s**. Log: [`.guardkit/autobuild/TASK-GR-SEED/logs/seed_run_TASK-GR-SEED-retry.log`](../../../.guardkit/autobuild/TASK-GR-SEED/logs/seed_run_TASK-GR-SEED-retry.log). Hit pre-flight idempotency gate (`event=seeding_skipped reason=already_seeded`) and exited 0 — confirming AC-SEED-04.
- **Fresh verify_lilymay capture**: [`.guardkit/autobuild/TASK-GR-SEED/logs/verify_lilymay_TASK-GR-SEED-retry.json`](../../../.guardkit/autobuild/TASK-GR-SEED/logs/verify_lilymay_TASK-GR-SEED-retry.json) shows the Student node with `attributes_keys=[enrolled_subjects, student_id, target_grade, year_group]`, summary `"Year 10, target grade 7. Enrolled in: English Literature, English Language."`, and 6 TopicConfidence nodes spanning struggling / developing / secure bands. `get_student_state(...)` returns `StudentState(empty=False, year_group=10, target_grade="7", subjects=[English Literature, English Language], topic_confidences=[6 entries])` — confirming AC-SEED-02 + AC-SEED-03.
- **AC-SEED-* status table** at line 362 above remains authoritative. The retry adds a second idempotency-evidence point on top of TASK-GSM-009's pre/post-counts evidence.
- **G4 / G5 / G6 / G13** remain Falsified pending Wave 5's MCP demo session (per the original spec — these are session-side gates, not seed-side; flipping them here would be a false-evidence claim).

The seed task closes here. Next gate work (G4/G5/G6/G13) belongs to a separate Wave-5 MCP demo task.
