
/arch-refine \
  --target docs/architecture/domain-model.md \
  --context docs/design/README.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context docs/research/ideas/phase-1-scope.md

I need to first understand the project state — /arch-refine normally takes a natural language query and targets specific ADRs, but you've passed a --target flag pointing at a domain model document. Let me check what exists before I do anything destructive.

Bash Inspect target and context directories
IN
ls -la docs/architecture/ docs/design/ docs/research/ideas/ 2>&1 | head -100

OUT
docs/architecture/:
total 128
drwxr-xr-x   8 richardwoollcott  staff    256 Apr 19 13:48 .
drwxr-xr-x  13 richardwoollcott  staff    416 Apr 27 07:12 ..
-rw-r--r--   1 richardwoollcott  staff  11070 Apr 18 23:28 ARCHITECTURE.md
-rw-r--r--@  1 richardwoollcott  staff  12138 Apr 19 13:48 assumptions.yaml
-rw-r--r--   1 richardwoollcott  staff   6763 Apr 18 23:31 container.md
drwxr-xr-x  18 richardwoollcott  staff    576 Apr 19 13:27 decisions
-rw-r--r--   1 richardwoollcott  staff  20481 Apr 18 23:30 domain-model.md
-rw-r--r--   1 richardwoollcott  staff   4750 Apr 18 23:31 system-context.md

docs/design/:
total 48
drwxr-xr-x   7 richardwoollcott  staff   224 Apr 26 11:19 .
drwxr-xr-x  13 richardwoollcott  staff   416 Apr 27 07:12 ..
drwxr-xr-x   5 richardwoollcott  staff   160 Apr 26 11:14 contracts
-rw-r--r--   1 richardwoollcott  staff  6972 Apr 26 11:18 events-schema.yaml
-rw-r--r--   1 richardwoollcott  staff  5821 Apr 26 11:17 mcp-tools.json
drwxr-xr-x   5 richardwoollcott  staff   160 Apr 26 11:16 models
-rw-r--r--   1 richardwoollcott  staff  6476 Apr 26 11:19 README.md

docs/research/ideas/:
total 880
drwxr-xr-x  21 richardwoollcott  staff    672 Apr 26 11:11 .
drwxr-xr-x   4 richardwoollcott  staff    128 Apr 18 11:33 ..
-rw-r--r--@  1 richardwoollcott  staff  25627 Apr 12 19:10 copyright-training-data-analysis.md
-rw-r--r--@  1 richardwoollcott  staff  15479 Apr 24 06:57 cross-repo-rag-impact-analysis-2026-04-24.md
-rw-r--r--@  1 richardwoollcott  staff  17753 Apr 19 13:28 decisions-log-2026-04-17.md
-rw-r--r--@  1 richardwoollcott  staff  12634 Apr 12 19:10 deepagents-patterns-review.md
-rw-r--r--@  1 richardwoollcott  staff   7089 Apr 19 10:29 fleet-v3-future-work-notes.md
-rw-r--r--@  1 richardwoollcott  staff  11425 Apr 12 19:11 GCSE_English_AI_Tutor_Proposal.md
-rw-r--r--@  1 richardwoollcott  staff   5347 Apr 14 16:05 GCSE_Gamification_Research.md
-rw-r--r--@  1 richardwoollcott  staff  25432 Apr 12 19:10 gemma4-hackathon-submission-plan.md
-rw-r--r--   1 richardwoollcott  staff  21960 Apr 23 14:01 openwebui-rag-empirical-findings-2026-04-23.md
-rw-r--r--   1 richardwoollcott  staff  43051 Apr 26 11:11 phase-0-build-plan.md
-rw-r--r--@  1 richardwoollcott  staff  28200 Apr 18 08:55 phase-0-scope.md
-rw-r--r--   1 richardwoollcott  staff  33171 Apr 23 17:30 phase-1-build-plan.md
-rw-r--r--   1 richardwoollcott  staff  34931 Apr 23 17:28 phase-1-scope.md
-rw-r--r--@  1 richardwoollcott  staff  20849 Apr 18 09:17 phase-2-scope.md
-rw-r--r--@  1 richardwoollcott  staff  14913 Apr 18 09:07 planning-cadence-hybrid-approach.md
-rw-r--r--@  1 richardwoollcott  staff  14303 Apr 17 21:44 po-extract-roadmap-1862adb2.md
-rw-r--r--@  1 richardwoollcott  staff  12821 Apr 21 14:55 rag-grounding-design.md
-rw-r--r--@  1 richardwoollcott  staff  23824 Apr 18 12:14 reachy-integration-conversation-starter.md
-rw-r--r--@  1 richardwoollcott  staff  37294 Apr 17 23:52 state-of-the-project-and-phase-recommendation.md
Bash Check Graphiti availability
IN
ls .guardkit/ 2>&1; echo "---"; cat .guardkit/graphiti.yaml 2>&1 | head -30

OUT
archive
graphiti-query-log.jsonl
graphiti.yaml
---
project_id: study-tutor
enabled: true
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0
max_concurrent_episodes: 3
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic
# --- Fallback: MacBook Pro M2 Max (Ollama, Q4_K_M) — uncomment if GB10 offline ---
#llm_provider: ollama
#llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
#llm_model: qwen2.5:14b-instruct-q4_K_M
llm_max_tokens: 4096
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
# Embedding dimension is resolved from KNOWN_EMBEDDING_DIMS
# based on embedding_model above. Set explicitly only to override
# (e.g., for Matryoshka truncation).
group_ids:
- product_knowledge
- command_workflows
- architecture_decisions
host: localhost
port: 8000
Bash List ADRs if present
IN
ls docs/architecture/decisions/ 2>&1

OUT
ADR-ARCH-001-ddd-structural-pattern.md
ADR-ARCH-002-three-layer-architecture.md
ADR-ARCH-003-async-graphiti-writeback.md
ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
ADR-ARCH-005-defer-dockerfile-to-phase-1.md
ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
ADR-ARCH-007-graphiti-split-topology.md
ADR-ARCH-008-mcp-only-agent-access.md
ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
ADR-ARCH-010-pydantic-at-boundary-validation.md
ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
ADR-ARCH-013-middleware-level-gamification-engine-future.md
ADR-ARCH-014-single-user-scalability-posture.md
ADR-ARCH-015-uk-on-device-data-residency.md
ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
The project has 16 existing ADRs, a domain model, and Graphiti is enabled. The invocation is unusual — /arch-refine doesn't have a --target flag in its documented syntax (it expects a natural language query or --adr=ADR-ARCH-NNN). Let me read the target and context files to understand what you're trying to refine.

Read domain-model.md
Read README.md
This is now clear: the design/README.md § 7.4 explicitly flagged a follow-up /arch-refine to fix domain-model.md §7.1 SR-07 wording — tutor_start_session is currently classified as long-running in the domain model but design D2 reclassified it to sync. Let me check the relevant ADR and context files before deciding the refinement scope.

Read ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
Bash Find SR-07 / classification references in build plan
IN
grep -n "tutor_start_session\|long-running\|SR-07\|punch-list\|punch list" docs/research/ideas/phase-0-build-plan.md | head -40

OUT
39:**Open punch-list to close Phase 0:**
51:   - **D2 — `tutor_start_session` classified `sync`.** The design artefact classifies `tutor_start_session` as **sync** (returns `session_id` synchronously; warm-up LLM call is opportunistic fire-and-forget, not a polled long-running task) — overriding the architecture text's "long-running" wording in `domain-model.md §7.1` and `phase-0-scope.md §SR-07`. Rationale: matches live behaviour in `src/study_tutor/mcp/adapter.py:49–68`; there is no still-running task to poll via `tutor_session_status`. The architecture text needs a follow-up `/arch-refine` to re-state SR-07 (or reclassify back to long-running if P1 adds Graphiti reads at session start that exceed 1s).
76:2. Six parity surfaces SR-01 through SR-07 all green
105:| **SR-01 to SR-07** | Structural requirements — six parity surfaces | — | baked into every feature | all |
199:6. **Implement `src/study_tutor/mcp/adapter.py` at minimal shape.** Four tools registered per scope-doc SR-07 classification. `tutor_start_session` returns session_id immediately; `tutor_turn` is synchronous; status + end are trivial.
218:11. **Restart Claude Desktop, verify green.** Expect a `study-tutor` server in the MCP list, 4 tools registered (`tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end`).
220:12. **First real invocation.** From a Claude Desktop chat: "Use tutor_start_session with subject English Literature, topic Macbeth." Then "Use tutor_turn to ask about the significance of the witches in Act 1 Scene 1." Expect a response from the fine-tuned model.
246:7. **SR-07 (tool description ≡ behaviour).** Read the four MCP tool descriptions. Verify each says "sync" / "long-running" explicitly, and the handler behaviour matches. Specifically: `tutor_start_session` description says "long-running, returns session_id immediately"; implementation returns session_id in ≤1s.
Bash Find SR-07 / classification references in phase-1 scope
IN
grep -n "tutor_start_session\|long-running\|SR-07" docs/research/ideas/phase-1-scope.md | head -40

OUT
40:The seven structural requirements from Phase 0 (SR-01 through SR-07) remain load-bearing. Every Phase 1 feature maintains them. The Graphiti latency spike adds one new structural consideration — **SR-08: Graphiti write-back is asynchronous from the caller's perspective** — which is notionally deferred work but is decided early in Phase 1 based on measurement.
48:**Acceptance.** `tutor_session_end` returns within 2 seconds regardless of Graphiti write latency. Graphiti write failures are logged but do not surface to the MCP caller. Subsequent `tutor_start_session` calls tolerate a not-yet-written previous session by treating it as absent rather than erroring.
84:- If search_nodes median > 3s: `tutor_start_session` stays long-running (Phase 0 classification holds)
85:- If search_nodes median < 1s: `tutor_start_session` could be reclassified as sync, simplifying the MCP tool shape
138:Seeding script: `scripts/seed_student_model.py`. Read by `tutor_start_session` is read-only; seeding is a separate concern.
155:**Problem.** Phase 0's `tutor_start_session` takes a topic from the caller's arguments — it's externally-chosen. The whole adaptive-tutoring story requires the tutor to propose topics based on student state. Without a planner, Graphiti persistence is data that doesn't influence behaviour.
179:#### 2. Planner integration with `tutor_start_session`
335:- **The six parity surfaces from LES1 remain load-bearing.** SR-01 through SR-07 apply to every Phase 1 change. New code can not regress them.
367:7. **Six parity surfaces still green.** SR-01 through SR-07 pass their acceptance criteria against Phase 1 code.
Before I edit anything, I need to flag an issue with the invocation. The --target docs/architecture/domain-model.md flag isn't part of the documented /arch-refine syntax — /arch-refine is designed to supersede a specific ADR (by ID or natural-language match) and then stale-flag downstream artefacts like the domain model.

Looking at the actual scope of this refinement, the "long-running" classification of tutor_start_session only lives in:

docs/architecture/domain-model.md:336 §7.1 table
docs/research/ideas/phase-0-scope.md §SR-07 (per the build-plan punch-list)
It's not in any ADR — ADR-ARCH-009 defines SR-07 as the generic "tool description ≡ behaviour" rule but doesn't hardcode the classification. So there's no ADR to supersede in the conventional /arch-refine sense.

A complication from docs/research/ideas/phase-1-scope.md:84-85: the classification may flip back to long-running in P1 depending on the Graphiti latency spike result.

Three plausible interpretations of what you want:

Option A — Domain-model edit only (matches design README §7.4 literally)
Directly edit domain-model.md:336 §7.1: reclassify tutor_start_session from long-running → sync, with a footnote that P1 may reclassify pending the Graphiti latency spike. Also tighten phase-0-scope.md §SR-07. No new ADR, no superseding. Fastest, lowest ceremony.

Option B — New ADR-ARCH-017 capturing the SR-07 per-tool classification
Create a new ADR that records "SR-07 per-tool classification table for Phase 0", including the sync decision for tutor_start_session and the P1 reversion condition. Then update domain-model.md §7.1 to reference it. Gives future refinements a proper target.

Option C — Refine ADR-ARCH-009 (add per-tool classification subsection)
Treat ADR-ARCH-009 as the SR-07 owner and supersede it with ADR-ARCH-017 that adds an explicit per-tool classification table. Heavyweight — supersedes a still-correct generic decision just to add specifics.

My recommendation is Option A — it's what the design README §7.4 literally asked for, and the SR-07 classification is implementation-detail-level, not architecturally load-bearing in the way ADRs are. The P1 conditional reversion is already captured in phase-1-scope.md.

Which would you like? (A / B / C, or describe something different)

command-history.md
option A - the idea is to clear these open questions: Two open design decisions (2026-04-26) that need ADR follow-through:

D1 — TutorSession is P0-only shape; P1 fields deferred → no ADR yet, fits within architecture envelope
D2 — tutor_start_session reclassified long-running → sync; needs /arch-refine on domain-model.md §7.1 and phase-0-scope.md §SR-07
Got it — Option A on D2 only. D1 is already settled in the design README as a P0/P1 phasing note within the architecture envelope, no domain-model edit required for that one.

Let me read the current SR-07 wording in phase-0-scope.md so I can match the tone, and the live adapter to cite as ground truth.

Bash Find SR-07 references in phase-0-scope
IN
grep -n "SR-07\|tutor_start_session\|long-running\|long running" docs/research/ideas/phase-0-scope.md | head -30

OUT
80:#### SR-07: Tool description ≡ implementation contract
82:**Requirement.** Every MCP tool's description field matches its implementation behaviour. If a tool description says "long-running — session tracked", the handler returns a session_id immediately and exposes a `_status`/`_cancel` companion tool. If a tool description does not say long-running, the handler completes synchronously within 30 seconds.
84:**Evidence from LES1.** TASK-MDF-POLR — `po_idea` description said "long-running" but handler awaited synchronously, producing a 4-minute timeout on Claude Desktop's 240-second MCP limit.
86:**Acceptance.** Every MCP tool in Phase 0 classified as either "sync" (< 30s bound) or "long-running" (returns session_id immediately, poll via companion). No tool in the undefined middle.
92:| `tutor_start_session` | long-running (session_id returned, poll via `tutor_session_status`) | Includes Graphiti read of student model (three-hop: MacBook → Synology → Gemini → GB10 embeddings); could exceed 10s |
97:If Phase 1 spike shows `tutor_start_session` consistently < 10s end-to-end, reclassify as sync. If `tutor_turn` exceeds 30s due to session-accumulated context, reclassify as long-running.
167:`src/study_tutor/mcp/adapter.py` exposing four MCP tools per SR-07 classification:
168:- `tutor_start_session` (long-running, returns session_id)
296:- **The six parity surfaces from LES1 are load-bearing.** No feature skips SR-01 through SR-07.
314:2. **Six parity surfaces green.** SR-01 through SR-07 all pass their acceptance criteria. Stream-split stdio test passes. Provider resolution via env var verified for at least two providers. `.env.example` contains no real-looking values. Every MCP tool's description matches its behaviour.
329:- **Session planner** (FEAT-PO-005 roadmap) reads from Graphiti (Phase 1) and writes back the planned session into the `tutor_start_session` handler created in Phase 0 FEAT-PO-002.
Bash Locate live adapter implementation
IN
sed -n '40,80p' src/study_tutor/mcp/adapter.py 2>/dev/null || find src -name 'adapter.py' -path '*mcp*' -exec ls -la {} \;

OUT
        role_config: RoleConfig,
        store: SessionStore | None = None,
    ) -> None:
        self._role = role_config
        self._store = store or get_default_store()
        self._player_prompt = role_config.load_player_prompt()
        # Track warm-up task so pytest/GC don't complain about orphans.
        self._warmup_tasks: set[asyncio.Task[Any]] = set()

    async def tutor_start_session(
        self,
        subject: str,
        topic: str | None = None,
        player_model: str | None = None,
    ) -> dict[str, Any]:
        """Create a session and warm up the LLM in the background.

        Returns ``{"session_id": "<uuid>"}`` in well under one second. A
        fire-and-forget ``asyncio.create_task`` primes the Ollama model so
        the first ``tutor_turn`` doesn't pay cold-start latency.
        """
        session = self._store.create(subject=subject, topic=topic)
        provider = player_model or _default_player_model()
        task = asyncio.create_task(
            self._warm_up(provider), name=f"warmup-{session.session_id}"
        )
        self._warmup_tasks.add(task)
        task.add_done_callback(self._warmup_tasks.discard)
        return {"session_id": session.session_id}

    async def tutor_turn(
        self,
        session_id: str,
        user_message: str,
        player_model: str | None = None,
    ) -> dict[str, Any]:
        """Generate one tutor reply for ``user_message`` within the session."""
        try:
            session = self._store.get(session_id)
        except SessionNotFoundError:
            return _session_not_found(session_id)
I have what I need. The live adapter at src/study_tutor/mcp/adapter.py:49-68 returns session_id synchronously and warm-up is fire-and-forget — confirms the sync classification.

The scope of edits:

docs/architecture/domain-model.md:336 §7.1 — flip tutor_start_session row to sync, with a P1-conditional footnote
docs/research/ideas/phase-0-scope.md:92, L97, L167–168 — same flip + tighten rationale
docs/design/README.md §3 D2 + §7.4 — mark the follow-up as closed (since this run is that follow-up)
No ADR changes (Option A). Let me read the exact current text for each, then apply edits.

Read domain-model.md (lines 331-355)
Read phase-0-scope.md (lines 76-175)
Read phase-0-scope.md (lines 241-255)
Bash Find all tutor_start_session references in phase-0-scope
IN
grep -n "tutor_start_session" docs/research/ideas/phase-0-scope.md

OUT
92:| `tutor_start_session` | long-running (session_id returned, poll via `tutor_session_status`) | Includes Graphiti read of student model (three-hop: MacBook → Synology → Gemini → GB10 embeddings); could exceed 10s |
97:If Phase 1 spike shows `tutor_start_session` consistently < 10s end-to-end, reclassify as sync. If `tutor_turn` exceeds 30s due to session-accumulated context, reclassify as long-running.
168:- `tutor_start_session` (long-running, returns session_id)
329:- **Session planner** (FEAT-PO-005 roadmap) reads from Graphiti (Phase 1) and writes back the planned session into the `tutor_start_session` handler created in Phase 0 FEAT-PO-002.
Bash Find SR-07 / long-running refs in build plan
IN
grep -n "tutor_start_session\|long-running" docs/research/ideas/phase-0-build-plan.md

OUT
51:   - **D2 — `tutor_start_session` classified `sync`.** The design artefact classifies `tutor_start_session` as **sync** (returns `session_id` synchronously; warm-up LLM call is opportunistic fire-and-forget, not a polled long-running task) — overriding the architecture text's "long-running" wording in `domain-model.md §7.1` and `phase-0-scope.md §SR-07`. Rationale: matches live behaviour in `src/study_tutor/mcp/adapter.py:49–68`; there is no still-running task to poll via `tutor_session_status`. The architecture text needs a follow-up `/arch-refine` to re-state SR-07 (or reclassify back to long-running if P1 adds Graphiti reads at session start that exceed 1s).
199:6. **Implement `src/study_tutor/mcp/adapter.py` at minimal shape.** Four tools registered per scope-doc SR-07 classification. `tutor_start_session` returns session_id immediately; `tutor_turn` is synchronous; status + end are trivial.
218:11. **Restart Claude Desktop, verify green.** Expect a `study-tutor` server in the MCP list, 4 tools registered (`tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end`).
220:12. **First real invocation.** From a Claude Desktop chat: "Use tutor_start_session with subject English Literature, topic Macbeth." Then "Use tutor_turn to ask about the significance of the witches in Act 1 Scene 1." Expect a response from the fine-tuned model.
246:7. **SR-07 (tool description ≡ behaviour).** Read the four MCP tool descriptions. Verify each says "sync" / "long-running" explicitly, and the handler behaviour matches. Specifically: `tutor_start_session` description says "long-running, returns session_id immediately"; implementation returns session_id in ≤1s.
Applying edits now. I'll keep the scope tight to what you confirmed (domain-model.md §7.1 + phase-0-scope.md §SR-07 + design/README.md follow-up notes), and flag one adjacent item at the end.

Edit domain-model.md
Added 2 lines
Edit phase-0-scope.md
Modified
Edit phase-0-scope.md
Modified
Edit README.md
Modified
Edit README.md
Modified
All five edits applied. Verifying the diff:

Bash Confirm files changed and line counts
IN
git diff --stat docs/architecture/domain-model.md docs/research/ideas/phase-0-scope.md docs/design/README.md

OUT
 docs/architecture/domain-model.md    | 4 +++-
 docs/design/README.md                | 4 ++--
 docs/research/ideas/phase-0-scope.md | 8 ++++----
 3 files changed, 9 insertions(+), 7 deletions(-)
Bash Verify all classification mentions are now consistent
IN
grep -n "tutor_start_session\|long-running" docs/architecture/domain-model.md docs/research/ideas/phase-0-scope.md docs/design/README.md

OUT
docs/design/README.md:55:| **D2** | `tutor_start_session` classified **`sync`** (not `long-running`). | Live behaviour: returns `session_id` synchronously; warm-up is fire-and-forget, not a polled task. SR-07 wording in `domain-model.md §7.1` and `phase-0-scope.md §SR-07` tightened to match — resolved 2026-04-27 via `/arch-refine`. |
docs/design/README.md:91:4. **Architecture follow-up (resolved 2026-04-27):** `domain-model.md §7.1` and `phase-0-scope.md §SR-07` tightened to reclassify `tutor_start_session` long-running → sync via `/arch-refine` (closes D2).
docs/architecture/domain-model.md:335:| `tutor_start_session` | sync — returns `session_id` synchronously; LLM warm-up is fire-and-forget (¹) | < 1s |
docs/architecture/domain-model.md:340:(¹) Phase 0 classification settled by live behaviour in `src/study_tutor/mcp/adapter.py:49–68` — there is no still-running task to poll via `tutor_session_status`. Phase 1 may revert to **long-running** if the Graphiti latency spike (`phase-1-scope.md` §"Graphiti latency spike") shows `search_nodes` median > ~3s for the student-model read at session start; resolved 2026-04-27 via `/arch-refine` (closes design D2).
docs/architecture/domain-model.md:422: McpAdapter.tutor_start_session
docs/research/ideas/phase-0-scope.md:82:**Requirement.** Every MCP tool's description field matches its implementation behaviour. If a tool description says "long-running — session tracked", the handler returns a session_id immediately and exposes a `_status`/`_cancel` companion tool. If a tool description does not say long-running, the handler completes synchronously within 30 seconds.
docs/research/ideas/phase-0-scope.md:84:**Evidence from LES1.** TASK-MDF-POLR — `po_idea` description said "long-running" but handler awaited synchronously, producing a 4-minute timeout on Claude Desktop's 240-second MCP limit.
docs/research/ideas/phase-0-scope.md:86:**Acceptance.** Every MCP tool in Phase 0 classified as either "sync" (< 30s bound) or "long-running" (returns session_id immediately, poll via companion). No tool in the undefined middle.
docs/research/ideas/phase-0-scope.md:92:| `tutor_start_session` | sync (< 1s) | Returns `session_id` synchronously; LLM warm-up is fire-and-forget (`asyncio.create_task` in `src/study_tutor/mcp/adapter.py:49–68`); no Graphiti read in Phase 0; no still-running task to poll |
docs/research/ideas/phase-0-scope.md:97:Phase 1 reversion conditions (per `phase-1-scope.md` §"Graphiti latency spike"): if the Phase 1 student-model read at session start pushes `search_nodes` median > ~3s, reclassify `tutor_start_session` back to long-running and add the `_status` polling companion. If `tutor_turn` exceeds 30s due to session-accumulated context, reclassify it as long-running.
docs/research/ideas/phase-0-scope.md:168:- `tutor_start_session` (sync, returns session_id; warm-up fire-and-forget)
docs/research/ideas/phase-0-scope.md:329:- **Session planner** (FEAT-PO-005 roadmap) reads from Graphiti (Phase 1) and writes back the planned session into the `tutor_start_session` handler created in Phase 0 FEAT-PO-002.
Quick check that the index file and C4 diagrams don't have the same stale classification:

Bash Check architecture index and C4 diagrams for stale classification
IN
grep -n "tutor_start_session\|long-running" docs/architecture/ARCHITECTURE.md docs/architecture/container.md docs/architecture/system-context.md 2>&1

OUT
docs/architecture/container.md:30:        Container(mcp, "MCP Adapter", "Python / mcp SDK", "Registers 4 tools: tutor_start_session (long-running), tutor_turn (sync), tutor_session_status, tutor_session_end. SR-07 classification.")
docs/architecture/ARCHITECTURE.md:94:| AI agents (Claude Desktop, future Jarvis) | MCP JSON-RPC over stdio — 4 tools with SR-07 sync/long-running classification | P0 |
docs/architecture/ARCHITECTURE.md:122:- **Performance:** `tutor_turn` p95 < 10s; `tutor_start_session` returns
Read ARCHITECTURE.md (lines 119-130)
Done — refinement applied. Summary:

Edits applied (all in scope):

docs/architecture/domain-model.md:335 §7.1 — tutor_start_session reclassified long-running → sync, with footnote citing live behaviour at adapter.py:49–68 and the Phase-1 reversion condition.
docs/research/ideas/phase-0-scope.md:88-97 §SR-07 — table flipped to sync, header updated from "provisional" → "settled", reversion condition inverted (P1 spike triggers a flip back to long-running, not the other way around).
docs/research/ideas/phase-0-scope.md:168 — FEAT-PO-002 bullet aligned.
docs/design/README.md:55 D2 + docs/design/README.md:91 §7.4 — both follow-up notes marked resolved 2026-04-27.
Total: 3 files, +9/-7 lines.

Three adjacent inconsistencies you didn't include in scope — flagging for a decision, not editing:

docs/architecture/container.md:30 — C4 Container diagram description still says tutor_start_session (long-running). Same architecture artefact family as domain-model.md; now inconsistent. Likely should match.
docs/research/ideas/phase-0-build-plan.md:246 — SR-07 verification step in your manual smoke test still says tutor_start_session description says "long-running, returns session_id immediately". Will fail your own verification step as written.
The actual MCP tool description registered at runtime — worth grepping in src/study_tutor/mcp/adapter.py to confirm the docstring/description text matches the new sync classification, since SR-07 is "tool description ≡ implementation contract" — that's the structural rule itself.
Want me to apply those three? They're a one-line fix each. The build-plan edit and the MCP tool description edit are particularly load-bearing for SR-07 to actually pass.

Graphiti seeding: no ADR changed, so architecture_decisions group is unaffected. The domain-model and design README changes belong in project_design / architecture_decisions re-seeding, but that's /system-arch --refresh and /system-design territory, not this command's job.

yes please make those changes
Applying. Need to read each location first to get the exact text.

Read container.md (lines 26-40)
Read phase-0-build-plan.md (lines 241-255)
Bash Find MCP tool descriptions and any long-running references in code
IN
grep -rn "long-running\|long running\|tutor_start_session" src/study_tutor/mcp/ 2>/dev/null

OUT
src/study_tutor/mcp/server.py:4:(long-running vs sync) per the Phase-0 scope (SR-07).
src/study_tutor/mcp/server.py:26:        adapter.tutor_start_session,
src/study_tutor/mcp/server.py:27:        name="tutor_start_session",
src/study_tutor/mcp/server.py:55:        "tutor_start_session, tutor_turn, tutor_session_status, tutor_session_end",
src/study_tutor/mcp/adapter.py:5:* ``tutor_start_session`` — long-running classification; returns ``session_id``
src/study_tutor/mcp/adapter.py:49:    async def tutor_start_session(
Read adapter.py (lines 2-51)
Read server.py
Found a load-bearing one: src/study_tutor/mcp/server.py:30 registers the actual tool description as "Long-running, returns session_id immediately" — that's the canonical SR-07 contract the runtime ships. Quick check for tests that assert on that string before I flip it.

Bash Check for tests asserting on the long-running description
IN
grep -rn "Long-running\|long-running\|long_running" tests/ src/study_tutor/ 2>&1 | grep -v __pycache__

OUT
src/study_tutor/mcp/adapter.py:5:* ``tutor_start_session`` — long-running classification; returns ``session_id``
src/study_tutor/mcp/server.py:4:(long-running vs sync) per the Phase-0 scope (SR-07).
src/study_tutor/mcp/server.py:30:            "Long-running, returns session_id immediately; LLM model is "
Bash Find tests that may verify tool descriptions
IN
find tests -name '*.py' | xargs grep -l "SR-07\|tutor_start_session\|description" 2>/dev/null | head -5

OUT
tests/unit/mcp/test_adapter.py
Bash Check what test_adapter asserts
IN
grep -n "description\|long\|sync\|SR-07" tests/unit/mcp/test_adapter.py | head -20

OUT
8:import asyncio
26:        description="test",
37:async def _drain_warmups(adapter: MCPAdapter) -> None:
42:        await asyncio.gather(*tasks, return_exceptions=True)
45:async def test_start_session_returns_session_id(adapter: MCPAdapter) -> None:
54:async def test_turn_rejects_unknown_session(adapter: MCPAdapter) -> None:
59:async def test_turn_generates_response(
85:async def test_session_end_flips_status(adapter: MCPAdapter) -> None:
97:async def test_session_end_unknown_returns_error(adapter: MCPAdapter) -> None:
102:async def test_server_registers_four_tools(
116:    # SR-07: description MUST NOT leak Phase 1 Graphiti behaviour.
117:    assert "graphiti" not in end_tool.description.lower()
118:    assert "async" not in end_tool.description.lower()
119:    assert "marks session ended" in end_tool.description.lower()
No test assertions on "long-running" for tutor_start_session. Applying all five edits:

Edit container.md
Modified
Edit phase-0-build-plan.md
Modified
Edit adapter.py
Added 3 lines
Edit server.py
Added 1 line
Edit server.py
Modified
All five edits applied. Let me run the existing MCP tests to confirm I haven't broken anything, and re-grep to confirm no stragglers:

Bash Confirm only legitimate long-running mentions remain
IN
grep -rn "long-running\|long running" docs/architecture/ docs/research/ideas/phase-0-scope.md docs/research/ideas/phase-0-build-plan.md docs/design/README.md src/study_tutor/mcp/ 2>&1 | grep -v __pycache__

OUT
docs/architecture/ARCHITECTURE.md:94:| AI agents (Claude Desktop, future Jarvis) | MCP JSON-RPC over stdio — 4 tools with SR-07 sync/long-running classification | P0 |
docs/architecture/domain-model.md:340:(¹) Phase 0 classification settled by live behaviour in `src/study_tutor/mcp/adapter.py:49–68` — there is no still-running task to poll via `tutor_session_status`. Phase 1 may revert to **long-running** if the Graphiti latency spike (`phase-1-scope.md` §"Graphiti latency spike") shows `search_nodes` median > ~3s for the student-model read at session start; resolved 2026-04-27 via `/arch-refine` (closes design D2).
docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md:37:| `tutor_start_session` | long-running (returns `session_id` in ≤1s; poll via `tutor_session_status`) | n/a (fire-and-forget) |
docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md:42:> `tutor_start_session` is architected as long-running for Phase-1 forward
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md:50:  would become long-running and require SR-07 reclassification, which
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md:65:- Simplifies the MCP tool contract — no long-running reclassification
docs/design/README.md:55:| **D2** | `tutor_start_session` classified **`sync`** (not `long-running`). | Live behaviour: returns `session_id` synchronously; warm-up is fire-and-forget, not a polled task. SR-07 wording in `domain-model.md §7.1` and `phase-0-scope.md §SR-07` tightened to match — resolved 2026-04-27 via `/arch-refine`. |
docs/design/README.md:91:4. **Architecture follow-up (resolved 2026-04-27):** `domain-model.md §7.1` and `phase-0-scope.md §SR-07` tightened to reclassify `tutor_start_session` long-running → sync via `/arch-refine` (closes D2).
src/study_tutor/mcp/server.py:4:(sync vs long-running) per the Phase-0 scope (SR-07). All four Phase-0
docs/research/ideas/phase-0-build-plan.md:51:   - **D2 — `tutor_start_session` classified `sync`.** The design artefact classifies `tutor_start_session` as **sync** (returns `session_id` synchronously; warm-up LLM call is opportunistic fire-and-forget, not a polled long-running task) — overriding the architecture text's "long-running" wording in `domain-model.md §7.1` and `phase-0-scope.md §SR-07`. Rationale: matches live behaviour in `src/study_tutor/mcp/adapter.py:49–68`; there is no still-running task to poll via `tutor_session_status`. The architecture text needs a follow-up `/arch-refine` to re-state SR-07 (or reclassify back to long-running if P1 adds Graphiti reads at session start that exceed 1s).
docs/research/ideas/phase-0-build-plan.md:246:7. **SR-07 (tool description ≡ behaviour).** Read the four MCP tool descriptions. Verify each is consistent with handler behaviour — by SR-07 acceptance, a description without the word "long-running" implies sync (< 30s). Specifically: all four Phase-0 tools are sync; `tutor_start_session` description says "sync; returns session_id immediately; LLM model is warmed up in the background"; implementation returns session_id in < 1s with `asyncio.create_task` warm-up.
docs/research/ideas/phase-0-scope.md:82:**Requirement.** Every MCP tool's description field matches its implementation behaviour. If a tool description says "long-running — session tracked", the handler returns a session_id immediately and exposes a `_status`/`_cancel` companion tool. If a tool description does not say long-running, the handler completes synchronously within 30 seconds.
docs/research/ideas/phase-0-scope.md:84:**Evidence from LES1.** TASK-MDF-POLR — `po_idea` description said "long-running" but handler awaited synchronously, producing a 4-minute timeout on Claude Desktop's 240-second MCP limit.
docs/research/ideas/phase-0-scope.md:86:**Acceptance.** Every MCP tool in Phase 0 classified as either "sync" (< 30s bound) or "long-running" (returns session_id immediately, poll via companion). No tool in the undefined middle.
docs/research/ideas/phase-0-scope.md:97:Phase 1 reversion conditions (per `phase-1-scope.md` §"Graphiti latency spike"): if the Phase 1 student-model read at session start pushes `search_nodes` median > ~3s, reclassify `tutor_start_session` back to long-running and add the `_status` polling companion. If `tutor_turn` exceeds 30s due to session-accumulated context, reclassify it as long-running.
src/study_tutor/mcp/adapter.py:8:  long-running if the Graphiti student-model read at session start
Bash Run MCP unit tests to confirm nothing broke
IN
uv run pytest tests/unit/mcp/ -x -q 2>&1 | tail -25

OUT
warning: `VIRTUAL_ENV=/Library/Frameworks/Python.framework/Versions/3.14` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
   Building study-tutor @ file:///Users/richardwoollcott/Projects/appmilla_github/study-tutor
Downloading cryptography (7.5MiB)
Downloading pydantic-core (1.9MiB)
      Built study-tutor @ file:///Users/richardwoollcott/Projects/appmilla_github/study-tutor
 Downloaded pydantic-core
 Downloaded cryptography
Uninstalled 16 packages in 155ms
Installed 17 packages in 35ms
........                                                                 [100%]
8 passed in 6.30s
Tests green (8/8). One more inconsistency found — ADR-ARCH-008 also classifies tutor_start_session as long-running. Reading to assess:

Read ADR-ARCH-008-mcp-only-agent-access.md (lines 31-60)
Important finding — I owe you a correction. My initial scope assessment was wrong.

I told you earlier the "long-running" classification only lived in domain-model.md §7.1 and phase-0-scope.md §SR-07, with no ADR. That was incorrect — ADR-ARCH-008:35-46 contains an explicit table classifying tutor_start_session as long-running, plus a reasoned rationale block:

tutor_start_session is architected as long-running for Phase-1 forward compatibility (where it will read the student model from Graphiti). In Phase 0 the implementation is a UUID mint + in-memory dict insert that returns in ≤1s. The classification is stable across phases so /feature-spec does not need to re-classify the MCP contract when Graphiti lands.

So this isn't just SR-07 wording — it was a deliberate architectural decision with a stated rationale ("forward compat over P0-accuracy"). The design D2 reclassification effectively overturns it. By editing the downstream docs and code without touching the ADR, I've now put the architecture set in a contradictory state:

ADR-ARCH-008 (binding): long-running, "stable across phases"
domain-model.md / phase-0-scope.md / container.md (derived): sync
server.py (runtime): sync
This is the staleness /arch-refine is built to prevent — and the right answer was actually Option B from the original menu (supersede ADR-ARCH-008 with a new ADR), not Option A. I missed it. Sorry.

Three options for how to recover:

1. Revert all edits, then run /arch-refine properly against ADR-ARCH-008. Cleanest. The new ADR (ADR-ARCH-017) supersedes ADR-ARCH-008's classification table with the sync decision + P1 reversion condition; downstream artefacts get re-derived. This is what the command's temporal-superseding flow exists for.

2. Keep the current edits, additionally supersede ADR-ARCH-008 now. Pragmatic. Same end state as #1, less rework, but the order of operations is non-canonical (we changed downstream first, then the ADR catches up).

3. Revert all edits and keep ADR-ARCH-008 as-is. This means design D2 was wrong — tutor_start_session should be classified long-running for forward-compat, even though the P0 implementation returns in <1s. We'd update design/README.md to retract D2 and add a _status/_cancel companion, or accept that P0 is in violation of SR-07. Probably not what you want, but it is on the table since ADR-ARCH-008's rationale is real.

Footnote on ADR-ARCH-008's rationale: the "stable across phases" argument is weakened by phase-1-scope.md:84-85 explicitly saying P1 classification depends on the Graphiti latency spike outcome — i.e., the classification was never going to be stable across phases, so the forward-compat rationale doesn't survive Phase 1 planning. So #1 or #2 is probably right.

Which option? My recommendation is #2 — same end state, no churn — but #1 is the cleaner version if you want the audit trail to look canonical.

Tests: tests/unit/mcp/ 8/8 passing.

phase-0-build-plan.md
option 1
Reverting all edits, then running canonical /arch-refine --adr=ADR-ARCH-008 flow.

Bash Check current modified files in scope
IN
git status --short docs/ src/study_tutor/ 2>&1

OUT
 M docs/architecture/container.md
 M docs/architecture/domain-model.md
 M docs/design/README.md
 M docs/research/ideas/phase-0-build-plan.md
 M docs/research/ideas/phase-0-scope.md
 M src/study_tutor/mcp/adapter.py
 M src/study_tutor/mcp/server.py
Bash Revert all session edits
IN
git checkout -- docs/architecture/container.md docs/architecture/domain-model.md docs/design/README.md docs/research/ideas/phase-0-build-plan.md docs/research/ideas/phase-0-scope.md src/study_tutor/mcp/adapter.py src/study_tutor/mcp/server.py

OUT
(Bash completed with no output)
Bash Confirm revert
IN
git status --short docs/ src/study_tutor/ 2>&1

OUT
(Bash completed with no output)
Revert clean. Now running canonical /arch-refine --adr=ADR-ARCH-008 flow. Per the command spec, I'll present the proposed refined decision + impact scope for your approval before writing anything.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ TARGETING: ADR-ARCH-008 — MCP-only agent access
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scope of supersession: ONLY the Phase-0 SR-07 tool classification
table (lines 35–46) and its "stable across phases for forward
compatibility" rationale block. The rest of ADR-ARCH-008
(single-transport choice, HTTP-deferral, auth posture) stands
unchanged.

Suggested model: ADR-ARCH-008 marked status: superseded, with a
note pointing to ADR-ARCH-017 for the SR-07 classification subdecision.
ADR-ARCH-017 is narrowly scoped to that table + reversion conditions —
it does not re-state the rest of ARCH-008.

Confirm partial-scope supersession model? [Y/N]
Pending that, here's the refined decision content I'd capture for ADR-ARCH-017:

Q1. What has changed?

Two findings from the 2026-04-26 /system-design pass invalidated ADR-ARCH-008's rationale for classifying tutor_start_session as long-running:

Live behaviour. src/study_tutor/mcp/adapter.py:49-68 returns session_id in <1s and runs warm-up as fire-and-forget (asyncio.create_task). There is no still-running task to poll — the long-running classification has no operational referent. This also means the SR-07 acceptance ("long-running tools expose a _status/_cancel companion") is currently in violation.

The forward-compat rationale doesn't survive Phase 1. phase-1-scope.md:84-85 explicitly makes the P1 classification dependent on the Graphiti latency spike outcome — so the "classification is stable across phases" argument from ADR-ARCH-008 was already known to be conditional. Forward-compat speculation should be replaced with measurement-conditional reversion.

Q2. What is the new decision?

Phase 0 SR-07 classification table:

Tool	Class	Bound
tutor_start_session	sync	< 1s; warm-up is fire-and-forget
tutor_turn	sync	p95 < 10s
tutor_session_status	sync	< 2s
tutor_session_end	sync (triggers async Graphiti write-back in P1)	< 2s
Phase 1 reversion condition. If the Graphiti student-model read at session start pushes search_nodes median > ~3s (per phase-1-scope.md:84-85), reclassify tutor_start_session back to long-running and add the _status/_cancel polling companion. Reversion is conditional on measurement, not speculation.

Q3. Alternatives considered

Keep long-running for forward compat (ADR-ARCH-008's choice). Rejected: P0 violates SR-07 (no _status companion), and the rationale assumes phase-stability that phase-1-scope.md already contradicts.
Add _status/_cancel companion to honour long-running. Rejected: introduces dead code in P0 to satisfy a classification with no operational basis.
Mark P0 classification as TBD until P1 spike. Rejected: SR-07 acceptance requires every Phase 0 tool classified; "no tool in the undefined middle".
Q4. Consequences

✅ SR-07 contract aligns with live behaviour (resolves a current violation).
✅ Replaces forward-compat speculation with measurement-conditional Phase 1 reversion.
⚠️ If P1 Graphiti read >3s and we revert, MCP tool description changes — visible to integrators (Claude Desktop, etc.) but not a code-API break.
Phase 4 — Downstream impact scope:


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ DOWNSTREAM IMPACT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ADRs:
  ⚠️ ADR-ARCH-008 — partially superseded (classification table + rationale)

Architecture artefacts:
  ⚠️ docs/architecture/domain-model.md §7.1 — table row needs flip
  ⚠️ docs/architecture/container.md L30 — C4 description needs flip

Design artefacts:
  ⚠️ docs/design/README.md §3 D2 + §7.4 — mark resolved

Scope/build-plan docs:
  ⚠️ docs/research/ideas/phase-0-scope.md §SR-07 (L88, L92, L97, L168)
  ⚠️ docs/research/ideas/phase-0-build-plan.md L246 (SR-07 verify step)

Code (the load-bearing SR-07 contract):
  ⚠️ src/study_tutor/mcp/server.py L29-32 — registered tool description
  ⚠️ src/study_tutor/mcp/adapter.py L5 — module docstring
  ⚠️ src/study_tutor/mcp/server.py L4 — module docstring

Graphiti staleness flagging:
  • Will tag downstream nodes referencing ADR-ARCH-008 with stale: true

C4 Re-review gate:
  • Container diagram description (single-line text change) —
    no structural change to L1/L2 topology, but description-cell update
    requires your sign-off per /arch-refine Phase 6.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision points before I write anything:

Confirm the partial-scope supersession model (ADR-ARCH-008 marked superseded, ADR-ARCH-017 scoped narrowly to the SR-07 table)? [Y/N]
Approve the refined decision Q1–Q4 above as drafted, or want any wording revised? [A/R]
Approve the impact scope as the full set of edits to apply? [A/R]
Once you say yes to all three I'll write ADR-ARCH-017, update ADR-ARCH-008's status block, re-apply the downstream edits, and present the C4 description change for the §6 review gate. No Graphiti seeding or staleness flagging will run without your explicit OK at the end.

please can you zoom out and explain this in terms of the bigger picture - what are wqe changing and why?
What's actually changing
A single MCP tool's classification: tutor_start_session flipping from "long-running" to "sync".

In MCP terms, those two classifications are different protocols:

Sync — client calls, gets a response, done. Bounded under 30s.
Long-running — client calls, gets a job ID immediately, then polls a _status/_cancel companion tool to track progress. Designed for tasks that take minutes.
Why this needs fixing
The code only ever implemented the sync protocol. The Study Tutor MCP server has four tools, none of them have a _status/_cancel companion, and tutor_start_session returns in well under a second. But the architecture docs (and the runtime tool description that ships to Claude Desktop) say "long-running".

That mismatch violates SR-07 — one of the six "parity surface" rules that say tool descriptions must match implementation behaviour. SR-07 isn't theoretical: it exists because a previous project (specialist-agent) hit a 4-minute Claude Desktop timeout from exactly this kind of label/behaviour drift. So we have a structural rule on the books, and we're failing it on day one.

Why the docs originally said long-running
When ADR-ARCH-008 was written on April 18, the call was forward-compatibility. The reasoning: Phase 1 will read student state from Graphiti at session start, that might be slow, so let's classify the tool long-running now to avoid a breaking change later. The ADR literally claimed "classification is stable across phases".

That bet looked reasonable at the time. It looks worse now for two reasons:

The Phase 0 code never implemented the protocol the classification implies. No _status companion was built. So forward-compat was paid for with a current SR-07 violation.
phase-1-scope.md explicitly says the P1 classification depends on a Graphiti latency measurement we haven't taken yet. Median > ~3s → long-running. Median < 3s → sync. So the "stable across phases" promise was already conditional on a measurement. Forward-compat speculation never had the certainty the ADR claimed.
What the new decision says
Phase 0 is sync, because that's what the code does, and SR-07 demands they match.
Phase 1 may revert to long-running, but only if measurement requires it — when the Graphiti student-model read at session start is empirically > ~3s. It's a measurement-conditional rule, replacing the forward-compat speculation.
Why we're going through the /arch-refine ceremony rather than just editing files
ADR-ARCH-008 captured this as a deliberate architectural choice with stated rationale. Silently editing it would erase the reasoning trail. The /arch-refine flow:

Supersedes the old ADR with a new one (ADR-ARCH-017) — both stay readable in docs/architecture/decisions/ and in the Graphiti knowledge graph.
Stale-flags downstream artefacts (domain-model, C4 diagrams, design docs) that were derived from the old decision.
Forces a re-review of any C4 diagrams that change.
This matters because: (a) Phase 1 planning will reference this exact decision and needs to find the current version; (b) the audit trail tells future-you (and any reviewer) why the original call was made and why it was overturned. Silently editing strips both.

What is NOT changing
ADR-ARCH-008 is mostly still correct. The supersession is narrow — it only touches the SR-07 classification subsection. These remain unchanged:

MCP stdio as the only transport (no REST, no HTTP, no A2A).
The four-tool surface itself.
The single-user / process-level trust auth posture.
All the other 15 ADRs.
The cost-benefit, simply
We're spending ~30 minutes of refinement ceremony to:

Resolve a current SR-07 violation that exists in shipped code.
Replace a speculative forward-compat argument with an empirical, measurement-conditional rule.
Keep the audit trail intact so Phase 1 work has a coherent foundation.
The alternative is to leave a known-violated structural rule in place because the original ADR rationale would feel awkward to retract. That's the kind of debt that compounds — especially when the same incident class (LES1) is what motivated SR-07's existence in the first place.

please proceed
Proceeding. Reading ADR-ARCH-008 in full and the architecture index to make the right edits.

Read ADR-ARCH-008-mcp-only-agent-access.md
Bash Check architecture index for ADR references
IN
grep -n "ADR-ARCH-008\|ADR-ARCH-016\|ADR-ARCH-017\|## " docs/architecture/ARCHITECTURE.md | head -40

OUT
10:## 1. One-paragraph summary
29:## 2. Structural pattern
42:## 3. Bounded contexts
68:## 4. Technology stack
89:## 5. Multi-consumer API surfaces
99:See `ADR-ARCH-008-mcp-only-agent-access.md`.
101:## 6. Cross-cutting concerns (12)
120:## 7. Constraints & NFRs (highlights)
139:See `ADR-ARCH-014` through `ADR-ARCH-016`.
141:## 8. Phase-by-phase deliverable map
150:## 9. Architecture Decision Records (index)
161:| ADR-ARCH-008 | MCP-only for agent access; single-user auth posture | Accepted |
169:| ADR-ARCH-016 | 18 May 2026 deadline as load-bearing architectural constraint | Accepted |
171:## 10. Assumptions
180:## 11. Related documents
Bash Confirm ADR file naming convention
IN
ls docs/architecture/decisions/ADR-ARCH-001-* | head -1 && head -3 docs/architecture/decisions/ADR-ARCH-001-ddd-structural-pattern.md

OUT
docs/architecture/decisions/ADR-ARCH-001-ddd-structural-pattern.md
# ADR-ARCH-001 — Use Domain-Driven Design structural pattern

## Status
Read ARCHITECTURE.md (lines 151-175)
Now executing — write ADR-ARCH-017, update ADR-ARCH-008 status, update the architecture index, then re-apply the downstream edits.

Write ADR-ARCH-017-tutor-start-session-sync-classification.md
81 lines
# ADR-ARCH-017 — `tutor_start_session` SR-07 classification: sync (Phase 0)

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 0
**Supersedes:** ADR-ARCH-008 (partial — only the SR-07 classification table at lines 35–46 and the "stable across phases for forward compatibility" rationale block; the rest of ADR-ARCH-008 — single-transport choice, HTTP-deferral, auth posture, Phase-0 session-scope note — stands unchanged).
**Related:** ADR-ARCH-009 (CC-07 / SR-07), LES1 row 19, design D2 (`docs/design/README.md §3`).

## Context

The 2026-04-26 `/system-design` pass surfaced two findings that invalidate ADR-ARCH-008's classification of `tutor_start_session` as long-running:

1. **The Phase 0 implementation never satisfied the long-running protocol.** [src/study_tutor/mcp/adapter.py:49–68](../../../src/study_tutor/mcp/adapter.py) returns `{"session_id": "..."}` synchronously in well under 1s; the LLM warm-up runs as a fire-and-forget `asyncio.create_task`. There is no still-running task to poll, and no `_status`/`_cancel` companion tool exists. This is a current SR-07 violation: the registered tool description says "Long-running, returns session_id immediately" but the handler exposes none of the long-running protocol's affordances.

2. **The forward-compat rationale doesn't survive Phase 1 planning.** ADR-ARCH-008 justified the long-running classification with "the classification is stable across phases so `/feature-spec` does not need to re-classify the MCP contract when Graphiti lands." But [phase-1-scope.md:84–85](../../research/ideas/phase-1-scope.md) explicitly makes the Phase 1 classification *dependent on* the Graphiti latency spike outcome:

   > If search_nodes median > 3s: `tutor_start_session` stays long-running (Phase 0 classification holds)
   > If search_nodes median < 1s: `tutor_start_session` could be reclassified as sync, simplifying the MCP tool shape

   So phase-stability was never load-bearing — it was always conditional on a measurement that hadn't been taken. Forward-compat speculation cannot justify a current SR-07 violation.

LES1 row 19 (latency classification, marked ⚠️ for study-tutor) and TASK-MDF-POLR (4-minute Claude Desktop timeout from a long-running/sync mismatch) are the prior-art evidence that an SR-07 violation is not a paper-only concern.

## Decision

`tutor_start_session` is classified **sync** in Phase 0. The full Phase-0 SR-07 classification table is:

| Tool | Class | Bound |
|---|---|---|
| `tutor_start_session` | **sync** | < 1s; warm-up is fire-and-forget |
| `tutor_turn` | sync | p95 < 10s |
| `tutor_session_status` | sync | < 2s |
| `tutor_session_end` | sync (triggers async Graphiti write-back in P1) | < 2s |

All four Phase-0 MCP tools are sync. No `_status`/`_cancel` companion tool is required.

**Phase 1 reversion condition.** If the Graphiti latency spike (per `phase-1-scope.md` §"Graphiti latency spike") shows that the Phase 1 student-model read at session start pushes `search_nodes` median > ~3s, `tutor_start_session` will be reclassified back to long-running and a `_status`/`_cancel` companion will be added. Reversion is conditional on measurement, not speculation. The reversion path is documented here and in `phase-0-scope.md §SR-07` so a future `/arch-refine` is unsurprising rather than disruptive.

## Alternatives considered

- **Keep `tutor_start_session` long-running for forward compatibility (ADR-ARCH-008's original choice).** Rejected. The forward-compat argument requires phase-stability, which `phase-1-scope.md` already contradicts. Meanwhile the long-running classification has no operational basis in Phase 0 — there is no polled task, no `_status`/`_cancel` companion, and the registered tool description misrepresents the handler. Holding the classification for a forward-compat that may not survive measurement creates a guaranteed current SR-07 violation in exchange for a hypothetical future continuity that may not materialise.

- **Add a `_status`/`_cancel` companion to honour the long-running classification.** Rejected. Introduces dead protocol surface in Phase 0 (a polling endpoint that has nothing to poll) to satisfy a classification with no operational basis. Increases the four-tool surface, complicates the demo script, and provides no value to either Lilymay or judges.

- **Mark Phase 0 classification as TBD until the Phase 1 latency spike.** Rejected. SR-07's acceptance criterion is explicit: "Every MCP tool in Phase 0 classified as either 'sync' (< 30s bound) or 'long-running' (returns session_id immediately, poll via companion). No tool in the undefined middle." TBD is exactly the undefined middle.

## Consequences

**Positive:**
- The Phase 0 SR-07 contract aligns with shipped behaviour. The current violation is resolved.
- The Phase 1 reversion path is documented and conditional on a specific empirical measurement — replacing forward-compat speculation with a measurement-conditional rule.
- The four-tool MCP surface stays minimal (no companion `_status`/`_cancel` for `tutor_start_session`).
- The classification is now derivable from inspection of `src/study_tutor/mcp/adapter.py` rather than from architectural commitment alone.

**Negative:**
- If the Phase 1 Graphiti latency spike shows `search_nodes` median > ~3s and we revert to long-running, MCP integrators (Claude Desktop, the demo script) will see a tool description change — visible in their tool list. This is a description-string change, not an API break, and the spike result will be known before any P1 implementation work commits to the tool surface.
- Two ADRs (ARCH-008 and ARCH-017) now need to be read together to understand the SR-07 classification subdecision. Mitigated by the partial-supersession status block on ARCH-008 and by both ADRs being co-located in `docs/architecture/decisions/`.

## Affected downstream artefacts

This decision supersedes wording in the following derived artefacts (all updated in the same `/arch-refine` run):

- `docs/architecture/domain-model.md §7.1` — table row for `tutor_start_session`.
- `docs/architecture/container.md` — C4 Container description for the MCP Adapter.
- `docs/research/ideas/phase-0-scope.md §SR-07` — classification table, header note, reversion conditions, FEAT-PO-002 bullet.
- `docs/research/ideas/phase-0-build-plan.md` — SR-07 verification step (punch-list item 7's D2 record stays as historical context).
- `docs/design/README.md §3 D2 + §7.4` — design follow-up note marked resolved.
- `src/study_tutor/mcp/server.py` — registered tool description (the canonical SR-07 contract).
- `src/study_tutor/mcp/adapter.py` — module docstring.

## References

- ADR-ARCH-008 (partially superseded): MCP-only for agent access; single-user auth posture.
- ADR-ARCH-009: Six parity surfaces (LES1) as load-bearing cross-cutting concerns.
- LES1 §1 row 19 + TASK-MDF-POLR — `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`.
- `docs/design/README.md §3 D2` — design pass that surfaced this contradiction.
- `docs/research/ideas/phase-1-scope.md §"Graphiti latency spike"` — the empirical reversion condition.
Edit ADR-ARCH-008-mcp-only-agent-access.md
Added 9 lines
Edit ADR-ARCH-008-mcp-only-agent-access.md
Added 6 lines
Edit ARCHITECTURE.md
Modified
Edit ARCHITECTURE.md
Added 1 line
ADRs written and indexed. Now applying the downstream edits — same as the previous round, but now referencing ADR-ARCH-017 as the authority.

Edit domain-model.md
Added 2 lines
Edit phase-0-scope.md
Modified
Edit phase-0-scope.md
Modified
Edit README.md
Modified
Edit README.md
Modified
Edit container.md
Modified
Edit phase-0-build-plan.md
Modified
Edit adapter.py
Added 3 lines
Edit server.py
Added 1 line
Edit server.py
Modified
All edits applied. Verifying tests pass and the architecture set is now consistent.

Bash Run MCP unit tests
IN
uv run pytest tests/unit/mcp/ -x -q 2>&1 | tail -8

OUT
warning: `VIRTUAL_ENV=/Library/Frameworks/Python.framework/Versions/3.14` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
........                                                                 [100%]
8 passed in 6.26s
Bash Final file diff list
IN
git status --short docs/ src/study_tutor/ 2>&1

OUT
 M docs/architecture/ARCHITECTURE.md
 M docs/architecture/container.md
 M docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md
 M docs/architecture/domain-model.md
 M docs/design/README.md
 M docs/research/ideas/phase-0-build-plan.md
 M docs/research/ideas/phase-0-scope.md
 M src/study_tutor/mcp/adapter.py
 M src/study_tutor/mcp/server.py
?? docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md
Tests 8/8 green. One file added (ADR-ARCH-017), nine modified.

Phase 6 — C4 Re-Review Gate
The container.md change is description-only — no structural topology change. The single line affected:

Before:


"Registers 4 tools: tutor_start_session (long-running), tutor_turn (sync),
 tutor_session_status, tutor_session_end. SR-07 classification."
After:


"Registers 4 tools, all sync per SR-07 (ADR-ARCH-017): tutor_start_session
 (sync; warm-up fire-and-forget), tutor_turn (sync), tutor_session_status (sync),
 tutor_session_end (sync; async Graphiti write-back in P1)."
L1 (system context) is unaffected — no new external systems, no relationships changed. The 21-node count in the C4 file is unchanged.

Final Summary
Created (1):

docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md
Modified (9):

ADR-ARCH-008 — status block flipped to "Partially superseded by ADR-ARCH-017"; classification table struck through with pointer; original rationale preserved verbatim with supersession warning above it.
ARCHITECTURE.md:161 — index status updated; new row for ADR-ARCH-017.
domain-model.md §7.1 — table row + footnote citing ADR-ARCH-017.
container.md:30 — C4 description.
design/README.md §3 D2 + §7.4 — both follow-up notes marked resolved with ADR-ARCH-017 reference.
phase-0-scope.md §SR-07 — header + table + reversion conditions + FEAT-PO-002 bullet.
phase-0-build-plan.md:246 — SR-07 verification step.
adapter.py:5 — module docstring.
server.py:4 + L29-32 — module docstring + the load-bearing registered tool description (the canonical SR-07 contract that ships to Claude Desktop).
Phase 8 — Graphiti Seeding (offered, not auto-run)
The new and superseded ADRs should be seeded into the architecture_decisions group. The guardkit graphiti add-context CLI handles sanitisation. Suggested commands:


guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md \
  --group architecture_decisions

guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md \
  --group architecture_decisions
Re-seeding ADR-ARCH-008 captures the new "Partially superseded" status block in the knowledge graph so Graphiti queries return the current state (not the pre-supersession version).

Staleness flagging (Phase 5 of /arch-refine) is what update_entity_metadata({stale: True}) does in the canonical flow — it tags downstream nodes that referenced ADR-ARCH-008's classification so /system-design will report them on next run. I haven't run that step (no direct Graphiti write access in this command shape) — the affected downstream artefacts are listed in the ADR-ARCH-017 §"Affected downstream artefacts" section and have already been edited in this run, so the staleness flag would fire and immediately resolve. Worth running if you want the audit trail intact, no-op functionally.

Want me to run the two seeding commands? Y/N — or hold off if you'd prefer to commit first and seed as a separate step.

please can you run the seeding commands
Running the two seeding commands. Graphiti seeding does LLM-based entity extraction via vLLM on GB10 — typically a couple of minutes per ADR.

Bash Seed new ADR-ARCH-017 to Graphiti
IN
guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md --group architecture_decisions 2>&1 | tail -30

OUT
Usage: guardkit-py graphiti add-context [OPTIONS] PATH
Try 'guardkit-py graphiti add-context --help' for help.

Error: No such option: --group
Bash Check correct flag for add-context
IN
guardkit graphiti add-context --help 2>&1

OUT
Usage: guardkit-py graphiti add-context [OPTIONS] PATH

  Add context from files to Graphiti.

  Adds content from markdown files to the Graphiti knowledge graph. Supports
  single files or directories with glob patterns.

  Examples:
      guardkit graphiti add-context docs/ADR-001.md
      guardkit graphiti add-context docs/architecture/
      guardkit graphiti add-context docs/ --pattern "**/*.md"
      guardkit graphiti add-context docs/ADR-001.md --type adr
      guardkit graphiti add-context docs/ --dry-run
      guardkit graphiti add-context docs/ --delay 1.0
      guardkit graphiti add-context docs/ --delay 0

  Supported parser types:
      - adr: Architecture Decision Records
      - feature_spec: Feature specifications
      - full_doc: Full document capture (entire markdown content)
      - project_overview: Project overview documents
      - project_doc: General project documentation (CLAUDE.md, README.md)

Options:
  --type TEXT           Force parser type (adr, feature-spec, project-
                        overview)
  -f, --force           Overwrite existing context
  --dry-run             Show what would be added without adding
  --pattern TEXT        Glob pattern for directory (default: **/*.md)
  -v, --verbose         Show detailed processing output
  -q, --quiet           Suppress non-error output
  --delay FLOAT         Inter-episode delay in seconds (default: 0.5, 0 to
                        disable)
  --chunk-size INTEGER  Force chunking for docs above this size in bytes
                        (default: 10240). Use 0 to always chunk.
  --timeout FLOAT       Per-episode timeout in seconds (overrides auto-
                        detected timeout). Use for slow vLLM instances.
  --help                Show this message and exit.
Bash Seed ADR-ARCH-017 with explicit adr parser type
IN
guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md --type adr -v 2>&1 | tail -50

OUT
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

Parsing 
docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification
.md with adr
  Found 1 episodes
    - adr_adr-arch-017-tutor-start-session-sr-07-classification-sync-phase-0 
(adr)
INFO:graphiti_core.graphiti:Completed add_episode in 182931.72883987427 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-017-tutor-start-session-sr-07-classification-sync-phase-0]: nodes=9, edges=26, invalidated=0
  ✓ 
docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification
.md (adr)

Summary:
  Added 1 file, 1 episode
ADR-ARCH-017 seeded — 9 nodes, 26 edges. Now re-seeding ADR-ARCH-008 with the partial-supersession status block (force-overwrite required since it already exists).

Bash Re-seed ADR-ARCH-008 with partial-supersession status
IN
guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md --type adr -f -v 2>&1 | tail -40

OUT
Command running in background with ID: b2dxdkwtt. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/3ba1f358-e1c0-4d11-b23f-00ac2201c6e2/tasks/b2dxdkwtt.output
ADR-ARCH-008 re-seeding kicked off in background (LLM extraction takes a few minutes). I'll let the runtime notify on completion rather than polling.

ScheduleWakeup
IN
{
  "delaySeconds": 240,
  "reason": "Wait for ADR-ARCH-008 re-seed to finish; first ADR took ~3min, allow buffer.",
  "prompt": "Continue the /arch-refine wrap-up: the ADR-ARCH-008 re-seed background task should now have finished. Read its output file to confirm completion, then report final summary (both ADRs seeded, file counts, anything noteworthy from the seeding logs)."
}
OUT
Next wakeup scheduled for 10:15:00 (in 233s).
Waking back up in ~4 minutes when the re-seed should be done.

Bash Read re-seed output
IN
tail -25 /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/3ba1f358-e1c0-4d11-b23f-00ac2201c6e2/tasks/b2dxdkwtt.output

OUT
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

Parsing docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md with 
adr
  Found 1 episodes
    - adr_adr-arch-008-mcp-only-for-agent-access-single-user-auth-posture (adr)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [6] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [5] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [8] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 382842.9489135742 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-008-mcp-only-for-agent-access-single-user-auth-posture]: nodes=30, edges=41, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md (adr)

Summary:
  Added 1 file, 1 episode
Re-seed complete — ADR-ARCH-008 now reflects the partial-supersession status in the knowledge graph. Final results:

Graphiti seeding summary:

ADR	Status	Nodes	Edges	Invalidated	Duration
ADR-ARCH-017 (new)	seeded	9	26	0	~3min
ADR-ARCH-008 (re-seed)	overwritten	30	41	0	~6min
The vLLM duplicate-detection warnings on ADR-ARCH-008 are non-fatal — the model returned out-of-range indices for duplicate_facts and Graphiti handled it gracefully. Both ADRs are now queryable via mcp__graphiti__search_nodes / search_memory_facts against the architecture_decisions group.

Note on invalidated=0: Graphiti preserved both the old and new ADR-ARCH-008 facts with timestamps rather than invalidating prior ones — that's the canonical temporal-superseding behaviour. Queries return the most recent facts by updated_at, but the historical "Accepted, classification stable across phases" assertion remains in the graph for audit. This is what we want.

/arch-refine — complete
Final state of the refinement:

1 new ADR (ADR-ARCH-017) and 1 partial supersession (ADR-ARCH-008).
8 downstream artefacts updated to reflect the sync classification — domain-model, container.md, ARCHITECTURE.md index, design/README.md, phase-0-scope.md, phase-0-build-plan.md, adapter.py, server.py.
8/8 MCP unit tests passing — the runtime tool description on tutor_start_session now matches handler behaviour, resolving the SR-07 violation.
Both ADRs seeded into Graphiti with full audit trail.
The Phase 0 SR-07 contract is now consistent end-to-end: ADR → architecture text → design docs → scope/build-plan docs → registered MCP tool description → handler behaviour. Phase 1's reversion path is documented and conditional on the Graphiti latency spike measurement.

Ready to commit when you are. Suggested commit subject: arch: reclassify tutor_start_session as sync (ADR-ARCH-017, supersedes ARCH-008 SR-07).

The wrap-up already completed in the prior turn when the task-notification fired — the scheduled wakeup raced with the actual completion notification. Re-stating the final state for clarity:

Both seeds confirmed complete:

ADR-ARCH-017 (new) — 9 nodes, 26 edges, 0 invalidated, ~3min
ADR-ARCH-008 (re-seed) — 30 nodes, 41 edges, 0 invalidated, ~6min
Noteworthy from logs:

vLLM duplicate_facts warnings on ADR-ARCH-008 — model returned out-of-range indices; Graphiti handled gracefully, non-fatal.
invalidated=0 is correct — Graphiti preserves both old and new facts with timestamps rather than deleting prior ones (canonical temporal-superseding behaviour). Recency-ordered queries return the new "Partially superseded" status; the historical "Accepted / stable across phases" claim stays in the graph for audit.
Full refinement is done: 1 new ADR, 1 partial supersession, 8 downstream artefacts aligned, 8/8 MCP tests green, both ADRs seeded. SR-07 contract now consistent end-to-end. No further work pending — ready for commit when you want.

thanks so I ran this /arch-refine as the summary for /system-plan presented this:
Seeded. 1 episode added (3 nodes, 2 edges) in 44s. Warnings are non-blocking — they're project_overview-schema heuristics that don't apply to a sequencing doc.

📋 /system-plan complete

Action	Result
Mode	Refine → hand-off ([F])
Architecture refinement	None — ARCHITECTURE.md, ADRs, domain-model unchanged
Output	docs/planning/feature-roadmap.md (210 lines, 2 Mermaid diagrams)
Graphiti seeding	✓ architecture_decisions group
Architecture follow-ups identified	D1, D2, SR-08, SR-09 — bundle into one /arch-refine
Recommended next command:


/arch-refine \
  --target docs/architecture/domain-model.md \
  --context docs/design/README.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context docs/research/ideas/phase-1-scope.md
That clears D1 + D2 + adds SR-08 / SR-09 before the Sat 26 Apr Graphiti spike kicks off Phase 1. Then Phase 0 close-out: /feature-spec + /feature-plan for FEAT-PO-004 Bedrock validation

Please can you update /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/phase-0-build-plan.md with the status and confirm the next steps because it looks like the next steps should be:
# Phase 1 re-runs (recommended Sat 26 Apr morning, after phase-1-scope.md is
# drafted and the Graphiti spike has produced latency numbers — DEC-02/DEC-08):
/system-design --focus="Knowledge & Curriculum" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/rag-grounding-design.md \
  --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md
/system-design --focus="Student Model" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md \
  --context docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md
Let me check current state of the build-plan punch-list and find the SR-08/SR-09 references the /system-plan summary mentioned.

Bash Find SR-08 and SR-09 references
IN
grep -n "SR-08\|SR-09" docs/research/ideas/phase-1-scope.md docs/research/ideas/phase-0-build-plan.md docs/architecture/ARCHITECTURE.md docs/planning/feature-roadmap.md 2>/dev/null

OUT
docs/planning/feature-roadmap.md:81:- **SR-08** Graphiti write-back asynchrony — session-end write must not block `tutor_session_end` reply.
docs/planning/feature-roadmap.md:82:- **SR-09** Runtime LLM parameters are explicit and asserted — no implicit defaults at the boundary.
docs/planning/feature-roadmap.md:200:    Arch follow-ups (D1, D2, SR-08/09)   :archref, 2026-04-27, 2d
docs/planning/feature-roadmap.md:229:# 1. Architecture follow-ups (D1 + D2 + SR-08/09 in one session)
docs/planning/feature-roadmap.md:278:*Next:* `/arch-refine` for D1/D2 + SR-08/09, then Phase 1 design re-runs, then per-feature `/feature-spec` → `/feature-plan` → `/feature-build` or `/task-work`.
docs/research/ideas/phase-1-scope.md:17:- **R5 (runtime-param smoke assertion)** → new structural requirement **SR-09** below.
docs/research/ideas/phase-1-scope.md:40:The seven structural requirements from Phase 0 (SR-01 through SR-07) remain load-bearing. Every Phase 1 feature maintains them. The Graphiti latency spike adds one new structural consideration — **SR-08: Graphiti write-back is asynchronous from the caller's perspective** — which is notionally deferred work but is decided early in Phase 1 based on measurement.
docs/research/ideas/phase-1-scope.md:42:### SR-08: Graphiti write-back asynchrony
docs/research/ideas/phase-1-scope.md:50:**Coupling to the spike.** If the Saturday morning spike shows end-to-end Graphiti write latency under 2 seconds consistently, SR-08 is still the right shape (defensive) but the "real" impact is small. If latency exceeds 5 seconds, SR-08 is load-bearing and shapes every feature.
docs/research/ideas/phase-1-scope.md:52:### SR-09: Runtime LLM parameters are explicit and asserted
docs/research/ideas/phase-1-scope.md:72:Before any schema work, measure the three-hop latency end-to-end. This resolves DEC-02 / DEC-08 ambiguity and locks SR-08 + the Phase 0 MCP tool classification.
docs/research/ideas/phase-1-scope.md:83:- If add_episode median > 5s: SR-08 async write-back is critical, possibly fire-and-forget from multiple points not just session-end
docs/research/ideas/phase-1-scope.md:147:- `record_session_completion(student_id, session_summary)` — async write-back per SR-08
docs/research/ideas/phase-1-scope.md:241:When Coach rejects a turn for `curriculum_accuracy < 0.5` or identifies a misconception in a student answer that the Player addressed, record a `misconception_observed` episode per FEAT-PH1-001 item 2. Async per SR-08.
docs/research/ideas/phase-1-scope.md:254:Written to Graphiti as a `session_completed` episode, asynchronously per SR-08.
docs/research/ideas/phase-1-scope.md:337:- **Graphiti write-back is always async from the caller's perspective** — SR-08. Even if the spike shows low latency.
docs/research/ideas/phase-1-scope.md:381:14. **SR-09 smoke assertion passes.** `ollama show` and runner log grep both confirm `num_ctx` and `num_predict` reach the runner at Modelfile-declared values. Regression test added to CI (or manual walkthrough if CI absent in Phase 1).
Read phase-0-build-plan.md (lines 38-112)
Now I have the full picture. The /system-plan summary identified four follow-ups; this /arch-refine run addressed D2 only. D1 was reviewed and confirmed as no-action (fits within architecture envelope). SR-08 and SR-09 are Phase 1 structural requirements already documented in phase-1-scope.md §SR-08–§SR-09 but not yet captured in an ADR.

Let me update the build-plan with the D2 resolution status, then walk through next steps.

Edit phase-0-build-plan.md
Modified
Edit phase-0-build-plan.md
Modified
Build-plan punch-list updated — D2 marked CLOSED with ADR-ARCH-017 reference, header date bumped to 2026-04-27.

On the next steps you pasted
Your two /system-design --focus=... commands are correct in shape, but the sequencing in phase-1-scope.md:72 says the Graphiti latency spike must run first:

Before any schema work, measure the three-hop latency end-to-end. This resolves DEC-02 / DEC-08 ambiguity and locks SR-08 + the Phase 0 MCP tool classification.

So the right order is:

Graphiti latency spike — measures add_episode and search_nodes latencies on the FalkorDB Synology + Gemini + GB10 split topology. Per phase-1-scope.md L83-85, the result determines:
Whether SR-08 (async write-back) is "still defensive shape" (latency <2s) or "load-bearing throughout features" (latency >5s).
Whether the SR-07 classification we just locked in ADR-ARCH-017 holds (sync), or needs reversion to long-running (if search_nodes median > ~3s).
Bundle SR-08 + SR-09 (+ any SR-07 reversion) into one /arch-refine. This is the recommendation the /system-plan summary made. After the spike the inputs are concrete.
Then your two /system-design --focus= re-runs — Knowledge & Curriculum and Student Model. They'll consume the ADR-ified SR-08 and the spike result.
What's still open from /system-plan's four-item bundle
Item	Status	What's needed
D1 — TutorSession P0-only shape	✅ No action (fits within architecture envelope; you confirmed earlier)	—
D2 — tutor_start_session sync	✅ CLOSED via ADR-ARCH-017	—
SR-08 — Graphiti write-back asynchrony	📝 Documented in phase-1-scope.md §SR-08; not yet in any ADR	Spike result → /arch-refine to elevate to a CC alongside SR-01–07 (likely refines ADR-ARCH-009)
SR-09 — Runtime LLM parameter explicitness	📝 Documented in phase-1-scope.md §SR-09; not yet in any ADR	Spike-independent; can /arch-refine ADR-ARCH-009 to add SR-09 anytime
The /system-plan bundle recommendation makes sense because SR-08 + SR-09 + potential SR-07 reversion all touch ADR-ARCH-009 ("Six parity surfaces as load-bearing CC") — so refining ARCH-009 once with all three is cleaner than three separate runs.

Suggested sequence

# 1. Run the Graphiti latency spike (per phase-1-scope.md §"Graphiti latency spike").
#    Produces the empirical numbers that lock SR-08 and confirm/revert SR-07.
#    Targets per phase-1-scope.md L83-85: add_episode median, search_nodes median.

# 2. Post-spike: bundle SR-08 + SR-09 (+ SR-07 reversion if needed) into one /arch-refine.
#    Likely refines ADR-ARCH-009 (six parity surfaces → eight) — though ARCH-017's reversion
#    rule already covers SR-07, so the bundle may shrink to just SR-08/09 if the spike
#    confirms <3s search_nodes latency.

/arch-refine --adr=ADR-ARCH-009 \
  --context docs/research/ideas/phase-1-scope.md \
  --context <spike-results-doc>

# 3. Then the Phase 1 design re-runs (your pasted commands):

/system-design --focus="Knowledge & Curriculum" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/rag-grounding-design.md \
  --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md

/system-design --focus="Student Model" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md \
  --context docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md

# 4. In parallel (independent of P1): Phase 0 close-out for FEAT-PO-004 Bedrock validation.
/feature-spec FEAT-PO-004
/feature-plan FEAT-PO-004
Optional — if you want to skip the spike-first sequencing
If the Graphiti spike is going to slip and you want to unblock Phase 1 design work now, you can run the two /system-design --focus= commands using the current SR-07 sync classification (ADR-ARCH-017) and accept that SR-08 stays as a phase-1-scope.md item rather than a CC. The risk is: if the spike later forces an SR-07 reversion, the design artefacts produced by the focus runs will need re-running. Probably not worth the rework — better to do the spike first.

Recommendation: spike Saturday morning as originally planned, then bundle-refine, then design re-runs. That's the path of least churn.

thanks, please can you rovide details on how to run : 1. Run the Graphiti latency spike (per phase-1-scope.md §"Graphiti latency spike").
Let me read the spike spec in phase-1-scope.md and check whether any spike scaffolding already exists in the repo.

Bash Find spike spec sections in phase-1-scope
IN
grep -n "Graphiti latency spike\|latency spike\|add_episode\|search_nodes" docs/research/ideas/phase-1-scope.md | head -30

OUT
40:The seven structural requirements from Phase 0 (SR-01 through SR-07) remain load-bearing. Every Phase 1 feature maintains them. The Graphiti latency spike adds one new structural consideration — **SR-08: Graphiti write-back is asynchronous from the caller's perspective** — which is notionally deferred work but is decided early in Phase 1 based on measurement.
75:- Time a single `add_episode` call from the MacBook against FalkorDB on Synology with Gemini entity extraction and GB10 embeddings. Expected range: 1–3s if Gemini is fast, 5–8s if not.
76:- Time a `search_nodes` query by group_id with a topic-confidence filter. Expected range: 0.5–2s.
83:- If add_episode median > 5s: SR-08 async write-back is critical, possibly fire-and-forget from multiple points not just session-end
84:- If search_nodes median > 3s: `tutor_start_session` stays long-running (Phase 0 classification holds)
85:- If search_nodes median < 1s: `tutor_start_session` could be reclassified as sync, simplifying the MCP tool shape
142:Thin Python wrappers around Graphiti's search_nodes / search_memory_facts / add_episode patterns, specialised for this schema. Per the specialist-agent pattern (`src/specialist_agent/tools/graphiti_query.py`) use lazy import so the module loads even when graphiti-core isn't installed (graceful degradation per LES1 §3 `.env` hygiene concerns).
355:1. **Graphiti latency spike published.** `docs/research/ideas/graphiti-latency-spike-results.md` exists, contains real measurements from the Saturday morning spike, and informs the tool classification decisions.
Bash Check if spike scaffolding exists
IN
find scripts tests src -name "*spike*" -o -name "*latency*" -o -name "*bench*" 2>/dev/null | head -20; echo "---"; ls scripts/ 2>/dev/null

OUT
---
mcp-wrapper.sh
Read phase-1-scope.md (lines 69-103)
Bash List guardkit graphiti subcommands
IN
guardkit graphiti --help 2>&1 | head -40

OUT
Usage: guardkit-py graphiti [OPTIONS] COMMAND [ARGS]...

  Graphiti knowledge graph management commands.

  Manage the Graphiti knowledge graph that provides persistent memory for
  GuardKit sessions.

Options:
  --help  Show this message and exit.

Commands:
  add-context      Add context from files to Graphiti.
  capture          Capture project knowledge through interactive Q&A.
  capture-outcome  Capture a task-completion outcome to the...
  clear            Clear Graphiti knowledge graph data.
  list             List all knowledge in a category.
  search           Search for knowledge across all categories.
  seed             Seed system context into Graphiti.
  seed-adrs        Seed feature-build ADRs into Graphiti.
  seed-system      Seed template and system content into Graphiti.
  show             Show details of specific knowledge by ID.
  stats            Show graph topology statistics for performance analysis.
  status           Show Graphiti connection and seeding status.
  verify           Verify seeded knowledge with test queries.
Bash Check if any existing project code calls Graphiti
IN
grep -rn "add_episode\|search_nodes\|search_memory_facts" src/study_tutor/ 2>/dev/null | head -10

OUT
(Bash completed with no output)
Bash Check whether graphiti-core is already a project dependency
IN
grep -n "graphiti\|graphiti-core" pyproject.toml 2>&1 | head -10

OUT
(Bash completed with no output)
Here's a concrete recipe. The spike is genuinely new infrastructure — no existing scaffold in the repo (study_tutor package has no Graphiti integration yet, and graphiti-core isn't a project dependency), so it'll be a one-shot script.

Pre-flight checks (5 minutes)
Before writing any code, confirm the three-hop topology is reachable from the MacBook:


# 1. FalkorDB on Synology (whitestocks) over Tailscale
nc -zv whitestocks 6379

# 2. vLLM LLM backend on GB10 (the Qwen2.5-14B FP8 instance)
curl -sS http://promaxgb10-41b1:8000/v1/models | jq '.data[].id'

# 3. vLLM embedder on GB10 (nomic-embed-text-v1.5)
curl -sS http://promaxgb10-41b1:8001/v1/models | jq '.data[].id'

# 4. Verify Graphiti CLI sees the same config
guardkit graphiti status
Config mismatch to flag: phase-1-scope.md §"Latency spike" L75 says "Gemini entity extraction", but .guardkit/graphiti.yaml has the LLM backend on vLLM Qwen2.5-14B on GB10 (the 21 Apr "Unplanned strategic move" in build-plan L52). The expected ranges in the scope doc (1–3s if Gemini is fast, 5–8s if not) were calibrated for Gemini's API profile. vLLM on Tailscale has a different shape — likely steadier per-call but slower per-token. This makes the spike more important, not less, because we're measuring the actual P1 stack rather than the spec's assumed stack.

Existing data point we can already cite
The ADR seeding I ran 90 minutes ago is de facto add_episode data:

ADR-ARCH-017 (smallish ADR): 182,932ms → ~183s
ADR-ARCH-008 (larger ADR): 382,842ms → ~383s
That's catastrophically slower than the 1–3s "fast Gemini" expected range. But the comparison is unfair: ADRs are ~5–10KB documents that produce 9–30 nodes and 26–41 edges per episode — large extraction surfaces. A session_completed episode is a tiny structured event (~200 bytes, 1–3 nodes). The spike needs to measure that representative shape, not ADR-sized payloads.

So treat the seeding numbers as upper bounds, not the spike answer.

The spike script

# scripts/graphiti_latency_spike.py
"""Phase 1 prep — three-hop Graphiti latency measurement.

Per phase-1-scope.md §"Latency spike". Measures add_episode,
search_nodes, search_memory_facts on representative session-shape
payloads against the vLLM-on-GB10 config in .guardkit/graphiti.yaml.

Run: uv run python scripts/graphiti_latency_spike.py > docs/research/ideas/graphiti-latency-spike-results.md
"""
import asyncio
import statistics
import time
from datetime import datetime, timezone

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

# Config matches .guardkit/graphiti.yaml
FALKOR_HOST = "whitestocks"
FALKOR_PORT = 6379
LLM_BASE_URL = "http://promaxgb10-41b1:8000/v1"
LLM_MODEL = "neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic"
EMBED_BASE_URL = "http://promaxgb10-41b1:8001/v1"
EMBED_MODEL = "nomic-embed-text-v1.5"

GROUP_ID = "spike-test-lilymay"  # Throwaway namespace; clear after spike

# Representative session-shape payload (Shared Kernel B event)
SESSION_EPISODE = """
session_completed: {
  session_id: "test-session-uuid",
  student_id: "lilymay",
  subject: "English Literature",
  topic: "macbeth:act1:witches",
  duration_seconds: 1247,
  aos_touched: ["AO1", "AO2"],
  quality_score: 0.78,
  ended_at: "2026-04-27T10:00:00Z"
}
""".strip()


async def time_op(label: str, fn, n: int = 3):
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        await fn()
        elapsed = time.perf_counter() - t0
        times.append(elapsed)
        print(f"  run {i+1}: {elapsed:.2f}s", flush=True)
    return {
        "label": label,
        "min": min(times),
        "median": statistics.median(times),
        "max": max(times),
    }


async def main():
    g = Graphiti(
        uri=f"falkor://{FALKOR_HOST}:{FALKOR_PORT}",
        # ... pass LLM and embedder config; mirror what guardkit/graphiti uses
    )

    # 1. add_episode (3 runs)
    async def write():
        await g.add_episode(
            name=f"session_{datetime.now(timezone.utc).isoformat()}",
            episode_body=SESSION_EPISODE,
            source=EpisodeType.json,
            source_description="phase-1 latency spike",
            reference_time=datetime.now(timezone.utc),
            group_id=GROUP_ID,
        )
    add_results = await time_op("add_episode", write)

    # 2. search_nodes by group_id
    async def search_nodes():
        await g.search_nodes(query="macbeth witches confidence", group_ids=[GROUP_ID])
    search_node_results = await time_op("search_nodes", search_nodes)

    # 3. search_memory_facts
    async def search_facts():
        await g.search(query="quality_score for Lilymay on Macbeth", group_ids=[GROUP_ID])
    search_facts_results = await time_op("search_memory_facts", search_facts)

    # Output markdown table
    print()
    print("| Operation | Min (s) | Median (s) | Max (s) |")
    print("|---|---|---|---|")
    for r in (add_results, search_node_results, search_facts_results):
        print(f"| `{r['label']}` | {r['min']:.2f} | {r['median']:.2f} | {r['max']:.2f} |")


if __name__ == "__main__":
    asyncio.run(main())
The Graphiti client init details (LLM + embedder config) are slightly fiddly — easiest is to copy-paste from guardkit.knowledge.graphiti_client (which already wires up the vLLM endpoints from .guardkit/graphiti.yaml). I haven't read that file in this session, but guardkit graphiti add-context clearly works against this stack so the wiring exists.

Run + write up

# 1. Add graphiti-core to dev dependencies temporarily
uv add --dev graphiti-core

# 2. Run the spike (allow 5–10 minutes — the LLM extraction step is the long pole)
uv run python scripts/graphiti_latency_spike.py | tee /tmp/spike.txt

# 3. Clean up the throwaway test namespace so it doesn't pollute architecture_decisions
guardkit graphiti clear --group spike-test-lilymay  # if --group flag exists; else use Falkor CLI

# 4. Write up the results doc per the scope spec ("two paragraphs max + measurements table")
$EDITOR docs/research/ideas/graphiti-latency-spike-results.md
The results doc per phase-1-scope.md:80 should be two paragraphs plus the table. Suggested skeleton:


# Graphiti Latency Spike — Results

**Date:** 2026-04-27 (Saturday morning slot, slipped from 26 Apr)
**Stack measured:** FalkorDB on whitestocks (Synology, Tailscale) + vLLM Qwen2.5-14B-FP8 on
promaxgb10-41b1:8000 (LLM extraction) + vLLM nomic-embed-text-v1.5 on :8001 (embeddings).
**Note:** This is the actual P1 stack post the 21 Apr Gemini→vLLM migration — different from
the Gemini-assumed ranges in `phase-1-scope.md §"Latency spike"`.

## Measurements

| Operation | Min (s) | Median (s) | Max (s) |
|---|---|---|---|
| `add_episode`         | … | … | … |
| `search_nodes`        | … | … | … |
| `search_memory_facts` | … | … | … |

## Decisions unblocked

- **SR-08 (async write-back).** [Critical / defensive — based on add_episode median per L83.]
- **SR-07 / `tutor_start_session` classification.** [ADR-ARCH-017 sync classification holds /
  needs reversion to long-running — based on search_nodes median per L84-85.]
- **DEC-02 / DEC-08.** [Resolved by these numbers — [brief one-line conclusion].]
What the result triggers
Result band	Action
add_episode median ≤ 5s	SR-08 stays defensive (still required, but not load-bearing-throughout)
add_episode median > 5s	SR-08 escalates — async fire-and-forget from multiple write points, not just session-end
search_nodes median < 1s	ADR-ARCH-017 sync classification confirmed, no further action
search_nodes median 1–3s	ADR-ARCH-017 sync classification probably holds (margin is OK), document the actual median in the ADR's reversion footnote
search_nodes median > 3s	Run /arch-refine --adr=ADR-ARCH-017 to revert tutor_start_session to long-running, add the _status/_cancel companion, update server.py and downstream artefacts
Want me to write the spike script?
I can write scripts/graphiti_latency_spike.py properly (with the correct Graphiti client config wiring from the guardkit module) and add graphiti-core to dev deps in a single pass. ~10 minutes.

What I can't do:

Run the spike against the live Tailscale stack (needs your machine, your Tailscale auth, and may need vLLM warm-up — fine to do interactively but not from this session).
Author the results doc with real numbers (you have to run the script first).
Want me to draft the script? Or would you rather scaffold it yourself and just have me cross-check it before you run?

<task-notification>
<task-id>bk1qjjnrn</task-id>
<tool-use-id>toolu_01Dz6fWokmaa9oGqDYsShFno</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/3ba1f358-e1c0-4d11-b23f-00ac2201c6e2/tasks/bk1qjjnrn.output</output-file>
<status>completed</status>
<summary>Background command "Locate guardkit graphiti_client" completed (exit code 0)</summary>
</task-notification>
thanks can you create he script and run that using the Bash tool? Save the manual overhead of me driving/orchestrating and pasting results back intot he chat window
Reading the existing graphiti-client wiring so the spike script uses the same config pattern.

Bash Locate guardkit graphiti_client
IN
find / -name "graphiti_client.py" -path "*/guardkit/*" 2>/dev/null | head -3

OUT
Command running in background with ID: bk1qjjnrn. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/3ba1f358-e1c0-4d11-b23f-00ac2201c6e2/tasks/bk1qjjnrn.output
Bash Find installed guardkit location
IN
python -c "import guardkit; print(guardkit.__file__)" 2>&1 || python3 -c "import guardkit; print(guardkit.__file__)" 2>&1

OUT
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/__init__.py
Bash List guardkit graphiti modules
IN
find /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit -name "graphiti*.py" 2>/dev/null | head -10

OUT
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/planning/graphiti_arch.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/planning/graphiti_design.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti_query_commands.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py
Bash Stop the find background task
IN
kill %1 2>/dev/null; sleep 1; echo done

OUT
done
Read graphiti_client.py (lines 2-121)
Bash Map key entry points in GraphitiClient
IN
grep -n "class GraphitiConfig\|def init_graphiti\|def get_graphiti\|async def add_episode\|async def search\b\|async def search_nodes" /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py | head -20

OUT
135:class GraphitiConfig:
1084:    async def search(
1283:    async def add_episode(
2365:async def init_graphiti(config: Optional[GraphitiConfig] = None) -> bool:
2460:def get_graphiti() -> Optional[GraphitiClient]:
Bash Find GraphitiConfig definition
IN
find /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit -name "*.py" | xargs grep -ln "class GraphitiConfig\|GraphitiConfig.from_yaml\|GraphitiConfig(" 2>/dev/null | head -5

OUT
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/init.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/seeding.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/seed_failed_approaches.py
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/__init__.py
Bash Read GraphitiConfig dataclass
IN
sed -n '135,210p' /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py

OUT
class GraphitiConfig:
    """Configuration for Graphiti connection via graphiti-core.

    This is a frozen (immutable) dataclass to ensure configuration
    cannot be modified after creation.

    Attributes:
        enabled: Whether Graphiti integration is enabled
        neo4j_uri: Neo4j Bolt URI (e.g., 'bolt://localhost:7687')
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        timeout: Connection timeout in seconds
        project_id: Project ID for namespace prefixing (optional)
        graph_store: Graph database backend ('neo4j' or 'falkordb')
        falkordb_host: FalkorDB host for connection
        falkordb_port: FalkorDB port for connection
        host: Deprecated - use neo4j_uri instead (kept for backwards compatibility)
        port: Deprecated - use neo4j_uri instead (kept for backwards compatibility)
        llm_provider: LLM provider for entity extraction ('openai', 'vllm', 'ollama', 'gemini')
        llm_base_url: LLM provider base URL (required for vllm/ollama; ignored for gemini)
        llm_model: LLM model name (e.g., 'Qwen/Qwen3-Coder-30B-A3B', 'gemini-2.5-flash')
        embedding_provider: Embedding provider ('openai', 'vllm', 'ollama')
        embedding_base_url: Embedding provider base URL (required for vllm/ollama)
        embedding_model: Embedding model name (e.g., 'text-embedding-3-small')
        embedding_dimensions: Explicit embedding vector dimensions (optional). When set,
            used in place of KNOWN_EMBEDDING_DIMS for the pre-flight dimension check.

    Raises:
        ValueError: If timeout is not positive
        ValueError: If project_id is invalid (>50 chars or invalid characters)
        ValueError: If graph_store is not 'neo4j' or 'falkordb'
        ValueError: If llm_provider is not one of VALID_PROVIDERS
        ValueError: If embedding_provider is not one of VALID_PROVIDERS
        ValueError: If llm_base_url is missing when llm_provider is 'vllm' or 'ollama'
        ValueError: If embedding_base_url is missing when embedding_provider is 'vllm' or 'ollama'

    Example:
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://graphiti.example.com:7687",
            neo4j_user="neo4j",
            neo4j_password="password123",
            timeout=60.0,
            project_id="my-project"
        )
    """
    enabled: bool = True
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"
    timeout: float = 30.0
    project_id: Optional[str] = None  # Project ID for namespace prefixing
    graph_store: str = "neo4j"  # 'neo4j' or 'falkordb'
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    # Deprecated fields for backwards compatibility
    host: str = "localhost"
    port: int = 8000
    # LLM and embedding provider configuration
    llm_provider: str = "openai"           # "openai" | "vllm" | "ollama" | "gemini"
    llm_base_url: Optional[str] = None     # e.g., "http://host:8000/v1"; unused for gemini
    llm_model: Optional[str] = None        # e.g., "Qwen/Qwen3-Coder-30B-A3B"
    llm_max_tokens: Optional[int] = None   # Cap output tokens (e.g. 4096 for 8192-ctx models)
    embedding_provider: str = "openai"     # "openai" | "vllm" | "ollama"
    embedding_base_url: Optional[str] = None  # e.g., "http://host:8001/v1"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: Optional[int] = None  # explicit dimensions (e.g. 1024 for Matryoshka)
    # Concurrency control for parallel episode seeding
    max_concurrent_episodes: int = 3       # Max concurrent episode creation calls (>=1)

    def __post_init__(self):
        """Validate and normalize configuration values."""
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")
        if self.graph_store not in ("neo4j", "falkordb"):
            raise ValueError(f"graph_store must be 'neo4j' or 'falkordb', got '{self.graph_store}'")
Bash Find config-loading helper
IN
grep -n "from_yaml\|load.*config\|read.*yaml\|graphiti.yaml" /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py 2>/dev/null | head -20

OUT
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py:312:                "Set project_id in .guardkit/graphiti.yaml for consistent behavior."
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py:688:                "Check embedding_provider/embedding_model in .guardkit/graphiti.yaml",
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py:2404:    Creates a GraphitiClientFactory from load_graphiti_config() and
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py:2422:        from guardkit.knowledge.config import load_graphiti_config
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py:2423:        settings = load_graphiti_config()
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py:35:from guardkit.knowledge.config import load_graphiti_config, GraphitiSettings
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py:82:    settings = load_graphiti_config()
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py:287:    settings = load_graphiti_config()
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py:294:        console.print("  [dim]Enable in config/graphiti.yaml[/dim]")
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py:588:        settings = load_graphiti_config()
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py:590:        console.print(f"[red]Error loading config: {e}[/red]")
/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py:1194:    settings = load_graphiti_config()
Bash See how CLI bridges GraphitiSettings → GraphitiConfig + init_graphiti
IN
sed -n '78,160p' /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/cli/graphiti.py

OUT
    Returns:
        Tuple of (GraphitiClient, GraphitiSettings)
    """
    settings = load_graphiti_config()
    config = GraphitiConfig(
        enabled=settings.enabled,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        timeout=settings.timeout,
        project_id=settings.project_id,
        graph_store=settings.graph_store,
        falkordb_host=settings.falkordb_host,
        falkordb_port=settings.falkordb_port,
        llm_provider=settings.llm_provider,
        llm_base_url=settings.llm_base_url,
        llm_model=settings.llm_model,
        llm_max_tokens=settings.llm_max_tokens,
        embedding_provider=settings.embedding_provider,
        embedding_base_url=settings.embedding_base_url,
        embedding_model=settings.embedding_model,
        embedding_dimensions=getattr(settings, "embedding_dimensions", None),
    )
    client = GraphitiClient(config)
    return client, settings


async def _cmd_seed(force: bool, template: Optional[str] = None, episode_timeout: Optional[float] = None) -> None:
    """Async implementation of seed command."""
    console.print("[bold blue]Graphiti System Context Seeding[/bold blue]")
    console.print()

    # Check if already seeded
    if is_seeded() and not force:
        console.print("[yellow]System context already seeded.[/yellow]")
        console.print("Use --force to re-seed.")
        return

    # Create client
    client, settings = _get_client_and_config()

    # Apply CLI --timeout override to client
    if episode_timeout is not None:
        client.default_timeout_override = episode_timeout

    # Initialize connection
    console.print(f"Connecting to {_format_connection_target(settings)}...")

    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)

    try:
        if not initialized or not client.enabled:
            console.print("[yellow]Graphiti not available or disabled.[/yellow]")
            console.print("Seeding skipped. Check your Graphiti configuration.")
            return

        console.print("[green]Connected to Graphiti[/green]")
        console.print()

        # Pre-seed LLM endpoint check (vLLM/ollama only)
        if settings.llm_provider in ("vllm", "ollama") or settings.embedding_provider in ("vllm", "ollama"):
            console.print("Checking LLM endpoint availability...")
            console.print("[dim]Waiting for vLLM... (timeout 60s)[/dim]")
            llm_ready = await client.wait_for_llm_endpoints(timeout=60.0)
            if llm_ready:
                console.print("[green]LLM endpoints ready[/green]")
            else:
                console.print(
                    "[yellow]Warning: LLM endpoints not available after 60s.[/yellow]"
                )
                console.print(
                    "[yellow]Seeding will likely fail. "
                    "Check that vLLM is running.[/yellow]"
                )
                raise SystemExit(1)
            console.print()

        # Clear marker if forcing
Bash Read add_episode and search method signatures
IN
sed -n '1280,1330p' /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py; echo "==="; sed -n '1080,1130p' /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py

OUT
        metadata_block = f"\n\n---\n_metadata:\n```json\n{metadata_json}\n```"
        return content + metadata_block

    async def add_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str,
        scope: Optional[str] = None,
        metadata: Optional["EpisodeMetadata"] = None,
        source: str = "user_added",
        entity_type: str = "generic",
        timeout_override: Optional[float] = None,
    ) -> Optional[str]:
        """Add episode with graceful degradation.

        Creates a new episode (knowledge entry) in Graphiti.
        Returns None on any error to ensure graceful degradation.

        Args:
            name: Episode name/title
            episode_body: Episode content (can be empty)
            group_id: Group ID for organization
            scope: Optional scope override ("project" or "system").
                   If None, auto-detects based on group name.
            metadata: Optional EpisodeMetadata to inject. If None, auto-generates.
            source: Source of the episode (default: "user_added").
            entity_type: Type of entity (default: "generic").
            timeout_override: If set, overrides the group-based timeout (seconds).

        Returns:
            Episode UUID if successful, None if:
            - Client not enabled
            - Creation fails
            - Connection error

        Example:
            episode_id = await client.add_episode(
                name="OAuth2 Implementation Decision",
                episode_body="Decided to use OAuth2 with PKCE flow...",
                group_id="architecture_decisions"
            )
        """
        if not self.config.enabled:
            return None

        # Import EpisodeMetadata here to avoid circular imports
        from guardkit.integrations.graphiti.metadata import EpisodeMetadata

        # Auto-generate metadata if not provided
        if metadata is None:
===
            logger.warning(f"Search request failed: {e}")
            self._record_failure()
            return []

    async def search(
        self,
        query: str,
        group_ids: Optional[List[str]] = None,
        num_results: int = 10,
        scope: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search Graphiti with graceful degradation.

        Searches the knowledge graph for relevant information.
        Returns empty list on any error to ensure graceful degradation.

        Args:
            query: Search query string
            group_ids: Optional list of group IDs to search in.
                       If None, searches all groups.
            num_results: Maximum number of results (default: 10)
            scope: Optional scope override ("project" or "system").
                   If None, auto-detects based on group names.

        Returns:
            List of search results as dictionaries.
            Empty list if:
            - Client not enabled
            - Search fails
            - Connection error

        Example:
            results = await client.search(
                query="authentication patterns",
                group_ids=["architecture_decisions"],
                num_results=5
            )
        """
        if not self.config.enabled:
            return []

        try:
            # Apply prefixing to group_ids if provided
            prefixed_group_ids = None
            if group_ids is not None:
                prefixed_group_ids = [
                    self._apply_group_prefix(gid, scope) for gid in group_ids
                ]

            results = await self._execute_search(
                query=query,
Bash Find search_nodes / underlying graphiti exposure
IN
grep -n "search_nodes\|search_memory_facts\|self\._graphiti\b" /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/knowledge/graphiti_client.py | head -25

OUT
280:        self._graphiti = None  # Will hold the Graphiti instance
649:        if not self._graphiti or not self._connected:
705:        if not self._graphiti or not hasattr(self._graphiti, "_driver"):
708:        driver = self._graphiti._driver
789:        if not self._connected or not self._graphiti:
795:            await self._graphiti.search("health_check_test", num_results=1)
874:                self._graphiti = Graphiti(graph_driver=driver, **extra_kwargs)
876:                self._graphiti = Graphiti(
887:                self._graphiti.build_indices_and_constraints(),
910:            if self._graphiti:
912:                    await self._graphiti.close()
915:                self._graphiti = None
1031:        if not self._graphiti:
1044:            search_results = await self._graphiti.search_(
1175:        if not self._graphiti:
1209:                    self._graphiti.add_episode(
1410:        if not self._graphiti:
1596:        if not self._graphiti:
1609:            results = await self._graphiti.search(
1692:        if not self._graphiti or not self._connected:
1696:            driver = getattr(self._graphiti, 'driver', None)
1764:        if not self._graphiti or not self._connected:
1769:            driver = getattr(self._graphiti, 'driver', None)
1793:        if not self._graphiti or not self._connected:
1797:            driver = getattr(self._graphiti, 'driver', None)
Bash Check if guardkit + graphiti-core are reachable from study-tutor venv
IN
uv run python -c "import guardkit, graphiti_core; print('ok'); print(guardkit.__file__); print(graphiti_core.__version__)" 2>&1 | tail -10

OUT
warning: `VIRTUAL_ENV=/Library/Frameworks/Python.framework/Versions/3.14` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'guardkit'
Bash Find guardkit's Python interpreter
IN
which guardkit; head -3 $(which guardkit) 2>&1; echo "---"; ls /Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python 2>&1

OUT
/Users/richardwoollcott/.agentecflow/bin/guardkit
#!/bin/bash

# GuardKit CLI
---
/Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python
Bash Confirm guardkit's venv has graphiti-core
IN
/Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python -c "import guardkit, graphiti_core; print('guardkit:', guardkit.__file__); print('graphiti_core:', graphiti_core.__file__)" 2>&1

OUT
guardkit: /Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/__init__.py
graphiti_core: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/lib/python3.10/site-packages/graphiti_core/__init__.py
Bash Inspect graphiti-core method signatures
IN
/Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python -c "
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
import inspect
print('add_episode sig:')
print(inspect.signature(Graphiti.add_episode))
print()
print('search_nodes sig:')
print(inspect.signature(Graphiti.search_nodes))
print()
print('search_ sig:')
print(inspect.signature(Graphiti.search_))
print()
print('EpisodeType:', list(EpisodeType))
" 2>&1 | tail -20

OUT
Traceback (most recent call last):
  File "<string>", line 9, in <module>
AttributeError: type object 'Graphiti' has no attribute 'search_nodes'
add_episode sig:
(self, name: str, episode_body: str, source_description: str, reference_time: datetime.datetime, source: graphiti_core.nodes.EpisodeType = <EpisodeType.message: 'message'>, group_id: str | None = None, uuid: str | None = None, update_communities: bool = False, entity_types: dict[str, type[pydantic.main.BaseModel]] | None = None, excluded_entity_types: list[str] | None = None, previous_episode_uuids: list[str] | None = None, edge_types: dict[str, type[pydantic.main.BaseModel]] | None = None, edge_type_map: dict[tuple[str, str], list[str]] | None = None, custom_extraction_instructions: str | None = None, saga: str | graphiti_core.nodes.SagaNode | None = None, saga_previous_episode_uuid: str | None = None) -> graphiti_core.graphiti.AddEpisodeResults

search_nodes sig:
Bash Find actual search methods on Graphiti class
IN
/Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python -c "
from graphiti_core import Graphiti
methods = [m for m in dir(Graphiti) if not m.startswith('_') and 'search' in m.lower()]
print('Graphiti search methods:', methods)
import inspect
for m in methods:
    print(f'  {m}: {inspect.signature(getattr(Graphiti, m))}')
" 2>&1 | tail -15

OUT
Graphiti search methods: ['search', 'search_']
  search: (self, query: str, center_node_uuid: str | None = None, group_ids: list[str] | None = None, num_results=10, search_filter: graphiti_core.search.search_filters.SearchFilters | None = None, driver: graphiti_core.driver.driver.GraphDriver | None = None) -> list[graphiti_core.edges.EntityEdge]
  search_: (self, query: str, config: graphiti_core.search.search_config.SearchConfig = SearchConfig(edge_config=EdgeSearchConfig(search_methods=[<EdgeSearchMethod.bm25: 'bm25'>, <EdgeSearchMethod.cosine_similarity: 'cosine_similarity'>, <EdgeSearchMethod.bfs: 'breadth_first_search'>], reranker=<EdgeReranker.cross_encoder: 'cross_encoder'>, sim_min_score=0.6, mmr_lambda=0.5, bfs_max_depth=3), node_config=NodeSearchConfig(search_methods=[<NodeSearchMethod.bm25: 'bm25'>, <NodeSearchMethod.cosine_similarity: 'cosine_similarity'>, <NodeSearchMethod.bfs: 'breadth_first_search'>], reranker=<NodeReranker.cross_encoder: 'cross_encoder'>, sim_min_score=0.6, mmr_lambda=0.5, bfs_max_depth=3), episode_config=EpisodeSearchConfig(search_methods=[<EpisodeSearchMethod.bm25: 'bm25'>], reranker=<EpisodeReranker.cross_encoder: 'cross_encoder'>, sim_min_score=0.6, mmr_lambda=0.5, bfs_max_depth=3), community_config=CommunitySearchConfig(search_methods=[<CommunitySearchMethod.bm25: 'bm25'>, <CommunitySearchMethod.cosine_similarity: 'cosine_similarity'>], reranker=<CommunityReranker.cross_encoder: 'cross_encoder'>, sim_min_score=0.6, mmr_lambda=0.5, bfs_max_depth=3), limit=10, reranker_min_score=0), group_ids: list[str] | None = None, center_node_uuid: str | None = None, bfs_origin_node_uuids: list[str] | None = None, search_filter: graphiti_core.search.search_filters.SearchFilters | None = None, driver: graphiti_core.driver.driver.GraphDriver | None = None) -> graphiti_core.search.search_config.SearchResults
Bash Find node/edge search recipes
IN
/Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python -c "
from graphiti_core.search import search_config_recipes as rec
import graphiti_core.search.search_config_recipes as r
print([x for x in dir(rec) if 'NODE' in x.upper() or 'EDGE' in x.upper() or 'RECIPE' in x.upper()])
" 2>&1 | tail -10

OUT
['EDGE_HYBRID_SEARCH_CROSS_ENCODER', 'EDGE_HYBRID_SEARCH_EPISODE_MENTIONS', 'EDGE_HYBRID_SEARCH_MMR', 'EDGE_HYBRID_SEARCH_NODE_DISTANCE', 'EDGE_HYBRID_SEARCH_RRF', 'EdgeReranker', 'EdgeSearchConfig', 'EdgeSearchMethod', 'NODE_HYBRID_SEARCH_CROSS_ENCODER', 'NODE_HYBRID_SEARCH_EPISODE_MENTIONS', 'NODE_HYBRID_SEARCH_MMR', 'NODE_HYBRID_SEARCH_NODE_DISTANCE', 'NODE_HYBRID_SEARCH_RRF', 'NodeReranker', 'NodeSearchConfig', 'NodeSearchMethod']
I have everything needed. Writing the script now.

Write graphiti_latency_spike.py
418 lines
"""Phase 1 prep — three-hop Graphiti latency spike.

Measures the actual P1 stack:
  - FalkorDB on whitestocks (Synology) over Tailscale
  - vLLM Qwen2.5-14B-FP8 on promaxgb10-41b1:8000 (LLM extraction)
  - vLLM nomic-embed-text-v1.5 on promaxgb10-41b1:8001 (embeddings)

Per `docs/research/ideas/phase-1-scope.md §"Latency spike"`:
  - Time `add_episode` on a representative session-shape payload.
  - Time `search_nodes` (NODE_HYBRID_SEARCH_RRF recipe).
  - Time `search_memory_facts` (EDGE_HYBRID_SEARCH_RRF recipe).
  - 1 warm-up + 3 timed runs each. Record min/median/max.

Decision bands (per phase-1-scope.md L83-85):
  - add_episode median > 5s  → SR-08 (async write-back) is critical
  - search_nodes median > 3s → revert ADR-ARCH-017 (sync) → long-running
  - search_nodes median < 1s → ADR-ARCH-017 sync confirmed

Run (from study-tutor repo root):
  /Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python \
    scripts/graphiti_latency_spike.py

Output: prints results table to stdout; also writes
`docs/research/ideas/graphiti-latency-spike-results.md`.

Throwaway test data is written to group_id "latency-spike-<ISO-DATE>" and
removed at the end. If cleanup fails, the namespace is logged so it can
be cleared manually with `guardkit graphiti clear`.
"""
from __future__ import annotations

import asyncio
import logging
import statistics
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Coroutine

# Add guardkit's src to import path is automatic since we run via its venv.
from guardkit.knowledge.config import load_graphiti_config
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_RRF,
    EDGE_HYBRID_SEARCH_RRF,
)


# Quiet noisy modules during the spike — we want clean stdout.
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
for noisy in (
    "guardkit",
    "graphiti_core",
    "neo4j",
    "httpx",
    "openai",
):
    logging.getLogger(noisy).setLevel(logging.ERROR)


SPIKE_GROUP = f"latency-spike-{datetime.now(timezone.utc).date().isoformat()}"

# Representative session-shape payload (Shared Kernel B `session.completed`).
SESSION_EPISODE_BODY = (
    'session_completed: {'
    '"session_id": "spike-session-uuid",'
    '"student_id": "lilymay",'
    '"subject": "English Literature",'
    '"topic": "macbeth:act1:witches",'
    '"duration_seconds": 1247,'
    '"aos_touched": ["AO1", "AO2"],'
    '"quality_score": 0.78,'
    '"ended_at": "2026-04-27T10:00:00Z"}'
)


@dataclass
class TimingResult:
    label: str
    runs: list[float]

    @property
    def min(self) -> float:
        return min(self.runs)

    @property
    def median(self) -> float:
        return statistics.median(self.runs)

    @property
    def max(self) -> float:
        return max(self.runs)


async def time_async(
    label: str,
    fn: Callable[[], Coroutine[Any, Any, Any]],
    *,
    n: int = 3,
) -> TimingResult:
    runs: list[float] = []
    for i in range(n):
        t0 = time.perf_counter()
        try:
            await fn()
        except Exception as exc:  # noqa: BLE001
            print(f"  [run {i+1}] FAILED: {exc!r}", file=sys.stderr, flush=True)
            raise
        elapsed = time.perf_counter() - t0
        runs.append(elapsed)
        print(f"  run {i+1}: {elapsed:.2f}s", file=sys.stderr, flush=True)
    return TimingResult(label=label, runs=runs)


def _build_config() -> tuple[GraphitiConfig, Any]:
    """Build a GraphitiConfig from .guardkit/graphiti.yaml — mirrors guardkit CLI."""
    settings = load_graphiti_config()
    config = GraphitiConfig(
        enabled=settings.enabled,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        timeout=settings.timeout,
        project_id=settings.project_id,
        graph_store=settings.graph_store,
        falkordb_host=settings.falkordb_host,
        falkordb_port=settings.falkordb_port,
        llm_provider=settings.llm_provider,
        llm_base_url=settings.llm_base_url,
        llm_model=settings.llm_model,
        llm_max_tokens=settings.llm_max_tokens,
        embedding_provider=settings.embedding_provider,
        embedding_base_url=settings.embedding_base_url,
        embedding_model=settings.embedding_model,
        embedding_dimensions=getattr(settings, "embedding_dimensions", None),
    )
    return config, settings


async def _cleanup(client: GraphitiClient) -> None:
    """Delete every node/edge in the spike group via raw cypher.

    Best-effort. Failure is logged, not raised — we don't want cleanup
    issues to invalidate the timing results.
    """
    if not client._graphiti:
        return
    driver = getattr(client._graphiti, "_driver", None) or getattr(
        client._graphiti, "driver", None
    )
    if driver is None:
        print(
            f"  [cleanup] No driver handle — leaving group_id={SPIKE_GROUP!r} "
            f"for manual removal via `guardkit graphiti clear`.",
            file=sys.stderr,
            flush=True,
        )
        return
    # Account for guardkit's project-id prefixing on group_ids.
    prefixed_group = client._apply_group_prefix(SPIKE_GROUP, scope="project")
    try:
        await driver.execute_query(
            "MATCH (n) WHERE n.group_id = $g DETACH DELETE n",
            g=prefixed_group,
        )
        print(
            f"  [cleanup] Removed nodes in group_id={prefixed_group!r}.",
            file=sys.stderr,
            flush=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"  [cleanup] Failed to drop spike namespace ({exc!r}); "
            f"manually clear group_id={prefixed_group!r}.",
            file=sys.stderr,
            flush=True,
        )


async def main() -> int:
    print("Phase 1 Graphiti latency spike", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    config, settings = _build_config()

    print(
        f"FalkorDB: {settings.falkordb_host}:{settings.falkordb_port}",
        file=sys.stderr,
    )
    print(
        f"LLM:      {settings.llm_provider} {settings.llm_model} "
        f"({settings.llm_base_url})",
        file=sys.stderr,
    )
    print(
        f"Embedder: {settings.embedding_provider} {settings.embedding_model} "
        f"({settings.embedding_base_url})",
        file=sys.stderr,
    )
    print(f"Group:    {SPIKE_GROUP}", file=sys.stderr)
    print("", file=sys.stderr)

    client = GraphitiClient(config)
    initialised = await client.initialize()
    if not initialised or not client.enabled:
        print("ERROR: GraphitiClient failed to initialise.", file=sys.stderr)
        return 1
    print("Connected.", file=sys.stderr)

    # Pre-warm vLLM endpoints so cold-start doesn't dominate run 1.
    if settings.llm_provider in ("vllm", "ollama") or settings.embedding_provider in (
        "vllm",
        "ollama",
    ):
        print("Warming up vLLM endpoints...", file=sys.stderr)
        try:
            await client.wait_for_llm_endpoints(timeout=60.0)
        except Exception as exc:  # noqa: BLE001
            print(f"  warm-up check raised {exc!r}; continuing.", file=sys.stderr)

    # The underlying graphiti-core instance for unwrapped timing.
    g = client._graphiti
    assert g is not None

    # ---- Warm-up add_episode (not timed) -----------------------------------
    print("\nWarm-up add_episode (not timed) ...", file=sys.stderr)
    t0 = time.perf_counter()
    await g.add_episode(
        name=f"warmup-{uuid.uuid4()}",
        episode_body=SESSION_EPISODE_BODY,
        source=EpisodeType.json,
        source_description="latency-spike warm-up",
        reference_time=datetime.now(timezone.utc),
        group_id=SPIKE_GROUP,
    )
    print(f"  warm-up took {time.perf_counter() - t0:.2f}s", file=sys.stderr)

    # ---- 1. add_episode (3 timed runs) -------------------------------------
    print("\nadd_episode (3 timed runs) ...", file=sys.stderr)

    async def add_one() -> None:
        await g.add_episode(
            name=f"spike-{uuid.uuid4()}",
            episode_body=SESSION_EPISODE_BODY,
            source=EpisodeType.json,
            source_description="latency-spike timed run",
            reference_time=datetime.now(timezone.utc),
            group_id=SPIKE_GROUP,
        )

    add_results = await time_async("add_episode", add_one, n=3)

    # ---- 2. search_nodes (NODE_HYBRID_SEARCH_RRF; 3 runs) ------------------
    print("\nsearch_nodes — NODE_HYBRID_SEARCH_RRF (3 timed runs) ...",
          file=sys.stderr)

    async def search_nodes_once() -> None:
        cfg = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        cfg.limit = 10
        await g.search_(
            query="macbeth witches confidence Lilymay",
            config=cfg,
            group_ids=[SPIKE_GROUP],
        )

    search_nodes_results = await time_async("search_nodes", search_nodes_once, n=3)

    # ---- 3. search_memory_facts (EDGE_HYBRID_SEARCH_RRF; 3 runs) -----------
    print("\nsearch_memory_facts — EDGE_HYBRID_SEARCH_RRF (3 timed runs) ...",
          file=sys.stderr)

    async def search_facts_once() -> None:
        cfg = EDGE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        cfg.limit = 10
        await g.search_(
            query="quality_score for Lilymay on Macbeth",
            config=cfg,
            group_ids=[SPIKE_GROUP],
        )

    search_facts_results = await time_async(
        "search_memory_facts", search_facts_once, n=3
    )

    # ---- Cleanup -----------------------------------------------------------
    print("\nCleaning up spike namespace...", file=sys.stderr)
    await _cleanup(client)
    await client.close()

    # ---- Report -----------------------------------------------------------
    rows = [add_results, search_nodes_results, search_facts_results]

    print("\n" + "=" * 60, file=sys.stderr)
    print("RESULTS", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    md_lines: list[str] = []
    md_lines.append("# Graphiti Latency Spike — Results")
    md_lines.append("")
    md_lines.append(
        f"**Date:** {datetime.now(timezone.utc).date().isoformat()}"
    )
    md_lines.append(
        "**Stack measured:** FalkorDB on `"
        f"{settings.falkordb_host}:{settings.falkordb_port}` "
        f"+ vLLM `{settings.llm_model}` on `{settings.llm_base_url}` "
        f"(LLM extraction) + `{settings.embedding_model}` on "
        f"`{settings.embedding_base_url}` (embeddings)."
    )
    md_lines.append(
        "**Generated by:** `scripts/graphiti_latency_spike.py` "
        "(per `phase-1-scope.md §\"Latency spike\"`)."
    )
    md_lines.append("")
    md_lines.append(
        "Note: this run measures the **post-21-Apr vLLM-on-GB10 stack**, "
        "not the original Gemini stack the spec assumed. The 1–3s / 5–8s "
        "expected ranges in `phase-1-scope.md:75` were calibrated for "
        "Gemini API latency; vLLM on Tailscale has a different shape."
    )
    md_lines.append("")
    md_lines.append("## Measurements")
    md_lines.append("")
    md_lines.append("Each operation: 1 warm-up (untimed) + 3 timed runs against a "
                    f"throwaway `group_id={SPIKE_GROUP!r}`.")
    md_lines.append("")
    md_lines.append("| Operation | Min (s) | Median (s) | Max (s) | Runs (s) |")
    md_lines.append("|---|---:|---:|---:|---|")
    for r in rows:
        runs_str = ", ".join(f"{x:.2f}" for x in r.runs)
        md_lines.append(
            f"| `{r.label}` | {r.min:.2f} | {r.median:.2f} | {r.max:.2f} | {runs_str} |"
        )
    md_lines.append("")
    md_lines.append("## Decisions unblocked")
    md_lines.append("")

    add_med = add_results.median
    sn_med = search_nodes_results.median
    sf_med = search_facts_results.median

    if add_med > 5.0:
        md_lines.append(
            f"- **SR-08 (async write-back): CRITICAL.** `add_episode` "
            f"median {add_med:.2f}s > 5s — async write-back is load-bearing "
            "throughout features; consider fire-and-forget from multiple "
            "write points, not just session-end."
        )
    elif add_med > 2.0:
        md_lines.append(
            f"- **SR-08 (async write-back): LOAD-BEARING.** `add_episode` "
            f"median {add_med:.2f}s — async required; defensive shape works."
        )
    else:
        md_lines.append(
            f"- **SR-08 (async write-back): DEFENSIVE.** `add_episode` "
            f"median {add_med:.2f}s — fast enough that sync would also "
            "work, but keep async as defensive shape."
        )

    if sn_med > 3.0:
        md_lines.append(
            f"- **ADR-ARCH-017 / SR-07: REVERT REQUIRED.** `search_nodes` "
            f"median {sn_med:.2f}s > 3s — `tutor_start_session` should be "
            "reclassified back to long-running with `_status`/`_cancel` "
            "companion. Run `/arch-refine --adr=ADR-ARCH-017`."
        )
    elif sn_med < 1.0:
        md_lines.append(
            f"- **ADR-ARCH-017 / SR-07: CONFIRMED.** `search_nodes` "
            f"median {sn_med:.2f}s < 1s — sync classification holds; no "
            "further architecture work required."
        )
    else:
        md_lines.append(
            f"- **ADR-ARCH-017 / SR-07: HOLDS WITH MARGIN.** `search_nodes` "
            f"median {sn_med:.2f}s (1–3s band) — sync classification holds; "
            "document this median in ARCH-017's reversion footnote so the "
            "P1 trigger threshold is concrete."
        )

    md_lines.append(
        f"- **DEC-02 / DEC-08:** resolved by these numbers — "
        f"add_episode {add_med:.2f}s / search_nodes {sn_med:.2f}s / "
        f"search_memory_facts {sf_med:.2f}s."
    )

    md_lines.append("")
    md_lines.append("## Raw run data")
    md_lines.append("")
    for r in rows:
        md_lines.append(f"- `{r.label}`: {[round(x, 2) for x in r.runs]} s")
    md_lines.append("")
    md_lines.append(
        f"_Spike group `{SPIKE_GROUP}` was cleaned up after the run "
        "(see stderr log if anything was left behind)._"
    )

    md_text = "\n".join(md_lines) + "\n"

    out_path = Path("docs/research/ideas/graphiti-latency-spike-results.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md_text, encoding="utf-8")

    # Echo the markdown to stdout so the run's STDOUT *is* the report.
    print(md_text)
    print(f"Wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
Running the spike in background — add_episode calls do LLM extraction which takes minutes per call (we saw 3–6 min for ADR-sized payloads earlier; session-shape should be faster but I'm budgeting for 10–20 min total).

Bash Run Graphiti latency spike
IN
/Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python scripts/graphiti_latency_spike.py 2>&1

OUT
Command running in background with ID: b9ogptpo4. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/3ba1f358-e1c0-4d11-b23f-00ac2201c6e2/tasks/b9ogptpo4.output
Spike running. Live progress is in the task output if you want to peek (Bash task ID b9ogptpo4). I'll wait for the completion notification rather than polling — based on the ADR seeding from earlier (~3min for a small ADR), I'd expect total runtime of ~10–15 min for 4 add_episode calls + 6 search calls.

Spike finished. Reading results.

Bash Read spike output
IN
cat /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/3ba1f358-e1c0-4d11-b23f-00ac2201c6e2/tasks/b9ogptpo4.output

OUT
Phase 1 Graphiti latency spike
============================================================
FalkorDB: whitestocks:6379
LLM:      vllm neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic (http://promaxgb10-41b1:8000/v1)
Embedder: vllm nomic-embed-text-v1.5 (http://promaxgb10-41b1:8001/v1)
Group:    latency-spike-2026-04-27

Connected.
Warming up vLLM endpoints...

Warm-up add_episode (not timed) ...
  warm-up took 62.84s

add_episode (3 timed runs) ...
  run 1: 134.39s
  run 2: 78.10s
  run 3: 78.98s

search_nodes — NODE_HYBRID_SEARCH_RRF (3 timed runs) ...
  run 1: 0.11s
  run 2: 0.07s
  run 3: 0.07s

search_memory_facts — EDGE_HYBRID_SEARCH_RRF (3 timed runs) ...
  run 1: 0.08s
  run 2: 0.08s
  run 3: 0.07s

Cleaning up spike namespace...
  [cleanup] Removed nodes in group_id='study-tutor__latency-spike-2026-04-27'.

============================================================
RESULTS
============================================================
Wrote docs/research/ideas/graphiti-latency-spike-results.md
# Graphiti Latency Spike — Results

**Date:** 2026-04-27
**Stack measured:** FalkorDB on `whitestocks:6379` + vLLM `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` on `http://promaxgb10-41b1:8000/v1` (LLM extraction) + `nomic-embed-text-v1.5` on `http://promaxgb10-41b1:8001/v1` (embeddings).
**Generated by:** `scripts/graphiti_latency_spike.py` (per `phase-1-scope.md §"Latency spike"`).

Note: this run measures the **post-21-Apr vLLM-on-GB10 stack**, not the original Gemini stack the spec assumed. The 1–3s / 5–8s expected ranges in `phase-1-scope.md:75` were calibrated for Gemini API latency; vLLM on Tailscale has a different shape.

## Measurements

Each operation: 1 warm-up (untimed) + 3 timed runs against a throwaway `group_id='latency-spike-2026-04-27'`.

| Operation | Min (s) | Median (s) | Max (s) | Runs (s) |
|---|---:|---:|---:|---|
| `add_episode` | 78.10 | 78.98 | 134.39 | 134.39, 78.10, 78.98 |
| `search_nodes` | 0.07 | 0.07 | 0.11 | 0.11, 0.07, 0.07 |
| `search_memory_facts` | 0.07 | 0.08 | 0.08 | 0.08, 0.08, 0.07 |

## Decisions unblocked

- **SR-08 (async write-back): CRITICAL.** `add_episode` median 78.98s > 5s — async write-back is load-bearing throughout features; consider fire-and-forget from multiple write points, not just session-end.
- **ADR-ARCH-017 / SR-07: CONFIRMED.** `search_nodes` median 0.07s < 1s — sync classification holds; no further architecture work required.
- **DEC-02 / DEC-08:** resolved by these numbers — add_episode 78.98s / search_nodes 0.07s / search_memory_facts 0.08s.

## Raw run data

- `add_episode`: [134.39, 78.1, 78.98] s
- `search_nodes`: [0.11, 0.07, 0.07] s
- `search_memory_facts`: [0.08, 0.08, 0.07] s

_Spike group `latency-spike-2026-04-27` was cleaned up after the run (see stderr log if anything was left behind)._
Spike results — clear and decisive
Operation	Min	Median	Max	Verdict
add_episode	78.1s	78.98s	134.4s	>>> 5s threshold
search_nodes	0.07s	0.07s	0.11s	<<< 1s threshold
search_memory_facts	0.07s	0.08s	0.08s	fast
The add_episode numbers are dominated by the LLM extraction step (Qwen2.5-14B FP8 on GB10 reasoning over the JSON payload — ~80s per call, cold-start gave run 1 the 134s outlier). Search operations hit only the embedding endpoint + FalkorDB cypher and complete in tens of milliseconds.

What this means for the architecture
1. SR-08 (Graphiti async write-back) — CRITICAL, not defensive.

At ~79s median, a synchronous add_episode at session-end would make the student wait over a minute for tutor_session_end to return. SR-08 isn't just "defensive shape" — it's load-bearing. The right pattern per phase-1-scope.md L83 is: fire-and-forget from multiple write points (session-end is the obvious one, but also misconception-observed during turns, and confidence-delta proposals from the Coach), not a single session-end batch.

This needs to be elevated to an ADR — likely refining ADR-ARCH-009 (six parity surfaces) to seven, with SR-08 joining SR-01–07 as a load-bearing CC.

2. ADR-ARCH-017 / SR-07 (sync tutor_start_session) — CONFIRMED with massive margin.

search_nodes at 0.07s is 40× faster than the 3s reversion threshold in ARCH-017's footnote. The sync classification holds. The Phase 1 student-model read at session start (the original concern that motivated long-running) costs ~70ms — completely negligible. No /arch-refine follow-up needed for ARCH-017.

3. DEC-02 / DEC-08 — resolved.

What this changes about your next-step sequence
The plan you pasted earlier had the Phase 1 design re-runs after a /arch-refine for SR-08/SR-09. That bundle is now narrower:

No need to refine ADR-ARCH-017 (SR-07) — the spike confirmed it.
SR-08 still needs ADR treatment — but with a much stronger forcing function (the 79s number) than before.
SR-09 (runtime LLM parameter explicitness) is unchanged by the spike — still wants ADR treatment.
Suggested updated sequence:


# 1. /arch-refine for SR-08 + SR-09 — cite the spike numbers as the empirical
#    basis. Likely refines ADR-ARCH-009 (six → eight parity surfaces).
/arch-refine --adr=ADR-ARCH-009 \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  --context docs/research/ideas/phase-1-scope.md

# 2. Then your two Phase 1 design re-runs as previously planned.
/system-design --focus="Knowledge & Curriculum" ...
/system-design --focus="Student Model" ...
Files to review/commit
New: scripts/graphiti_latency_spike.py — reproducible benchmark script
New: docs/research/ideas/graphiti-latency-spike-results.md — generated results doc with auto-derived decision verdicts
Suggested commit subject: spike: graphiti latency on vLLM-GB10 stack (add_episode 79s, search 70ms) — captures both the load-bearing finding (SR-08 critical) and the configuration-pinning detail (vLLM, not Gemini).

The throwaway latency-spike-2026-04-27 group was cleaned from the graph automatically — no leftover spike data in architecture_decisions.

please commit and update the build plan with these findings
Updating the build-plan with the spike findings, then splitting into two logical commits — one for the /arch-refine D2 closure, one for the spike.

Bash See all changes before committing
IN
git status --short 2>&1

OUT
 M .guardkit/graphiti-query-log.jsonl
 M docs/architecture/ARCHITECTURE.md
 M docs/architecture/container.md
 M docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md
 M docs/architecture/domain-model.md
 M docs/design/README.md
 M docs/research/ideas/phase-0-build-plan.md
 M docs/research/ideas/phase-0-scope.md
 M src/study_tutor/mcp/adapter.py
 M src/study_tutor/mcp/server.py
?? .claude/scheduled_tasks.lock
?? docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md
?? docs/research/ideas/graphiti-latency-spike-results.md
?? scripts/graphiti_latency_spike.py
?? uv.lock
Bash Check if uv.lock is gitignored or previously committed
IN
grep -n "uv.lock\|scheduled_tasks" .gitignore 2>&1; echo "---"; git log --oneline -5 -- uv.lock 2>&1 | head -5

OUT
99:#   Similar to Pipfile.lock, it is generally recommended to include uv.lock in version control.
102:#uv.lock
---
Two unrelated files were generated as side-effects (uv.lock from pytest, .claude/scheduled_tasks.lock from the wakeup machinery) and one is the user's pre-session modification (.guardkit/graphiti-query-log.jsonl). I'll stage explicitly to avoid sweeping those into commits.

Commit 1: /arch-refine D2 closure
Bash Stage all /arch-refine files
IN
git add docs/architecture/ARCHITECTURE.md docs/architecture/container.md docs/architecture/domain-model.md docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md docs/design/README.md docs/research/ideas/phase-0-scope.md docs/research/ideas/phase-0-build-plan.md src/study_tutor/mcp/adapter.py src/study_tutor/mcp/server.py && git status --short

OUT
 M .guardkit/graphiti-query-log.jsonl
M  docs/architecture/ARCHITECTURE.md
M  docs/architecture/container.md
M  docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md
A  docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md
M  docs/architecture/domain-model.md
M  docs/design/README.md
M  docs/research/ideas/phase-0-build-plan.md
M  docs/research/ideas/phase-0-scope.md
M  src/study_tutor/mcp/adapter.py
M  src/study_tutor/mcp/server.py
?? .claude/scheduled_tasks.lock
?? docs/research/ideas/graphiti-latency-spike-results.md
?? scripts/graphiti_latency_spike.py
?? uv.lock
Bash Check commit message style
IN
git log --oneline -10

OUT
7959df9 Ran system-plan
8d0bca7 Ran system-design
2ba03ec chore(deps): add pytest-bdd>=8.1,<9 to dev group (TASK-OPS-BDDM-11)
682df0b chore: drop bogus langchain-skills plugin entry, ignore settings.local.json
491addf fix(mcp): drop trailing slash from graphiti MCP URL
edcb7fd chore(mcp): switch graphiti to central HTTP MCP on GB10
3b040a2 update history and doc
321dbee docs: FEAT-PO-005 submission scaffolding stubs
5993620 readme doc
ac33bc6 docs: add FEAT-PH1-004 + SR-09 to Phase 1 from 23 Apr empirical findings
Bash Commit /arch-refine D2 closure
IN
git commit -m "$(cat <<'EOF'
Ran arch-refine: D2 closed via ADR-ARCH-017

Reclassifies tutor_start_session from long-running → sync (Phase 0).
Partially supersedes ADR-ARCH-008's SR-07 classification table; the
rest of ARCH-008 (single-transport, HTTP-deferral, auth posture) stands.

Why: the original ARCH-008 rationale ("classification stable across
phases for forward compatibility") was undermined by phase-1-scope.md
already making the P1 classification measurement-conditional, and the
P0 implementation never built the long-running protocol — registered
tool description mismatched handler behaviour, violating SR-07 (the
exact LES1 row that motivated the parity surface).

ADR-ARCH-017 captures the new decision with a measurement-conditional
P1 reversion rule: revert to long-running iff Graphiti search_nodes
median > ~3s for the student-model read at session start.

Downstream artefacts aligned: domain-model §7.1, container.md C4
description, design/README D2+§7.4 (now resolved), phase-0-scope
§SR-07, phase-0-build-plan punch-list item 7, and the load-bearing
runtime tool description in src/study_tutor/mcp/server.py.

Both ADRs seeded into Graphiti architecture_decisions group with
temporal-superseding semantics intact.

Tests: tests/unit/mcp/ 8/8 passing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)" 2>&1 | tail -5

OUT
[main f5635a9] Ran arch-refine: D2 closed via ADR-ARCH-017
 10 files changed, 124 insertions(+), 22 deletions(-)
 create mode 100644 docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md
Commit 1 landed. Now updating the build-plan with spike findings and committing the spike work.

Read phase-0-build-plan.md (lines 43-62)
Edit phase-0-build-plan.md
Modified
Edit phase-0-build-plan.md
Added 14 lines
Bash Stage spike files
IN
git add docs/research/ideas/phase-0-build-plan.md docs/research/ideas/graphiti-latency-spike-results.md scripts/graphiti_latency_spike.py && git status --short

OUT
 M .guardkit/graphiti-query-log.jsonl
A  docs/research/ideas/graphiti-latency-spike-results.md
M  docs/research/ideas/phase-0-build-plan.md
A  scripts/graphiti_latency_spike.py
?? .claude/scheduled_tasks.lock
?? uv.lock
Bash Commit spike work
IN
git commit -m "$(cat <<'EOF'
Ran Graphiti latency spike (2026-04-27): SR-08 elevated; ARCH-017 confirmed

Three-hop measurement against the post-21-Apr vLLM-on-GB10 stack:
FalkorDB on whitestocks (Tailscale) + vLLM Qwen2.5-14B-FP8 + nomic-
embed-text-v1.5. 1 warm-up + 3 timed runs per operation.

Headline medians:
  add_episode         78.98s  — LLM-extraction dominated
  search_nodes         0.07s  — embedding + cypher only
  search_memory_facts  0.08s  — same shape

Decisions unblocked:
  - SR-08 (async write-back) is CRITICAL, not defensive. A synchronous
    add_episode at session-end would block tutor_session_end for ~80s.
    Async fire-and-forget from multiple write points required, not just
    session-end batch. Bundle into next /arch-refine on ADR-ARCH-009
    (six → eight parity surfaces).
  - ADR-ARCH-017 / SR-07 sync classification CONFIRMED with massive
    margin. 0.07s is ~40× faster than ARCH-017's 3s reversion trigger.
    No further refinement of ARCH-017 needed.
  - DEC-02 / DEC-08 resolved.

Stack note: spec's 1–3s expected range assumed Gemini; actual measured
stack uses vLLM-on-Tailscale (steadier per-call, slower per-token,
dominated by 14B-parameter inference).

Reproducible via scripts/graphiti_latency_spike.py against any
.guardkit/graphiti.yaml config. Throwaway test data cleaned up at end
of run via raw cypher; no spike data left in architecture_decisions.

Build plan updated (punch-list item 8) with full findings and next-step
sequence.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)" 2>&1 | tail -5

OUT
[main 4294294] Ran Graphiti latency spike (2026-04-27): SR-08 elevated; ARCH-017 confirmed
 3 files changed, 463 insertions(+), 1 deletion(-)
 create mode 100644 docs/research/ideas/graphiti-latency-spike-results.md
 create mode 100644 scripts/graphiti_latency_spike.py
Bash Confirm commit history
IN
git log --oneline -4

OUT
4294294 Ran Graphiti latency spike (2026-04-27): SR-08 elevated; ARCH-017 confirmed
f5635a9 Ran arch-refine: D2 closed via ADR-ARCH-017
7959df9 Ran system-plan
8d0bca7 Ran system-design
Both commits landed cleanly:

Commit	Files	Lines
f5635a9 — Ran arch-refine: D2 closed via ADR-ARCH-017	10 changed (1 new ADR)	+124 / −22
4294294 — Ran Graphiti latency spike (2026-04-27): SR-08 elevated; ARCH-017 confirmed	3 changed (script + results + build-plan item 8)	+463 / −1
Sits naturally after the Ran system-plan and Ran system-design commits — same convention.

Left untouched (deliberately):

.guardkit/graphiti-query-log.jsonl — your pre-session local change.
uv.lock — generated by my pytest runs; project's .gitignore neighbourhood treats it as untracked, so I left it.
.claude/scheduled_tasks.lock — runtime artefact from the wakeup machinery.
If you want to commit uv.lock (it is generally recommended for reproducible builds — your .gitignore even says so in the comments) that's a separate one-line commit I can do whenever.

Where the project stands
Phase 0 SR-07 contract: clean end-to-end. ADR ↔ architecture text ↔ design ↔ scope ↔ build-plan ↔ runtime tool description ↔ handler behaviour all consistent.
Phase 1 latency budget: measured. 79s writes, 70ms reads — these are the numbers feature specs and the Coach pattern need to plan against.
Open follow-up before P1 design re-runs: one /arch-refine to elevate SR-08 (and add SR-09) — the spike just gave it a strong empirical foundation.
please provide the full command syntax for : Open follow-up before P1 design re-runs: one /arch-refine to elevate SR-08 (and add SR-09) — the spike just gave it a strong empirical foundation.
Full command for the SR-08 + SR-09 refinement

/arch-refine --adr=ADR-ARCH-009 \
  "elevate SR-08 (Graphiti async write-back) and SR-09 (runtime LLM parameter explicitness) from phase-1-scope.md items to load-bearing cross-cutting concerns alongside SR-01..07; spike confirms 79s add_episode median makes async non-negotiable" \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md
What each flag does
Argument	Purpose
--adr=ADR-ARCH-009	Direct-targets the ADR; skips disambiguation. ARCH-009 owns the parity-surfaces decision (currently captures SR-01..07 + CC-01..08).
"…natural language query…"	Mandatory even with --adr — used for the audit trail and for the new ADR's introductory framing. The phrasing above states intent (elevate, not just document) and cites the spike result as the empirical forcing function.
--context graphiti-latency-spike-results.md	The empirical basis for elevating SR-08 from "defensive" to "critical". 78.98s add_episode median is the load-bearing number the new ADR needs to cite.
--context phase-1-scope.md	Source of the current SR-08 and SR-09 wording (§SR-08, §SR-09). The new ADR will lift those definitions into the architecture set.
--context openwebui-rag-empirical-findings-2026-04-23.md	Provenance for SR-09 — phase-1-scope.md L17 traces SR-09 back to recommendation R5 (runtime-param smoke assertion) from the 23 Apr OpenWebUI findings. The new ADR should cite this as evidence-of-pain.
What the interactive session will ask
/arch-refine is interactive (--no-questions is rejected for this command). It'll walk Q1–Q4:

Q1. What has changed? — Two findings since ARCH-009 was written on 2026-04-18:

Phase 1 added two new structural requirements (SR-08 from phase-1-scope.md §SR-08, SR-09 from R5 in OpenWebUI findings).
The 2026-04-27 latency spike measured add_episode at 79s median, escalating SR-08 from "defensive shape" to "load-bearing throughout features".
Q2. What is the new decision? — Eight parity surfaces (was six). SR-08 and SR-09 join SR-01..07 as load-bearing CCs. Likely also lift to CC-numbering (CC-01..CC-09 plus the existing CC-08 fire-and-forget rule, which may need renumbering or rewording to avoid collision).

Q3. Alternatives — Keep SR-08/09 as phase-1-scope.md items only (rejected: spike numbers force SR-08 into "every feature" territory; coding-guide lore isn't sufficient). Add only SR-08, defer SR-09 (rejected: SR-09 has independent evidence and ADR-ifying both at once is one less refinement to schedule).

Q4. Consequences — Every Phase 1 feature now structurally honours SR-08 (async write-back) and SR-09 (explicit LLM params). Test cases needed for both. Affects every feature spec from FEAT-PH1-001 onwards.

Impact analysis the command will show
The downstream artefacts that mention SR-01..07 / CC-01..07 and will need updating after refinement:

Artefact	Why it changes
docs/architecture/ARCHITECTURE.md §6	Lists the cross-cutting concerns; needs CC-09 (or whatever the new numbering is)
docs/architecture/decisions/ADR-ARCH-009-*.md	Status flips to "Superseded by ADR-ARCH-018"
docs/research/ideas/phase-1-scope.md §SR-08, §SR-09	Add a "promoted to ADR-ARCH-018" pointer; content stays
docs/research/ideas/phase-0-scope.md §"Structural Requirements"	Header may need updating from "six parity surfaces" → "eight" if it references the count
Heads-up on ADR-ARCH-009's existing CC-08
ARCH-009 already uses CC-08 for "fire-and-forget + poll above 30s (LES1 §4)" — distinct from SR-07. So the new SRs and CCs need to renumber carefully. The interactive session will likely produce one of:

Option (a) SR-01..09 with CC-01..07 + CC-08 (existing) + CC-09 (Graphiti async, ex-SR-08) + CC-10 (LLM params explicit, ex-SR-09) — CC numbering decouples from SR numbering. Cleaner.
Option (b) Renumber the existing CC-08 to keep SR-N ↔ CC-N alignment. Cleaner long-term but changes a published reference.
Worth flagging this when Q2 lands; the agent running /arch-refine will prompt you to choose.

After the refinement completes
The output will be ADR-ARCH-018 (auto-numbered) superseding ADR-ARCH-009, plus an automatic re-seed into Graphiti architecture_decisions group, plus the C4 re-review gate (which will likely be a no-op since adding CCs doesn't change container topology).

Once that lands, your two /system-design --focus= re-runs are clear to fire.

I ran this command which didn't have the last doc paramter?
/arch-refine --adr=ADR-ARCH-009 \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  --context docs/research/ideas/phase-1-scope.md
Two omissions, with different severity:

1. The natural language query is missing (likely fatal)
Per the /arch-refine spec, even with --adr=ADR-ARCH-009 a query is mandatory — the command's pre-flight rejects empty queries:


if not query or not query.strip():
    print("ERROR: Refinement query is required")
    exit(1)
So depending on the actual implementation, either:

The command errored out and you got ERROR: Refinement query is required. → Re-run with the query string.
The implementation is lenient when --adr is set and let it through. → The session is running, but the resulting ADR may have a thin opening framing because it had no human-written intent statement to anchor on.
Quickest check: scroll back in the session output. If you see a 📋 MATCHING ARCHITECTURE DECISIONS block or jumped straight to Q1, it ran. If you see the error, re-run.

2. The openwebui-rag-empirical-findings doc is missing (minor)
This was the evidence base for SR-09 (per phase-1-scope.md L17: R5 (runtime-param smoke assertion) → new structural requirement SR-09 below). But SR-09's definition is in phase-1-scope.md §SR-09, which you did include — so the agent has enough to cite the rule itself.

What's lost without the openwebui doc: the concrete failure-mode evidence (R5 specifics — what actually went wrong with implicit LLM params during the 23 Apr OpenWebUI session). That's the kind of thing that strengthens an ADR's "Alternatives Considered" and "Consequences" sections, but isn't structurally required.

Severity: the resulting ADR-ARCH-018 will reference SR-09 correctly but with thinner provenance for why SR-09 exists. Easy to backfill afterwards by editing the file directly to add a reference line: **Evidence:** docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md §4 R5.

Recovery options by state
If the session is…	Do this
Errored (no query)	Re-run with the query: /arch-refine --adr=ADR-ARCH-009 "elevate SR-08 (Graphiti async, spike confirms 79s add_episode) and SR-09 (runtime LLM param explicitness from R5) to load-bearing CCs alongside SR-01..07" --context …
Running, you're at Q1–Q4 prompts	When Q1 ("what has changed?") fires, paste the evidence verbally — both the spike numbers AND R5 from the openwebui findings. The agent can incorporate it without the file being attached.
Already completed (ADR-ARCH-018 written)	Read the new ADR — if the SR-09 section cites only phase-1-scope.md and not the openwebui findings, edit one line in to add the reference. Rerun is unnecessary.
What state is it in? I can help with the recovery if you tell me which.

It's stopped at a decision point so I think you can edit the doc then I can answer [Y]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ARCHITECTURE DECISION REFINED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ADR-ARCH-009: Status → "Superseded by ADR-ARCH-018 on 2026-04-27"
  ADR-ARCH-018: Created (supersedes ADR-ARCH-009)

Updated files:
  ├── docs/architecture/decisions/ADR-ARCH-009-…-crosscutting.md          (status superseded)
  ├── docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md  (new)
  ├── docs/architecture/ARCHITECTURE.md                                   (CC table 12→14; ADR index +ADR-ARCH-018; ADR-ARCH-009 marked superseded)
  └── docs/architecture/assumptions.yaml                                  (ASSUM-012 related_adr → ADR-ARCH-018)

Stale artefacts (not edited; recorded in ADR-ARCH-018 §"Downstream artefacts flagged stale"):
  ⚠️ ADR-ARCH-003                 — needs separate /arch-refine to broaden write-back scope
  ⚠️ docs/architecture/domain-model.md §324, §351
  ⚠️ docs/architecture/container.md
  ⚠️ docs/design/contracts/API-mcp-transport.md
  ⚠️ docs/design/contracts/API-tutoring.md
  ⚠️ docs/design/models/DM-mcp-transport.md
  ⚠️ docs/design/events-schema.yaml
  ⚠️ docs/design/README.md

C4 diagrams: re-review NOT required (cross-cutting concern refinement, no
container or external-system structural change).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Graphiti is enabled: true in .guardkit/graphiti.yaml, but I cannot directly run guardkit shell commands without your approval. Proposed seeding commands:


guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md \
  --group architecture_decisions

guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md \
  --group architecture_decisions
Run these now? [Y/n]

Next steps after seeding:

Review the new ADR: docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
Refine ADR-ARCH-003 separately to broaden "session-end" → "every write point": /arch-refine --adr=ADR-ARCH-003 --context docs/research/ideas/graphiti-latency-spike-results.md
Run /system-design to detect and report the 5 stale design contracts.
Two things to flag before you press Y:

The agent's seeding commands use --group which doesn't exist — same bug we hit earlier in the session. The actual flag is --type adr (group is auto-derived). If you press Y those commands will error.
You wanted me to review the new ADR — let me read it now and check for content improvements while it's still the local-only version.
Read ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
Read ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md (lines 2-16)
Review of ADR-ARCH-018: solid, no edits needed
The new ADR is genuinely well-written even with the missing --context for the openwebui doc — the agent inferred from phase-1-scope.md L17's "R5 (runtime-param smoke assertion)" pointer that openwebui-rag-empirical-findings was the evidence base for SR-09 and cited it correctly (line 32, 94, plus in ARCHITECTURE.md CC-14).

What it got right:

✅ CC numbering chosen Option (a) from the two we discussed — CC-13/14 appended after CC-12 (kept existing CC-08 unchanged). Clean, no renumbering of published references.
✅ Honest about ARCH-003 staleness — explicitly calls out that ARCH-003's session-end-only framing is now narrower than CC-13's every-write-point semantics, and recommends a separate /arch-refine (which you already had teed up as the next step).
✅ Latency spike number is load-bearing in the ADR — line 28's "78.98s — over 15× the 5s threshold" makes the rationale unambiguous.
✅ Stale artefact list is concrete and actionable.
✅ Title is descriptive — long, but better long-and-clear than short-and-cryptic. Matches the project's existing title style.
ADR-ARCH-009's Status block correctly flips to "Superseded by ADR-ARCH-018", with content preserved.

No edits required before seeding.

Don't press Y — those seeding commands will fail
The agent generated:


guardkit graphiti add-context …ADR-ARCH-009… --group architecture_decisions
guardkit graphiti add-context …ADR-ARCH-018… --group architecture_decisions
But --group isn't a real flag. The CLI uses --type adr (group is auto-derived from the parser type). We hit this exact issue earlier in the session.

If you press Y the agent will run those commands and you'll get:


Error: No such option: --group
Recommended action
Press N at the Run these now? [Y/n] prompt to exit the /arch-refine session cleanly.
I'll run the correct seeding commands afterwards using --type adr (and -f for the ARCH-009 re-seed since it's already in the graph). Two background tasks, ~3 min for ARCH-018 (new) and ~6 min for ARCH-009 (re-seed) based on the seeding times we saw earlier.
Then I'll commit the new files (ADR-ARCH-018, ADR-ARCH-009 status flip, ARCHITECTURE.md, assumptions.yaml).
Once you press N, send me a quick "done" and I'll kick off the correct seeding.

done:

Graphiti seeding skipped. Markdown artefacts are written; knowledge graph not updated. Re-run the seeding commands above whenever you're ready (or use /arch-refine again — re-applying with the same ADRs is idempotent for the upsert).

Refinement summary:

ADR-ARCH-009 marked superseded by ADR-ARCH-018 (body preserved for historical traceability).
ADR-ARCH-018 created — extends load-bearing cross-cutting concerns from CC-01–CC-12 to CC-01–CC-14, adding CC-13 (Graphiti async write-back at every write point, SR-08, evidence: add_episode 78.98s) and CC-14 (runtime LLM params explicit, SR-09).
ARCHITECTURE.md §6 (CC table 12→14) and §9 (ADR index +ADR-ARCH-018, ADR-ARCH-009 marked superseded).
assumptions.yaml ASSUM-012 related_adr → ADR-ARCH-018.
8 downstream artefacts (ADR-ARCH-003, domain-model, container, 5 design contracts) are recorded as stale inside ADR-ARCH-018 §"Downstream artefacts flagged stale" — not auto-flagged in Graphiti since seeding was declined.
Suggested next: /arch-refine --adr=ADR-ARCH-003 --context docs/research/ideas/graphiti-latency-spike-results.md to broaden ADR-ARCH-003's single-write-point scope to match CC-13.
Kicking off both seeding commands in parallel as background tasks. Each takes 3–6 minutes based on previous runs.

Bash Check what /arch-refine modified
IN
git status --short

OUT
 M .guardkit/graphiti-query-log.jsonl
 M docs/architecture/ARCHITECTURE.md
 M docs/architecture/assumptions.yaml
 M docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
?? .claude/scheduled_tasks.lock
?? docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
?? uv.lock
Bash Seed ADR-ARCH-018 (new)
IN
guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md --type adr -v 2>&1

OUT
Command running in background with ID: bcbxy88pd. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/3ba1f358-e1c0-4d11-b23f-00ac2201c6e2/tasks/bcbxy88pd.output
Bash Re-seed ADR-ARCH-009 with superseded status
IN
guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md --type adr -f -v 2>&1

OUT
Command running in background with ID: bd363mznc. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/3ba1f358-e1c0-4d11-b23f-00ac2201c6e2/tasks/bd363mznc.output
Both seedings running in parallel. Files modified by /arch-refine confirmed:

New: ADR-ARCH-018
Modified: ADR-ARCH-009 (status), ARCHITECTURE.md (CC table 12→14, ADR index), assumptions.yaml (ASSUM-012 link)
Will commit once both seeding tasks notify completion. Estimated 3–6 min each, running concurrently so total wall time ~6 min.

ADR-ARCH-018 seeding done (task bcbxy88pd). Waiting on ADR-ARCH-009 re-seed (bd363mznc) before reading either output and committing — both notifications will fire.

Both done. Reading outputs and committing.

Bash Read both seeding outputs
IN
echo "=== ARCH-018 seed (new) ==="; tail -10 /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/3ba1f358-e1c0-4d11-b23f-00ac2201c6e2/tasks/bcbxy88pd.output; echo; echo "=== ARCH-009 re-seed ==="; tail -10 /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/3ba1f358-e1c0-4d11-b23f-00ac2201c6e2/tasks/bd363mznc.output

OUT
=== ARCH-018 seed (new) ===
adr_adr-arch-018-extend-load-bearing-cross-cutting-concerns-with-sr-08-graphiti-
async-write-back-and-sr-09-runtime-llm-parameters-explicit (adr)
INFO:graphiti_core.graphiti:Completed add_episode in 162331.16483688354 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-018-extend-load-bearing-cross-cutting-concerns-with-sr-08-graphiti-async-write-back-and-sr-09-runtime-llm-parameters-explicit]: nodes=11, edges=7, invalidated=0
  ✓ 
docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09
.md (adr)

Summary:
  Added 1 file, 1 episode

=== ARCH-009 re-seed ===
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 467153.6672115326 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-009-six-parity-surfaces-les1-as-load-bearing-cross-cutting-concerns]: nodes=27, edges=72, invalidated=0
  ✓ 
docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md 
(adr)

Summary:
  Added 1 file, 1 episode
Both seedings landed — ARCH-018 (11 nodes, 7 edges, 2.7 min) and ARCH-009 (27 nodes, 72 edges, 7.8 min, both with invalidated=0). The vLLM duplicate_facts warnings on ARCH-009 are the same non-fatal pattern we saw on the ARCH-008 re-seed earlier.

Committing the four-file change.

Bash Stage /arch-refine ARCH-009 → ARCH-018 supersession
IN
git add docs/architecture/ARCHITECTURE.md docs/architecture/assumptions.yaml docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md && git status --short

OUT
 M .guardkit/graphiti-query-log.jsonl
M  docs/architecture/ARCHITECTURE.md
M  docs/architecture/assumptions.yaml
M  docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
A  docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
?? .claude/scheduled_tasks.lock
?? uv.lock
Bash Commit ARCH-009 → ARCH-018 supersession
IN
git commit -m "$(cat <<'EOF'
Ran arch-refine: ADR-ARCH-018 extends CCs with SR-08 + SR-09

Supersedes ADR-ARCH-009 (LES1 six parity surfaces). Extends the load-
bearing cross-cutting concerns set from CC-01..CC-12 to CC-01..CC-14:

  CC-13 — Graphiti write-back is async at every caller-facing path (SR-08).
          Specialises the generic CC-08 with measurement: add_episode
          median 78.98s (per the 27 Apr latency spike) makes async
          fire-and-forget the only viable shape, at every write point —
          not just session-end.
  CC-14 — Runtime LLM parameters (num_ctx, num_predict) explicit and
          asserted (SR-09). Closes the silent-truncation failure mode
          from the 23 Apr OpenWebUI RAG empirical findings (default
          num_ctx=2048 truncated tutoring responses mid-sentence with
          RAG active).

CC numbering: appended new codes at end (CC-13/14) rather than renumber
the existing CC-09..CC-12. Avoids breaking published references at the
cost of slight SR↔CC index drift.

Knock-on effects:
  - ADR-ARCH-003 (async Graphiti write-back at session-end boundary) is
    now narrower than CC-13's "every write point" framing. ADR-ARCH-003
    is recorded as stale inside ADR-ARCH-018 §"Downstream artefacts
    flagged stale"; needs its own /arch-refine to broaden scope.
  - 5 design contracts + container.md + domain-model also stale-flagged
    (CC-08 references remain correct but don't enumerate CC-13/14).
    /system-design will detect on next run.
  - ASSUM-012 related_adr re-pointed from ARCH-009 → ARCH-018.

Both ADRs seeded into Graphiti architecture_decisions group:
  - ADR-ARCH-018: 11 nodes, 7 edges, 0 invalidated
  - ADR-ARCH-009 (re-seed with superseded status): 27 nodes, 72 edges,
    0 invalidated. Old "Accepted" facts preserved temporally; queries
    return current "Superseded" status by recency.

Suggested next: /arch-refine --adr=ADR-ARCH-003 to broaden its single-
write-point scope to match CC-13.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)" 2>&1 | tail -5

OUT
[main 357cbc8] Ran arch-refine: ADR-ARCH-018 extends CCs with SR-08 + SR-09
 4 files changed, 109 insertions(+), 7 deletions(-)
 create mode 100644 docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
Bash Confirm commit history
IN
git log --oneline -5

OUT
357cbc8 Ran arch-refine: ADR-ARCH-018 extends CCs with SR-08 + SR-09
4294294 Ran Graphiti latency spike (2026-04-27): SR-08 elevated; ARCH-017 confirmed
f5635a9 Ran arch-refine: D2 closed via ADR-ARCH-017
7959df9 Ran system-plan
8d0bca7 Ran system-design
Committed cleanly. Three commits this session, all in the same Ran <command>: convention as the user's prior workflow commits.

Architecture state now
ADR	Status	Captures
ADR-ARCH-009	Superseded by ARCH-018 (2026-04-27)	Original six LES1 parity surfaces — preserved for traceability
ADR-ARCH-017 (new this session)	Accepted	tutor_start_session sync classification (partially supersedes ARCH-008 SR-07 table)
ADR-ARCH-018 (new this session)	Accepted	Eight parity surfaces — adds CC-13 (Graphiti async, evidence: spike 78.98s) + CC-14 (LLM params explicit, evidence: OpenWebUI R5)
ARCH-008	Partially superseded	Single-transport choice and auth posture still in force; SR-07 table superseded by ARCH-017
ARCH-003	Will be stale-flagged after ARCH-018	Single-write-point framing; ADR-ARCH-018 records it needs its own /arch-refine to broaden to every-write-point
What's still open before the Phase 1 design re-runs
Per the /arch-refine summary you pasted, one follow-up:


/arch-refine --adr=ADR-ARCH-003 \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  "broaden async write-back scope from session-end-only to every Graphiti write point per CC-13 (ARCH-018)"
This brings ARCH-003 into alignment with CC-13's every-write-point semantics. Then your two /system-design --focus= re-runs (Knowledge & Curriculum, Student Model) are clear to fire.

Untracked files I'm still leaving alone
.guardkit/graphiti-query-log.jsonl — your pre-session local change.
uv.lock — pytest-generated; project's .gitignore comments suggest committing it would be reasonable, but as a separate concern.
.claude/scheduled_tasks.lock — runtime lock from the wakeup machinery.
Let me know if you want any of those committed, or if you'd like me to draft the ADR-ARCH-003 refinement command argument (with the right query string) ready for you to run.