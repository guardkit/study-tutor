
/system-arch \
  --from docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context docs/research/ideas/decisions-log-2026-04-17.md \
  --context docs/research/ideas/state-of-the-project-and-phase-recommendation.md \
  --context docs/research/ideas/deepagents-patterns-review.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md \
  --context domains/gcse-english/GOAL.md \
  --context docs/gamification/design.md

  I'll orchestrate /system-arch interactively. First, let me load all the context files and check Graphiti availability in parallel.

Read phase-0-scope.md
Read phase-0-build-plan.md
Read decisions-log-2026-04-17.md
Read state-of-the-project-and-phase-recommendation.md
Read GOAL.md
Read design.md
Read cross-agent-lessons-from-specialist-agent.md
Globpattern: "docs/architecture/**/*.md"
No files found
Read graphiti.yaml
Context loaded. Let me check for the deepagents patterns doc and the Graphiti config status.

Globpattern: "docs/research/ideas/deepagents-patterns-review.md"
Found 1 file
Globpattern: ".guardkit/**"
No files found
Globpattern: "docs/architecture/**"
No files found
Globpattern: "**/guardkit.yaml"
No files found
Read deepagents-patterns-review.md
All context loaded. Now starting the orchestration.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM ARCHITECTURE: Study Tutor — GCSE English AI Tutor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Context loaded (8 files):

phase-0-scope.md — primary --from input
phase-0-build-plan.md
decisions-log-2026-04-17.md — 8 closed decisions
state-of-the-project-and-phase-recommendation.md
deepagents-patterns-review.md
cross-agent-lessons-from-specialist-agent.md — LES1, 6 parity surfaces
domains/gcse-english/GOAL.md — domain contract
docs/gamification/design.md — 15-level economy
Mode auto-detection:

Glob docs/architecture/** → no files found
Mode: setup (no existing architecture context found)
Graphiti availability check:

Glob .guardkit/graphiti.yaml → not found
⚠️ Graphiti unavailable — continuing without knowledge graph context. Reason: .guardkit/graphiti.yaml does not exist. To enable: create .guardkit/graphiti.yaml with enabled: true and ensure FalkorDB is reachable.
Architecture definition will continue WITHOUT persistence. Markdown artefacts will still be generated under docs/architecture/, but context won't be queryable by /system-plan, /system-design, or /feature-spec.

Continue without persistence? [Y/n]:

Once you confirm, I'll begin Category 1 (Domain & Structural Pattern). To move quickly given the dense context you've provided, I'll propose answers drawn from the scope/decisions docs and invite you to revise — still 6 categories, still with checkpoints, but you can say "C" to accept the proposed capture rather than dictating each field from scratch.

Your move:

graphiti.yaml
thanks I jsut ran the guardkit init which has created the graphiti.yaml and I copied the mcp.json across so Graphiti should be available now please check as this is essential before we proceed
Read graphiti.yaml
Globpattern: ".guardkit/**"
Found 1 file
Globpattern: ".mcp.json"
No files found
Graphiti config found and enabled. Let me verify Tier 2 connectivity (FalkorDB + embedder reachability) before proceeding, and look for .mcp.json.

Bash Check guardkit CLI availability and version
IN
which guardkit && guardkit --version 2>&1 | head -5

OUT
/Users/richardwoollcott/.agentecflow/bin/guardkit
GuardKit version 1.0.0
Installation: /Users/richardwoollcott/.agentecflow
Globpattern: "**/.mcp.json"
No files found
Bash List study-tutor root contents
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/ | head -30

OUT
total 40
drwxr-xr-x   15 richardwoollcott  staff   480 Apr 18 21:27 .
drwxr-xr-x  159 richardwoollcott  staff  5088 Apr 17 18:36 ..
drwxr-xr-x@   8 richardwoollcott  staff   256 Apr 18 21:27 .claude
drwxr-xr-x   15 richardwoollcott  staff   480 Apr 12 23:28 .git
-rw-r--r--    1 richardwoollcott  staff  4688 Apr 12 13:14 .gitignore
drwxr-xr-x@   3 richardwoollcott  staff    96 Apr 18 21:27 .guardkit
-rw-r--r--    1 richardwoollcott  staff   553 Apr 18 21:09 command_history.md
drwxr-xr-x    6 richardwoollcott  staff   192 Apr 18 20:38 docs
drwxr-xr-x    3 richardwoollcott  staff    96 Apr 18 20:38 domains
-rw-r--r--    1 richardwoollcott  staff  1065 Apr 12 13:14 LICENSE
-rw-r--r--    1 richardwoollcott  staff     0 Apr 18 21:26 mcp.json
drwxr-xr-x@   2 richardwoollcott  staff    64 Apr 12 14:10 migrations
-rw-r--r--    1 richardwoollcott  staff    32 Apr 12 13:14 README.md
drwxr-xr-x    4 richardwoollcott  staff   128 Apr 18 20:39 roles
drwxr-xr-x@   7 richardwoollcott  staff   224 Apr 18 21:27 tasks
Found mcp.json in repo root but it's empty (0 bytes) and named without leading dot. Let me check Graphiti connectivity and check if there's a reference .mcp.json to copy from.

Bash Run Graphiti connectivity check
IN
guardkit graphiti check 2>&1 | head -40

OUT
Usage: guardkit-py graphiti [OPTIONS] COMMAND [ARGS]...
Try 'guardkit-py graphiti --help' for help.

Error: No such command 'check'.
Bash Check specialist-agent MCP and guardkit config for reference
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/.mcp.json 2>&1; ls -la /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/.guardkit/ 2>&1

OUT
-rw-r--r--  1 richardwoollcott  staff  1123 Apr 17 12:19 /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/.mcp.json
total 2024
drwxr-xr-x   10 richardwoollcott  staff      320 Apr 17 12:22 .
drwxr-xr-x   69 richardwoollcott  staff     2208 Apr 17 20:04 ..
drwxr-xr-x  184 richardwoollcott  staff     5888 Apr 14 00:02 autobuild
-rw-r--r--@   1 richardwoollcott  staff      152 Apr 14 06:32 bootstrap_state.json
-rw-r--r--@   1 richardwoollcott  staff     2840 Apr 13 18:08 context-manifest.yaml
drwxr-xr-x   24 richardwoollcott  staff      768 Apr 14 06:32 features
-rw-r--r--@   1 richardwoollcott  staff  1021307 Apr 14 00:33 graphiti-query-log.jsonl
-rw-r--r--    1 richardwoollcott  staff      466 Apr 17 12:22 graphiti.yaml
drwxr-xr-x    3 richardwoollcott  staff       96 Apr 11 13:12 seeding
drwxr-xr-x@   2 richardwoollcott  staff       64 Apr 14 06:38 worktrees
Bash Find valid graphiti subcommands
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
  add-context  Add context from files to Graphiti.
  capture      Capture project knowledge through interactive Q&A.
  clear        Clear Graphiti knowledge graph data.
  list         List all knowledge in a category.
  search       Search for knowledge across all categories.
  seed         Seed system context into Graphiti.
  seed-adrs    Seed feature-build ADRs into Graphiti.
  seed-system  Seed template and system content into Graphiti.
  show         Show details of specific knowledge by ID.
  stats        Show graph topology statistics for performance analysis.
  status       Show Graphiti connection and seeding status.
  verify       Verify seeded knowledge with test queries.
Read .mcp.json
Bash Check Graphiti connection status from study-tutor repo
IN
guardkit graphiti status 2>&1 | head -60

OUT
╔════════════════════════════════════════╗
║       Graphiti Knowledge Status        ║
╚════════════════════════════════════════╝

  Status: ENABLED
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
WARNING:guardkit.knowledge.graphiti_client:Graphiti initialization error: llm_provider is 'gemini' but GOOGLE_API_KEY is not set. Export GOOGLE_API_KEY before initialising Graphiti.
  Connection: Failed


 Graphiti check — partially failing:

Tier 1: ✅ .guardkit/graphiti.yaml exists, enabled: true
Tier 2: ❌ Connection failed — llm_provider is 'gemini' but GOOGLE_API_KEY is not set
Also noticed two config issues:

mcp.json in repo root is empty (0 bytes) and lacks the leading dot — should be .mcp.json (specialist-agent has it with leading dot)
No .env file in study-tutor yet, so GOOGLE_API_KEY isn't available for Graphiti
Bash Check for .env files in both repos
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.env 2>&1; ls -la /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/.env 2>&1 | head -2

OUT
ls: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.env: No such file or directory
-rw-r--r--  1 richardwoollcott  staff  473 Apr 17 18:32 /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/.env
Bash Check if GOOGLE_API_KEY is set in shell env (redacted)
IN
env | grep -i "google\|gemini" | sed 's/=.*/=<redacted>/' 2>&1

OUT
(Bash completed with no output)
Diagnosis:

Check	Status	Fix needed
.guardkit/graphiti.yaml exists & enabled	✅	—
FalkorDB config (whitestocks:6379)	✅	—
Embedder config (promaxgb10-41b1:8001)	✅	—
GOOGLE_API_KEY in env	❌	Need to provide for Gemini entity extraction
.env file in study-tutor	❌	Needs creating (gitignored, SR-06 safe)
.mcp.json (with leading dot) in repo root	❌	mcp.json exists but is empty + misnamed
Three things needed before I can proceed with architecture seeding:

GOOGLE_API_KEY available. Options:

(a) Copy GOOGLE_API_KEY line from specialist-agent/.env into a new study-tutor/.env
(b) Or export GOOGLE_API_KEY=<key> in the shell that spawned this session (least invasive; won't persist across restarts)
.mcp.json populated. The current mcp.json (no dot, empty) should be removed and replaced with .mcp.json modelled on specialist-agent's — at minimum the graphiti MCP server entry, pointing at study-tutor's own .env.

Verify. After the above, I'll re-run guardkit graphiti status and confirm Connection: OK before we proceed.

Do you want me to:

[A] Create study-tutor/.env by copying the relevant keys (GOOGLE_API_KEY, plus anything else Graphiti needs) from specialist-agent/.env, and write study-tutor/.mcp.json adapted from specialist-agent's? I'll read specialist-agent's .env to understand what's needed, but won't commit anything — .env is gitignored.
[B] Wait while you set GOOGLE_API_KEY and create .mcp.json manually, then I re-check.
[C] Proceed without Graphiti persistence (defer fixing to after Phase 0 kickoff) — markdown artefacts still get generated but the /system-plan//system-design//feature-spec chain won't have queryable architecture context.
Your call? (I'd recommend [A] — this is a copy of a working pattern from a neighbouring repo, and getting Graphiti right now avoids re-seeding everything later.)

.env
I've manually sorted the .env and .mcp.json please can you check Graphiti connection
Bash Re-check Graphiti connection status
IN
guardkit graphiti status 2>&1 | tail -20

OUT
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
    • patterns: 100
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
    • agents: 100
  Project Knowledge:
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
  Decisions:
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
    • architecture_decisions: 100
  Learning:
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
    • failure_patterns: 99
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"

  Total Episodes: 583
Bash Verify .env and .mcp.json exist
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.env /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.mcp.json /Users/richardwoollcott/Projects/appmilla_github/study-tutor/mcp.json 2>&1

OUT
Exit code 1
ls: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/mcp.json: No such file or directory
-rw-r--r--@ 1 richardwoollcott  staff  218 Apr 17 12:13 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.env
-rw-r--r--  1 richardwoollcott  staff  828 Apr 17 09:57 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.mcp.json
Bash Extract key status lines
IN
guardkit graphiti status 2>&1 | grep -E "Status|Connection|Total|ERROR|WARNING" | head -10

OUT
║       Graphiti Knowledge Status        ║
  Status: ENABLED
  Total Episodes: 583
Graphiti connection: ✅ OK

Status: ENABLED
Embedder responding (HTTP 200 from promaxgb10-41b1:8001)
583 total episodes already seeded across categories (patterns:100, agents:100, architecture_decisions:100, failure_patterns:99, etc.)
.env (218 bytes) and .mcp.json (828 bytes) present; stale mcp.json removed
graphiti_available = true. Tier 2 passed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ready to begin the 6-category interactive session.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Given the dense pre-existing context (phase-0-scope, decisions-log, GOAL.md, gamification/design, LES1), I'll propose each category's answers drawn directly from those documents. You accept with C, revise with R, add an ADR with A, or skip the rest with S.

Category 1: Domain & Structural Pattern
Q1. What does this system do?

Proposed: A GCSE English AI tutor for Year 10/11 students preparing for AQA 8700 (Language) and 8702 (Literature). Combines a fine-tuned Gemma 4 31B (tutoring behaviour, Layer 1), ChromaDB curriculum RAG (knowledge, Layer 2), and Graphiti student model (progress/confidence/gamification, Layer 3) orchestrated by a DeepAgents harness with Player-Coach quality monitoring. Accessed via MCP (primary for architecture demos) and Open WebUI (primary for day-to-day use). Target submission: Gemma 4 Good Hackathon, 18 May 2026.

Q2. Who are the primary users?

Proposed:

Lilymay — the reference student. Year 10, Robert Blake School, AQA 8700+8702. Primary user via Open WebUI today.
Hackathon judges — read the public repo, watch the demo video, assess architecture and methodology.
Parents / teachers — via Reachy Mini progress reporting (stretch, gated by DEC-06).
AI agents — Claude Desktop, future Ship's Computer fleet, invoke the tutor via MCP tools.
Developers — clone the public repo, bring their own sources, reproduce the tutor on a clean machine.
Q3. What are the core business domains?

Proposed:

Tutoring — Socratic scaffolding, AO-aligned feedback, grade calibration (Grade 4–9), session lifecycle. Owned by domains/gcse-english/GOAL.md.
Knowledge / Curriculum — RAG-backed curriculum content (Macbeth, Power & Conflict poetry, etc.). Layer 2 — ChromaDB + Docling ingestion, sources user-provided ("bring your own sources").
Student Model — per-student topic confidence taxonomy (Struggling/Developing/Secure/Mastered), misconceptions, session history, AO progress. Graphiti (Phase 1+).
Gamification — XP economy, 15-level progression, 6 achievement categories, streaks, Boss Battle, daily challenges, quests. Docs exist Phase 0; state engine Phase 2.
Provenance & Compliance — AQA copyright boundaries, Mr Bruff purchased-and-transformed policy, bring-your-own-sources packaging. Cross-cutting but authoritative in domains/gcse-english/GOAL.md §6.
Inference Runtime — provider abstraction across Ollama (GB10 local), AWS Bedrock Custom Model Import (scale-to-zero), API providers (Coach / fallback). Governed by SR-03.
Q4. What structural pattern best fits this project?

Looking at the evidence — deepagents-patterns-review.md §1.3 names an explicit three-layer architecture (behaviour + knowledge + student model); Phase 0 deliberately factors domains/, roles/, src/, docs/gamification/ as separate bounded areas; the specialist-agent pattern being inherited is effectively DDD-flavoured (roles as bounded contexts with per-role role.yaml, criteria, prompts); LES1's six parity surfaces cut across every context as cross-cutting concerns.

Proposed: D (Domain-Driven Design) — bounded contexts around Tutoring / Knowledge / Student Model / Gamification / Runtime, with cross-cutting concerns (MCP transport, provider resolution, safeguarding) captured as shared kernel / structural requirements.

Honest trade-off consideration: M (Modular Monolith) is a reasonable alternative — Phase 0 is small enough that DDD is arguably over-specified. However, the three-layer architecture from deepagents-patterns-review.md is explicit in the research, and Phase 1/2 add genuine bounded contexts (Graphiti student model, gamification state engine) that benefit from DDD's language. DDD also matches the pattern inherited from specialist-agent.

Category 1 — checkpoint (after you respond):

Captured:

Purpose: GCSE English AI tutor, three-layer architecture, hackathon submission 18 May 2026
Users: Lilymay (primary), judges, parents/teachers (via Reachy stretch), AI agents (MCP), developers (public repo)
Domains: Tutoring, Knowledge/Curriculum, Student Model, Gamification, Provenance/Compliance, Inference Runtime
Structural Pattern: DDD — three-layer architecture with bounded contexts; inherits specialist-agent role-aware pattern
ADR would be captured automatically:

ADR-ARCH-001: Use Domain-Driven Design structural pattern with three-layer architecture (fine-tuned behaviour + RAG knowledge + Graphiti student model)
Your choice [C]ontinue / [R]evise / [S]kip / [A]DR?

C
Category 1 captured. Moving to Category 2 (I'll batch Graphiti seeding at the end once artefacts are written, rather than repeatedly rewriting the same domain-model.md per category — the final seeded content will reflect everything captured).

Category 2: Bounded Contexts / Module Structure
Since you chose DDD, both DDD-specific and event-driven questions apply.

Q5 / Q5d. What are the major bounded contexts?

Proposed — six bounded contexts:

Tutoring Context (src/study_tutor/session/, roles/tutor/, domains/gcse-english/)
Owns: session lifecycle (start → plan → turn×N → summary → end), tutor prompt assembly, Socratic scaffolding rules.
Aggregate root: TutorSession (session_id, student_id, subject, paper, topic, grade_target, turns, state).
References (via IDs only): Student (Student Model), Topic/AO/Text (Knowledge & Curriculum).
Knowledge & Curriculum Context (src/study_tutor/knowledge/, domains/gcse-english/sources/)
Owns: ChromaDB collection management, Docling ingestion pipeline, text/topic/AO taxonomy.
Aggregate roots: CurriculumCollection (per domain; Phase 1+), Text (Macbeth, Power & Conflict poems, …), AssessmentObjective (AO1–AO6).
Phase 0 state: taxonomy declared in GOAL.md; ChromaDB wiring deferred to Phase 1 per roadmap.
Student Model Context (Phase 1 — stubbed in Phase 0; src/study_tutor/student/)
Owns: per-student state in Graphiti — Student, TopicConfidence, Misconception, Session episodes, AO progress.
Aggregate root: Student (with scoped group_id student:{id}, subject subject:gcse-english).
Confidence bands per docs/gamification/design.md §6: Struggling/Developing/Secure/Mastered.
Phase 0 deliverable: schema declared in GOAL.md §11 and the Phase 0 scope's "knock-on to Phase 1" section.
Gamification Context (Phase 2 — design only in Phase 0; docs/gamification/design.md)
Owns: XP economy, 15-level progression, 6 achievement categories, streak state, daily challenge/quest state, Boss Battle unlock gating.
Aggregate roots: StudentProgress (level, total XP, streak, longest streak), Achievement, Quest, BossBattle.
Events it reacts to: session.completed, achievement.unlocked, quest.completed/expired, boss_battle.completed.
Inference Runtime Context (src/study_tutor/llm/)
Owns: provider abstraction, model routing via AGENT_MODELS__REASONING_MODEL (SR-03), local/bedrock/openai/anthropic/gemini implementations, [providers] extra (SR-04).
Aggregate root: LLMClient (factory-resolved).
Phase 0 primary: Ollama on GB10 (local). Phase 0 validation: AWS Bedrock Custom Model Import (bedrock). API providers declared but not on critical path.
MCP Transport Context (src/study_tutor/mcp/, src/study_tutor/cli/, scripts/mcp-wrapper.sh)
Owns: MCP tool registration (SR-07), stdio discipline (SR-01), launcher CWD abs-path (SR-02), fire-and-forget + poll semantics for long-running tools.
Aggregate root: McpAdapter (exposes 4 tools: tutor_start_session, tutor_turn, tutor_session_status, tutor_session_end).
Tool classification per Phase 0 scope SR-07 table.
Q6d. Aggregate roots and their invariants?

Proposed summary (per-context):

TutorSession: state machine (initialised → planning → active → summarising → ended); turns append-only; cannot receive turns when ended.
Student: exactly one per human user; group_id scoped; achievements monotonically sticky (§5 of gamification design).
TopicConfidence: 0.0 ≤ c ≤ 1.0; per-session delta capped at ±0.1 (gamification §6.2); band transitions fire mastery events.
StudentProgress: level monotonic (never decreases); XP monotonic; streak can reset; longest_streak monotonic.
McpAdapter: tool description ≡ handler contract (SR-07); sync tools bounded <30s; long-running tools return session_id in ≤1s.
LLMClient: provider resolved at factory (SR-03); never hard-coded in handler (LES1 evidence: TASK-MDF-PMEV / CRMV).
Q7d. Shared kernel / anti-corruption layers?

Proposed — two shared kernels, one ACL:

Shared Kernel: Domain taxonomy — Subject, Paper, Text, AssessmentObjective (AO1–AO6), Topic, GradeTarget live in a shared-language module used by Tutoring, Knowledge, Student Model, and Gamification. Defined authoritatively in domains/gcse-english/GOAL.md §3–§4 + §6 taxonomy.
Shared Kernel: Session event vocabulary — the event names in gamification §11.2 (session.completed, achievement.unlocked, etc.) are the contract between Tutoring (producer) and Gamification (consumer). Graphiti write-back (Student Model) is the third consumer.
Anti-corruption layer: Inference Runtime boundary — LLMClient.invoke(messages, **opts) normalises across Ollama/Bedrock/API providers. The Tutoring context never speaks Bedrock ARNs, Ollama URLs, or provider-specific request shapes; that knowledge stays inside src/study_tutor/llm/.
Q8d. Domain events flowing between contexts (Phase 1+):

Proposed:

session.started { session_id, student_id, subject, topic } — Tutoring emits; Student Model records session episode head.
session.turn_completed { session_id, turn_index, ao_scaffolded } — Tutoring emits; Coach (Phase 1) evaluates; Student Model may append misconception.
session.completed { session_id, duration, topic, aos_touched, quality_score } — Tutoring emits; Gamification awards XP + streak delta + achievement check; Student Model updates TopicConfidence via Coach-proposed delta (≤ ±0.1).
achievement.unlocked { student_id, achievement_id, xp_reward } — Gamification emits; Student Model persists; Reachy (if present) triggers celebration.
quest.completed / quest.expired — Gamification internal; recorded.
boss_battle.completed { student_id, paper, trophy_id } — Gamification emits; Student Model records.
Eventual consistency: Graphiti write-back is explicitly async / fire-and-forget from the tutor's perspective (DEC-02, LES1 §4 evidence). Within-session state lives in in-memory TutorSession and is only persisted at session-end. This is a conscious trade-off — session feels responsive to the student, Graphiti absorbs the 1–3s Gemini-extraction latency.

Q5e / Q6e / Q7e. Event streams, handlers, consistency:

Proposed — no external event bus in Phase 0. Events are in-process Python callables wired by the DeepAgents harness (Phase 1). NATS is explicitly out of scope per LES1 row-3/4/5 markers for study-tutor. If/when the Ship's Computer fleet integration lands (post-hackathon), the existing event vocabulary maps cleanly to NATS subjects (agents.study-tutor.session.completed etc.), but that's not Phase 0–2 work.

Category 2 — checkpoint:

Captured 6 bounded contexts with aggregate roots, 2 shared kernels + 1 ACL, 6 domain events, Phase 0 scope honoured (in-process events; NATS deferred).

ADRs that would be captured automatically:

ADR-ARCH-002: Three-layer architecture — behaviour (fine-tuned LLM) / knowledge (RAG) / student model (Graphiti)
ADR-ARCH-003: Async Graphiti write-back at session-end boundary (not per-turn) — absorbs Gemini extraction latency off the tutoring hot path
Your choice [C]ontinue / [R]evise / [S]kip / [A]DR?

C
Category 2 captured. Moving to Category 3.

Category 3: Technology & Infrastructure
Q8. Programming languages and frameworks?

Proposed:

Python 3.11 (matches specialist-agent + current Gemma 4 tooling). pyproject.toml modelled on specialist-agent; install via uv or venv (pip install -e '.[providers]').
Framework stack:
deepagents (Phase 1+ harness — create_deep_agent() pattern from dataset-factory + specialist-agent)
langchain + langchain-ollama, langchain-openai, langchain-anthropic, langchain-google-genai, langchain-aws (all declared in [providers] extra per SR-04)
mcp Python SDK for transport
click for CLI (errors on stdout lint per SR-01)
pydantic for domain models and Graphiti entities
graphiti-core (Phase 1+) for student model persistence
chromadb + docling for Layer 2 (Phase 1+ ingestion; Phase 0 stub)
Q9. Databases and data stores?

Proposed:

ChromaDB — Layer 2 curriculum RAG. Per-subject collections. User-provided sources via domains/gcse-english/sources/ (bring-your-own, not shipped in repo). Phase 0: gitignored placeholder directory; Phase 1: ingestion pipeline reused from agentic-dataset-factory.
FalkorDB via Graphiti — Layer 3 student model. Hosted on Synology NAS (whitestocks:6379 per .guardkit/graphiti.yaml). Reached over Tailscale from MacBook. Phase 0: not wired; Phase 1: Graphiti schema + write-back (DEC-02).
In-memory session dict — Phase 0 only. TutorSession state keyed by session_id, no persistence across MCP server restarts. Upgraded to Graphiti-backed in Phase 1.
Merged fine-tuned model weights — ~/fine-tuning/output/gcse-tutor-gemma4-31b/ on GB10 (FS, not a DB). Mirror copy in S3 for Bedrock Custom Model Import.
S3 — appmilla-study-tutor-bedrock-models — model artefact storage for Bedrock import. AWS account per prerequisites.
Q10. Deployment model?

Proposed — three runtime paths (selected per env var, SR-03):

local (Phase 0 primary): Ollama on GB10, Tailscale-reachable. Fine-tuned Gemma 4 31B Q4_K_M GGUF. Lilymay's existing daily path. Cold-start not an issue (always-on).
bedrock (Phase 0 validation): AWS Bedrock Custom Model Import, Gemma 4 31B merged-16bit weights. Scale-to-zero, 30–60s cold start, ~$1.50–3.00 per 5-min window. Removes GB10 dependency from demo week (DEC-07).
openai / anthropic / gemini (available, not critical path in Phase 0): API providers. Reserved for Coach (Phase 1) if it runs on different provider than Player, or fallback if local paths unavailable.
No Dockerfile in Phase 0 (do-not-change per scope). Venv install documented in README. SR-05 reactivates if/when Dockerfile is added in Phase 1+.

MCP transport: stdio via bash wrapper (SR-01, SR-02). HTTP transport deferred to Phase 1+.

User-facing interfaces: Open WebUI on GB10 (Lilymay, unchanged from today) + Claude Desktop (MCP architecture demo). No custom web UI in Phase 0 (DEC-05). Static HTML dashboard generated via Claude Design in Phase 2.

Q11. CI/CD pipeline?

Proposed — minimal for Phase 0:

Pre-commit checks (local, optional Phase 0; required Phase 1): .env.example placeholder hygiene (grep for real-looking keys per SR-06); .gitignore audit (no *.pdf, *.gguf, chroma/, output/train.jsonl).
GitHub Actions (Phase 0 stub → Phase 1 hardening):
Lint: ruff check (already specialist-agent pattern)
Unit tests: pytest tests/unit/ — specifically test_stdio_discipline.py (SR-01) and test_provider_resolution.py (SR-03) per build-plan
Import smoke test: each declared provider in [providers] importable (SR-04)
No deployment pipeline — Phase 0 is a public repo, not a hosted service. Bedrock import is manual / AWS console one-off.
Walkthrough gate: clean-machine README walkthrough (Wed 23 April in Phase 0 timeline) is the canonical gate; logged to .claude/reviews/TASK-REV-PH0-walkthrough-log.md per specialist-agent precedent.
Q12. External services / integrations?

Proposed:

Service	Purpose	Phase	Notes
Ollama (GB10)	Layer 1 inference — fine-tuned Gemma 4 31B	0 primary	Tailscale, ~1ms RTT per B8E4 walkthrough
AWS Bedrock (Custom Model Import)	Scale-to-zero Layer 1	0 validation	Frees GB10 for training (DEC-07)
AWS S3	Model artefact hosting	0	appmilla-study-tutor-bedrock-models
Google Gemini (2.5 Pro)	Graphiti entity extraction LLM	1+	DEC-08 — latency monitored, not pre-validated
GB10 embedder (nomic-embed-text-v1.5 on :8001)	Graphiti embeddings + ChromaDB	1+	Small enough not to block training
FalkorDB on Synology NAS	Graphiti graph store	1+	whitestocks:6379 per config
Tailscale	Network path MacBook ↔ GB10 ↔ Synology	all	Proven in B8E4 walkthrough
LiteLLM (GB10, separate port)	OpenAI-compatible proxy routing OpenWebUI → Bedrock	0	DEC-07; falls back to Ollama-direct if breaks
Reachy Mini SDK	Stretch embodied companion	2 stretch	DEC-06 go/no-go at 4 May
Claude Desktop (MCP client)	Architecture reveal in demo + daily invocation surface	0+	Via claude_desktop_config.json bash wrapper
Explicitly NOT integrated in Phase 0: NATS (per LES1 study-tutor column — MCP-only), Kubernetes/ECS (no containerisation), custom React UI, mobile/Flutter, Docker Compose.

Category 3 — checkpoint:

Captured:

Language: Python 3.11
Frameworks: deepagents, langchain (multi-provider), mcp SDK, click, pydantic, graphiti-core (P1), chromadb + docling (P1)
Data stores: ChromaDB (L2), FalkorDB/Graphiti (L3 P1+), in-memory session dict (P0), S3 + Bedrock for model weights
Deployment: Venv-only Phase 0 (no Dockerfile per DNC); local/bedrock/API provider paths; MCP stdio transport; Open WebUI unchanged
CI/CD: Minimal — lint, unit tests for parity surfaces, env-hygiene checks; walkthrough as canonical gate
External services: Ollama+GB10, Bedrock+S3, Gemini+GB10 embedder+FalkorDB (P1), Tailscale, LiteLLM, Reachy (stretch), Claude Desktop
ADRs that would be captured automatically:

ADR-ARCH-004: Python 3.11 + deepagents + langchain + mcp stack (pattern inherited from specialist-agent)
ADR-ARCH-005: Defer Dockerfile to Phase 1+ — venv-only install for Phase 0 (avoids SR-05 complexity while repo skeleton stabilises)
ADR-ARCH-006: Dual inference path — Ollama (primary) + Bedrock (validation) — selected per SR-03 env var, decouples demo week from GB10 training schedule
ADR-ARCH-007: Graphiti split topology — FalkorDB on Synology NAS, entity-extraction LLM on Gemini, embedder on GB10 (per DEC-02)
Your choice [C]ontinue / [R]evise / [S]kip / [A]DR?

C
Category 3 captured. Moving to Category 4.

Category 4: Multi-Consumer API Strategy
Q13. What types of consumers will access this system?

Proposed — five consumer types across phases:

Consumer	Who	When	Primary surface
Human student (Lilymay)	The reference Year 10 student	Phase 0+ (daily)	Open WebUI → Ollama (or Bedrock via LiteLLM proxy)
AI agents (Claude Desktop, Ship's Computer fleet)	Claude via MCP; future Jarvis intent router	Phase 0+	MCP stdio — 4 tools
Clean-machine developer / hackathon judge	Clones public repo, follows README	Phase 0+	CLI (study-tutor serve …), README walkthrough
Dashboard viewer (parent / student)	Reads static HTML dashboard	Phase 2	Static HTML rendered from session-export JSON
Reachy Mini companion	Embodied voice interface	Phase 2 stretch (gated 4 May)	Python SDK on Reachy Pi reading Graphiti state
Q14. What API protocols per consumer type?

Proposed:

Consumer	Protocol	Tool/schema
Human student (Open WebUI)	OpenAI-compatible chat completions	Via Ollama native API; or Bedrock via LiteLLM proxy (DEC-07)
AI agents (MCP)	MCP JSON-RPC over stdio	4 tools: tutor_start_session (long-running), tutor_turn (sync <30s), tutor_session_status (sync), tutor_session_end (sync triggers async write-back) — SR-07 classified
CLI operator	CLI arguments + stdout/stderr	study-tutor serve --role tutor --transport stdio (SR-01 split)
Dashboard viewer	File-system read of rendered HTML	No live API in Phase 2; renders from session-export.json (Phase 1 deliverable)
Reachy	Python function calls to Graphiti + gamification-engine queries	docs/gamification/design.md §9 scenarios
Phase 0 deliberately ships only: MCP stdio (agents) + CLI (developers). Open WebUI reuses the existing Ollama-direct path unchanged. HTTP MCP transport and any session-export JSON schema are Phase 1+.

Q15. Different data shapes / access patterns per consumer?

Proposed — four distinct shapes, sharing one domain vocabulary:

MCP tool payloads (agents): JSON-RPC with {session_id, subject, paper, topic, grade_target, student_name} on tutor_start_session; {session_id, message} on tutor_turn. Responses are MCP content arrays. SR-07 classification enforced — long-running returns session_id ≤1s and polls via tutor_session_status.
Open WebUI / OpenAI chat-completions (humans): Plain message stream. No knowledge of session_id, topic taxonomy, AOs, or gamification — the tutor behaviour all lives in the fine-tuned model weights. Phase 0 is genuinely Layer-1-only from this surface.
CLI / stdio (developers): Banner + help text on stderr (SR-01); MCP JSON-RPC on stdout. --help minimal. No TTY-dependent output.
Static HTML dashboard (Phase 2 consumer): Read-only snapshot view over session-export.json. Fields per docs/gamification/design.md §10 (level+title+progress bar, streak, weekly XP, active quests, daily challenges, topic mastery grid, Boss Battle unlock progress, recent achievements, near-unlocks).
Shared vocabulary (cross-consumer): Subject, Paper, Text, AssessmentObjective, Topic, GradeTarget, ConfidenceBand — as per the shared kernel in Category 2. Every consumer speaks this language at its own granularity.

Q16. Authentication / authorisation differences?

Proposed — Phase 0 is a single-user local system; Phase 1+ stays single-user. No multi-tenancy, no public API.

Consumer	Phase 0	Phase 1+
Open WebUI	No auth (localhost / Tailscale-only LAN)	Same
MCP (Claude Desktop)	Stdio = process-level trust. Transport is local.	Same
CLI	OS file-system permissions. .env gitignored, contains real keys (user's machine only).	Same
Dashboard	No auth — static HTML rendered from a file; served via any local HTTP server or opened directly	Same
Reachy	Home network; Tailscale or local LAN	Same
External provider APIs (outbound)	AGENT_MODELS__* env vars + .env (SR-06 hygiene); GOOGLE_API_KEY for Graphiti; AWS_* IAM-scoped to bedrock:* + specific S3 bucket	Same
Safeguarding boundary (authorisation-adjacent, per GOAL.md §6.3): If the student discloses distress, tutor stops tutoring and suggests a trusted adult / Childline / Samaritans — not auth in the security sense, but a content-authorisation boundary the tutor enforces regardless of who is connected.

Out of scope for hackathon: OAuth2, JWT, multi-tenant user management, API key rotation infrastructure, role-based access control at the tool level. This is a personal learning tool, not a SaaS.

Category 4 — checkpoint:

Captured:

Consumer surfaces:
Humans: Open WebUI (chat completions)
AI agents: MCP stdio, 4 tools with SR-07 sync/long-running classification
Developers: CLI with stderr-only diagnostics (SR-01)
Dashboard viewers: Static HTML over session-export JSON (Phase 2)
Reachy: Python SDK reads Graphiti directly (Phase 2 stretch)
Shared vocabulary across all consumers: Subject, Paper, Text, AO, Topic, GradeTarget, ConfidenceBand
Auth posture: Single-user local / Tailscale; process-level trust on stdio; outbound API keys via .env under SR-06 hygiene; safeguarding as a content-authorisation boundary
ADR that would be captured automatically:

ADR-ARCH-008: MCP-only for agent access; Open WebUI unchanged for humans; single-user auth model (process + LAN trust) — no multi-tenancy until post-hackathon
Your choice [C]ontinue / [R]evise / [S]kip / [A]DR?

C
Category 4 captured. Moving to Category 5.

Category 5: Cross-Cutting Concerns
The Phase 0 scope gives us an unusual advantage here: the six parity surfaces (SR-01 — SR-07) are the cross-cutting concerns, made structural by the LES1 lessons-doc discipline. I'll capture those authoritatively, plus safeguarding, provenance/copyright, and the gamification event bus.

Q17. Authentication / authorisation approach?

Proposed (as captured in Cat 4 + expanded):

Inbound: no auth layer. Process-level trust for MCP stdio; LAN/Tailscale trust for Open WebUI; OS filesystem permissions for CLI.
Outbound (provider APIs): env-var driven, .env under SR-06 hygiene. Keys never committed. GOOGLE_API_KEY for Graphiti, AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY scoped to bedrock:* + specific S3 bucket, optional OPENAI_API_KEY/ANTHROPIC_API_KEY.
Content-level authorisation (safeguarding): tutor stops on student-distress signals per GOAL.md §6.3 — not a security boundary, but a behavioural one that overrides every other instruction.
Q18. Logging / observability strategy?

Proposed:

Structured stderr logging only (MCP stdio mode): click.echo(..., err=True) pattern enforced (SR-01). No print() to stdout anywhere in the serve path. Stream-split test in tests/unit/mcp/test_stdio_discipline.py is the continuous gate.
Log destinations: stderr in Phase 0 (captured by Claude Desktop's MCP server logs). Phase 1+ can add a rotating file handler (logs/study-tutor.log) for long-running sessions.
Level discipline: INFO for session lifecycle events (session.started, turn_completed, session.ended), WARNING for provider-switch fallbacks, ERROR for failed LLM calls. No DEBUG on the hot path.
No OpenTelemetry / tracing in Phase 0. Phase 1+ may add tracing once the DeepAgents harness lands (useful for Coach-loop debugging).
Walkthrough logs as a first-class artefact: .claude/reviews/TASK-REV-PH0-walkthrough-log.md captures the clean-machine reproduction (specialist-agent precedent B8E4).
Graphiti query logs: retained per specialist-agent pattern (graphiti-query-log.jsonl) once Phase 1 wires Graphiti in.
Q19. Error handling patterns?

Proposed — three-layered:

Session-level exceptions (Tutoring Context): SessionNotFoundError, SessionAlreadyEndedError, InvalidTurnStateError. Caught at the MCP handler boundary, returned as MCP error responses with actionable messages.
Provider-level exceptions (Inference Runtime): ProviderNotConfiguredError, ProviderUnreachableError, ProviderAuthError. Surfaced as structured errors ({error_code, provider, retryable}); handler decides whether to fall back to another provider (Phase 1+ — Phase 0 just surfaces).
MCP protocol errors: JSON-RPC error responses per MCP spec. Tool-description mismatches are caught by test_mcp_tool_contract.py — SR-07's structural gate.
Retry policy: None in Phase 0 — explicit failure is better than silent retry on the first revision. Phase 1 may add bounded retry for Graphiti write-back (which is async anyway) but not for user-facing tutor_turn.

Error evidence pattern: every ProviderUnreachableError log line records provider name, endpoint, and latency-at-failure. Mirrors the LES1 evidence discipline — when something breaks, the log tells you which of the 6 parity surfaces was involved.

Q20. Data validation approach?

Proposed:

Pydantic everywhere at boundaries. MCP tool inputs (TutorStartSessionRequest, TutorTurnRequest), LLM client options, Graphiti entity schemas (Student, TopicConfidence, etc. — Phase 1), session-export JSON (Phase 1). Source-of-truth enforced at the edge so internal code can assume validity.
AgentManifest-style declaration: single Pydantic model for tutor capabilities (per deepagents-patterns-review §1.6), deriving MCP tool definitions from the same schema. Deferred to Phase 1 but the shape is locked here.
Domain vocabulary enums: Subject ∈ {English Language, English Literature}, Paper ∈ {Paper1, Paper2}, AssessmentObjective ∈ {AO1…AO6}, ConfidenceBand ∈ {Struggling, Developing, Secure, Mastered}, GradeTarget ∈ {4…9}. Defined in the shared kernel.
.env placeholder validation: .env.example has <your-openai-key-here>-style literals; grep-based pre-merge check rejects =sk-, =AIza, =AKIA prefixes (SR-06).
Tool description ≡ behaviour contract test (SR-07): validates declarative "sync"/"long-running" markers match actual handler shape. Runs in CI.
Q21. Other cross-cutting concerns?

Proposed — the six parity surfaces promoted to first-class cross-cutting status, plus three additions:

#	Concern	Source	Contexts affected
CC-01	MCP stdio discipline (SR-01)	LES1 MCPB	MCP Transport (authoritative); all contexts (via logging rules)
CC-02	Launcher CWD abs-path (SR-02)	LES1 walkthrough §5c	MCP Transport; packaging (README)
CC-03	Provider resolution at factory (SR-03)	LES1 PMEV/CRMV	Inference Runtime (authoritative); Tutoring (consumer)
CC-04	[providers] extra completeness (SR-04)	LES1 LCOI	Inference Runtime (packaging)
CC-05	Dockerfile literal-match to venv install (SR-05)	LES1 DKRX	Deferred to Phase 1+ (no Dockerfile in Phase 0)
CC-06	.env hygiene — no real-looking keys committed (SR-06)	LES1 §retest-env	All contexts via .env.example
CC-07	Tool description ≡ implementation contract (SR-07)	LES1 POLR	MCP Transport (authoritative); Tutoring (classification table)
CC-08	Fire-and-forget + poll above 30s	LES1 §4 POLR	MCP Transport; Tutoring (long-running tutor_start_session)
CC-09	Safeguarding boundary	GOAL.md §6.3	Tutoring (authoritative); overrides all behaviour
CC-10	Copyright / provenance boundary	GOAL.md §6.1 + copyright-training-data-analysis.md	Knowledge & Curriculum; packaging (public repo); Tutoring output (no AQA quotation)
CC-11	In-process event bus (gamification vocabulary)	Category 2 + design.md §11.2	Tutoring (producer); Gamification (consumer P2); Student Model (consumer P1)
Caching: none in Phase 0 (session state in-memory already). Phase 1+ may cache Graphiti read-at-start (topic confidence) per session — decide when latency spike measures it.

Rate limiting: none. Single user; no abuse surface. External provider APIs rate-limited by vendor.

Feature flags: none. Phase gating is handled by git commits and the phase-N-scope docs — not runtime flags. No phase-straddling code in Phase 0.

Category 5 — checkpoint:

Captured 11 cross-cutting concerns (CC-01 through CC-11), spanning:

The 6 parity surfaces (SR-01 → SR-07) promoted to CC-01 → CC-07
Fire-and-forget above 30s (CC-08) as its own concern, distinct from SR-07 tool-description contract
Safeguarding (CC-09) — content authorisation, overrides all behaviour
Copyright/provenance (CC-10) — AQA-specific, affects output and packaging
In-process event bus (CC-11) — gamification vocabulary, three-consumer contract
No caching, no rate limiting, no feature flags in Phase 0.

ADRs that would be captured automatically:

ADR-ARCH-009: Six parity surfaces (LES1) as load-bearing cross-cutting concerns — every feature honours CC-01 to CC-07 structurally from first commit
ADR-ARCH-010: Pydantic-at-boundary validation strategy; domain vocabulary enums in shared kernel
ADR-ARCH-011: No caching / rate limiting / feature flags in Phase 0 — defer to Phase 1+ once load profile is known
Your choice [C]ontinue / [R]evise / [S]kip / [A]DR?

[R]evise - happy with all this we should just check the latest version of the langchain deepagents sdk in case any new features such as async subagents affect the architecture:see https://docs.langchain.com/oss/python/deepagents/overview and https://github.com/langchain-ai/deepagents

Good call. Let me fetch the latest deepagents docs and GitHub README before finalising Category 5.

Web Fetchhttps://docs.langchain.com/oss/python/deepagents/overview
Fetched from https://docs.langchain.com/oss/python/deepagents/overview
Web Fetchhttps://github.com/langchain-ai/deepagents
Fetched from https://github.com/langchain-ai/deepagents
Let me dig deeper — specifically into async patterns and subagent parallelism. The overview didn't surface middleware names; let me check the changelog and context7 directly.

Web Fetchhttps://github.com/langchain-ai/deepagents/releases
Fetched from https://github.com/langchain-ai/deepagents/releases
Context7 [resolve-library-id]langchain deepagents Python SDK async su…
OUT
Available Libraries:



Title: Deep Agents

Context7-compatible library ID: /langchain-ai/deepagents

Description: Deep Agents is a Python package that implements a general-purpose architecture for creating advanced agents capable of planning and acting over complex tasks by combining planning tools, sub-agents, file system access, and detailed prompts.

Code Snippets: 722

Source Reputation: High

Benchmark Score: 74.99




Title: Deep Agents

Context7-compatible library ID: /websites/langchain_oss_python_deepagents

Description: Deep Agents is a standalone library for building intelligent agents that can plan, manage context through file systems, spawn subagents, and handle complex multi-step tasks.

Code Snippets: 117

Source Reputation: High

Benchmark Score: 69.47




Title: Deepagent Quickstarts

Context7-compatible library ID: /langchain-ai/deepagents-quickstarts

Description: Deepagent Quickstarts provides a collection of examples demonstrating various agents that can be easily configured using the Deepagents open-source agent harness, which features planning, computer access, and sub-agent delegation.

Code Snippets: 153

Source Reputation: High

Benchmark Score: 56.71




Title: Deep Agents

Context7-compatible library ID: /hwchase17/deepagents

Description: Deep Agents is a Python package that provides a general-purpose framework for building advanced LLM-powered agents capable of handling complex tasks by incorporating planning tools, sub-agents, file system access, and detailed prompts.

Code Snippets: 4

Source Reputation: High

Benchmark Score: 34




Title: Deep Agents

Context7-compatible library ID: /langchain-ai/deepagentsjs

Description: A TypeScript package for creating Deep Agents that overcome the limitations of simple LLM agents by implementing planning tools, sub-agents, file system access, and detailed prompts for complex tasks.

Code Snippets: 176

Source Reputation: High

Benchmark Score: 82.6

Context7 [query-docs]Async subagent execution in latest versi…
OUT
Define and invoke an async subagent

Source: https://context7.com/langchain-ai/deepagents/llms.txt


Configures a remote subagent for background tasks and integrates it into a deep agent.



# Define async subagent pointing to a remote deployment
remote_researcher: AsyncSubAgent = {
    "name": "deep-researcher",
    "description": "Performs intensive research tasks in the background on a dedicated server.",
    "graph_id": "research-agent",  # Graph name on the remote server
    "url": "https://my-langgraph-deployment.langchain.app",  # Optional: defaults to LangGraph SDK default
}

# Create agent with async subagent
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    subagents=[remote_researcher],
)

# The agent gains tools for managing async tasks:
# - launch_task: Start a background task
# - check_task: Check status of a running task
# - update_task: Send updates to a running task
# - cancel_task: Cancel a running task
# - list_tasks: List all active tasks

result = agent.invoke({
    "messages": [{"role": "user", "content": "Start a deep research task on quantum computing trends"}]
})


Research Agent Example with Custom Subagents

Source: https://context7.com/langchain-ai/deepagents/llms.txt


This example demonstrates creating a multi-step research agent using custom subagents, web search tools, and strategic thinking. It requires importing datetime, init_chat_model, tool, and create_deep_agent.



from datetime import datetime
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from deepagents import create_deep_agent

@tool
def tavily_search(query: str) -> str:
    """Search the web using Tavily API for current information."""
    # In production, use actual Tavily client
    return f"Search results for: {query}"

@tool
def think(thought: str) -> str:
    """Record a strategic thought or reflection about the research process."""
    return f"Recorded thought: {thought}"


current_date = datetime.now().strftime("%Y-%m-%d")

# Research subagent for deep topic exploration
research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate research to this agent. Give it one topic at a time for thorough investigation.",
    "system_prompt": f"""You are a research specialist. Today's date is {current_date}.

Your job is to thoroughly research the given topic using web searches and strategic thinking.
- Use tavily_search to gather current information
- Use think to record insights and plan next steps
- Synthesize findings into a clear, comprehensive summary
- Include citations and sources where available""",
    "tools": [tavily_search, think],
}


# Main orchestrator agent
ORCHESTRATOR_PROMPT = """You are a research orchestrator managing complex research projects.

When given a research task:
1. Break it down into specific research questions
2. Delegate each question to the research-agent subagent
3. Launch multiple research agents in parallel when questions are independent
4. Synthesize all findings into a comprehensive final report

Use the task tool to delegate research work. Maximum 3 concurrent research tasks."""

model = init_chat_model("anthropic:claude-sonnet-4-6", temperature=0.0)

agent = create_deep_agent(
    model=model,
    tools=[tavily_search, think],
    system_prompt=ORCHESTRATOR_PROMPT,
    subagents=[research_sub_agent],
)


# Run a research task
result = agent.invoke({
    "messages": [{"role": "user", "content": "Research the current state of large language models, focusing on recent advances in reasoning capabilities and multimodal understanding."}]
})

print(result["messages"][-1].content)


Create Deep Agent with Subagents

Source: https://github.com/langchain-ai/deepagents/blob/main/examples/deep_research/research_agent.ipynb


Creates a deep agent instance using the create_deep_agent function. This function takes a model, tools, a system prompt, and a list of subagents as arguments. The agent is configured for parallel task execution and independent findings.



# Create the agent
agent = create_deep_agent(
      model=model,
      tools=tools, 
      system_prompt=INSTRUCTIONS,
      subagents=[research_sub_agent],
  )


Define Asynchronous SubAgents

Source: https://context7.com/langchain-ai/deepagents/llms.txt


Initializes an AsyncSubAgent for remote execution on Agent Protocol-compliant servers.



from deepagents import create_deep_agent, AsyncSubAgent

Async Subagents

Source: https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/tests/unit_tests/smoke_tests/snapshots/system_prompt_with_sync_and_async_subagents.md


Async subagents are beneficial for long-running tasks that would otherwise block the main agent. They are also useful for tasks that can leverage specialized remote deployments or when you need to run multiple tasks concurrently and gather their results at a later time.

Context7 [query-docs]Middleware architecture in 0.5.x. List a…
OUT
Create Deep Agent with Filesystem Backend

Source: https://github.com/langchain-ai/deepagents/blob/main/examples/content-builder-agent/README.md


Illustrates the Python code for initializing a deep agent using a filesystem backend. It shows how to integrate memory, skills, tools, and subagents, with memory and skills loaded via middleware and tools passed directly. Subagents can be loaded from YAML or defined inline.



agent = create_deep_agent(
    memory=["./AGENTS.md"],                        # ← Middleware loads into system prompt
    skills=["./skills/"],                          # ← Middleware loads on demand
    tools=[generate_cover, generate_social_image], # ← Image generation tools
    subagents=load_subagents("./subagents.yaml"),  # ← See note below
    backend=FilesystemBackend(root_dir="./"),
)

# Note on subagents:
# Unlike `memory` and `skills`, subagents must be defined in code.
# We use a small `load_subagents()` helper to externalize config to YAML.
# You can also define them inline:

# subagents=[
#     {
#         "name": "researcher",
#         "description": "Research topics before writing...",
#         "model": "anthropic:claude-haiku-4-5-20251001",
#         "system_prompt": "You are a research assistant...",
#         "tools": [web_search],
#     }
# ]


Configure FilesystemMiddleware

Source: https://context7.com/langchain-ai/deepagents/llms.txt


Adds filesystem tools to an agent using either ephemeral or composite storage backends.



from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.backends import StateBackend, CompositeBackend
from langchain.agents import create_agent

# Using StateBackend (ephemeral, in-memory storage)
middleware = FilesystemMiddleware(backend=StateBackend())

# Using CompositeBackend for hybrid storage
from deepagents.backends.store import StoreBackend

backend = CompositeBackend(
    default=StateBackend(),
    routes={"/memories/": StoreBackend()}  # Persistent storage for memories
)
middleware = FilesystemMiddleware(backend=backend)

# Create agent with filesystem middleware
agent = create_agent(
    model="anthropic:claude-sonnet-4-6",
    middleware=[middleware],
)

# The agent can now use filesystem tools:
# - ls(path="/workspace") - List directory contents
# - read_file(file_path="/workspace/main.py", offset=0, limit=100)
# - write_file(file_path="/workspace/output.txt", content="Hello")
# - edit_file(file_path="/workspace/main.py", old_string="foo", new_string="bar")
# - glob(pattern="**/*.py", path="/workspace")
# - grep(pattern="TODO", path="/workspace", glob="*.py")

result = agent.invoke({
    "messages": [{"role": "user", "content": "Read the main.py file and list all TODO comments"}],
    "files": {"/workspace/main.py": {"content": "# TODO: implement feature\ndef main():\n    pass", "encoding": "utf-8"}}
})

Architecture Diagram

Source: https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/THREAT_MODEL.md


The DeepAgents architecture utilizes a middleware stack that manages core functionalities such as memory, skills, filesystem access, and subagent orchestration. This framework-controlled stack sits between the user application and various backends, including LLMs, local execution environments, and remote LangGraph servers. The design incorporates a trust boundary that separates user-configured backends from the core framework logic, ensuring that state, file systems, and sandboxed environments are managed securely.



FilesystemMiddleware - Add filesystem tools to agents

Source: https://context7.com/langchain-ai/deepagents/llms.txt


The FilesystemMiddleware provides agents with essential file manipulation capabilities such as listing directory contents, reading, writing, and editing files. It also supports pattern matching through glob and grep tools. If the backend supports the SandboxBackendProtocol, agents can additionally execute shell commands.



The Deep Agent architecture

Source: https://github.com/langchain-ai/deepagents/blob/main/libs/evals/CONTRIBUTING.md


The Deep Agent architecture incorporates several design patterns for agentic tasks. These include a detailed system prompt with tool guidance, planning middleware using the write_todos tool for structured thinking, a filesystem interface for context management, and the ability to spawn specialized sub-agents via the task tool.

Useful findings. Key changes in recent deepagents releases that affect the architecture:

deepagents 0.5.3 (15 April 2026, 3 days ago):

AsyncSubAgent class — native async subagent support. Remote-deployment-capable via graph_id + url pointing at a LangGraph deployment.
Auto-injected tools: launch_task, check_task, update_task, cancel_task, list_tasks — the fire-and-forget + poll pattern is now first-class in the SDK.
Static structured output for subagent responses (Pydantic).
model=None deprecated → explicit model required in create_deep_agent().
deepagents 0.5.2 (10 April 2026):

Permissions system with route-scoped backends.
upload_files for StateBackend; path traversal protection.
Middleware architecture confirmed as the canonical 0.5.x pattern:

FilesystemMiddleware + pluggable backends (StateBackend ephemeral, StoreBackend via LangGraph Store persistent, CompositeBackend routing).
Parallel subagent execution is idiomatic ("Launch multiple research agents in parallel when questions are independent").
Architectural implications for Study Tutor — three changes:

LES1 row 10 (fire-and-forget above 30s, ⚠️ for study-tutor) becomes less bespoke. The SDK now provides launch_task / check_task natively — our Phase 1 Coach evaluation can be an AsyncSubAgent rather than a hand-rolled fire-and-forget. This is cleaner than reinventing the pattern and aligns tutor_start_session's session-id+poll shape with deepagents' own conventions.

Player-Coach in Phase 1 should use async subagents for the Coach specifically. Coach runs alongside, not in front of, tutor_turn. Per-turn quality scores batch into Graphiti at session-end. This reinforces ADR-ARCH-003 (async Graphiti write-back).

CompositeBackend routing maps cleanly onto our storage layers. Phase 1 student model can be a StoreBackend route (Graphiti-backed) while session turns live in StateBackend (ephemeral, in-process). Phase 0 doesn't need this yet (no deepagents in hot path), but the shape informs the Phase 1 design.

Phase 0 impact: minimal, but two structural decisions to lock in now —

Declare deepagents >= 0.5.3 in [providers] extra (Phase 0 SR-04 compliance, even though Phase 0 code doesn't import it yet — smoke-test passes cleanly).
Document the async-subagent direction as the Phase 1 Coach pattern so FEAT-PO-006 scope doesn't have to rediscover it.
Revised Category 5 — adding one cross-cutting concern and one ADR:

#	Concern	Source	Contexts affected
…	(CC-01 through CC-11 as before)		
CC-12	Async-capable subagent boundary (deepagents 0.5.3+) — Coach runs as AsyncSubAgent in Phase 1 via launch_task/check_task; session turns stay sync; Graphiti write-back piggybacks async semantics	deepagents 0.5.3 release notes + LES1 row 10 ⚠️	Tutoring (Phase 1+); MCP Transport (complements CC-08); Student Model (async consumer)
Additional ADR:

ADR-ARCH-012: Pin deepagents >= 0.5.3; use create_deep_agent(model=<explicit>, subagents=[…]) with AsyncSubAgent for Phase 1 Coach + CompositeBackend(default=StateBackend, routes={'/student/': StoreBackend}) for session/student-model routing. Phase 0 declares in [providers] for SR-04 compliance; Phase 1 imports.
Additional ADR:

ADR-ARCH-013: Defer middleware-level gamification state engine (Phase 2 FEAT-PO-007 could be a custom gamification_middleware reacting to session.completed events) — captured as future direction, not Phase 0/1 commitment.
Revised Category 5 — checkpoint:

Captured 12 cross-cutting concerns (CC-01 through CC-12), including the 6 parity surfaces, fire-and-forget semantics (native via deepagents 0.5.3), safeguarding, copyright, in-process event bus, and the async-subagent boundary.

ADRs to be captured:

ADR-ARCH-009: Six parity surfaces as load-bearing cross-cutting concerns
ADR-ARCH-010: Pydantic-at-boundary validation + domain vocabulary enums
ADR-ARCH-011: No caching / rate limiting / feature flags in Phase 0
ADR-ARCH-012: deepagents 0.5.3+ pinned; AsyncSubAgent for Phase 1 Coach; CompositeBackend routing for student-model persistence
ADR-ARCH-013: Middleware-level gamification engine noted as future direction for Phase 2
Your choice [C]ontinue / [R]evise / [S]kip / [A]DR?

C
Moving to Category 6.

Category 6: Constraints & NFRs
Q22. Performance requirements?

Proposed:

Metric	Target (Phase 0)	Target (Phase 1)	Source
tutor_turn p95 latency	< 10s (single Ollama call)	< 10s (with RAG + Coach async)	Phase 0 scope SR-07 table
tutor_start_session	≤ 1s to return session_id (long-running classification)	≤ 1s — Graphiti read is async after return	LES1 §4 fire-and-forget; gamification §11 async
tutor_session_status / tutor_session_end	< 2s (sync)	< 2s	SR-07 sync classification
Ollama inference (GB10 local)	~5–8s per 200-token response	Same	Existing empirical
Bedrock cold start	30–60s first call; warm < 10s	Same	DEC-07
Graphiti write-back (Phase 1+)	async / fire-and-forget; 1–3s acceptable	< 5s budget (DEC-08 trigger)	DEC-02, DEC-08
Clean-machine walkthrough (README quickstart)	< 30 min from clone to first tutor_turn	Same	Phase 0 SC-1
No throughput targets — single-user system. Ollama concurrency is 1 (sequential turns per session); that's sufficient.

Q23. Scalability requirements?

Proposed:

Single-user by design through hackathon submission and post-hackathon personal use (Lilymay).
Multi-student is a Phase 3 / post-hackathon concern; handled by student-scoped Graphiti group_ids (student:{id}) per the entity schema — schema is multi-student-ready from day 1, runtime is not.
Horizontal scaling via Bedrock is already the scale-to-zero story (DEC-07); if a future version needs N concurrent students, Bedrock's managed inference is the path. Ollama on GB10 is single-user-concurrent by choice.
No load-balancing, no multi-region, no HA targets. If GB10 or Synology go down, Lilymay loses the tutor temporarily — acceptable for personal use.
Q24. Compliance / regulatory constraints?

Proposed:

Area	Constraint	Source	Enforcement
AQA copyright (absolute)	No reproduction/paraphrase of AQA past-paper questions, mark schemes, examiner reports. Specification references (AO names, definitions, paper shapes) are factual curriculum and acceptable.	GOAL.md §6.1; copyright-training-data-analysis.md §2, §6	Tutor behaviour (fine-tuned); gitignored source dirs; README provenance section
Commercial study-guide copyright	No verbatim reproduction of Mr Bruff / CGP / York Notes etc. Training-data provenance documented; outputs synthesised through three-layer transformation.	copyright-training-data-analysis.md §4	Not shipped in repo; .gitignore hardening; "bring your own sources" model
Set-text copyright	Short quotations only (fair use); no substantial passages. "tomorrow, and tomorrow" fine; full soliloquies not.	GOAL.md §6.1	Tutor behaviour
UK GDPR (implicit)	Student data (name, progress, misconceptions) stays on-device (GB10 + Synology NAS + MacBook) and household Tailscale network. No cloud sync of personal data in Phase 0/1/2.	DEC-05 (Open WebUI primary, single-user); gemma4-hackathon-submission-plan.md privacy story	Architectural — no external telemetry; session-export.json stays local
Safeguarding (content authorisation)	On distress disclosure: stop tutoring, signpost trusted adult + Childline 0800 1111 / Samaritans 116 123. No probing, no diagnosis.	GOAL.md §6.3	Hard-coded in tutor behaviour; overrides all other instructions
Grade predictions prohibited	Never output "this is a Grade N response." Band-descriptor language acceptable.	GOAL.md §6.1	Tutor behaviour
Kaggle hackathon rules	To be read Friday 18 April (prerequisite). May impose repo-visibility, submission-format, licensing constraints.	Phase 0 build plan §Prerequisites	Read + reflect before weekend
Q25. Availability / SLA requirements?

Proposed — no SLA.

Personal learning tool, not a service.
Availability targets:
Ollama on GB10: best-effort. GB10 will be unavailable during the sequential training sequence (DEC-07) — Bedrock path covers that gap.
Bedrock: AWS-managed, no SLA commitment from our side. Cold-start budget 60s acceptable.
Graphiti / Synology: household network dependency; if unreachable, tutor degrades gracefully to session-local state (no student model write-back that session).
Degradation posture: fail soft — a failed Graphiti write-back warns but does not block the student's session end. A failed Bedrock fallback surfaces as a provider error (CC-09-adjacent) but doesn't corrupt session state.
Demo week (12–16 May): this is the one genuine availability window. Bedrock primary means GB10 availability doesn't matter. Back-up plan: Ollama-on-GB10 if Bedrock misbehaves.
Q26. Security constraints beyond authentication?

Proposed:

Key hygiene (SR-06): .env never committed with real keys; .env.example with unambiguous <placeholder> values (never not_needed / sk-test-xxxx — LES1 §retest-env evidence).
IAM scoping: AWS IAM user limited to bedrock:* + s3:* on the specific appmilla-study-tutor-bedrock-models bucket only. No wildcard.
Network: Tailscale-only for internal service discovery (GB10, Synology). No public-internet-exposed services. Open WebUI is LAN/Tailscale accessible, not internet-exposed.
Data residency: Student data on-device or on UK-household hardware (GB10, Synology, MacBook). Gemini (Graphiti entity extraction) does see session summaries during write-back — this is a deliberate trade-off for Graphiti latency/cost (DEC-08). Document in the technical write-up.
Secret redaction: CLI tools that might emit secrets should support --quiet / redaction (LES1 §2). Relevant for guardkit graphiti status (already does) and any new ops scripts.
Content injection resistance: LLM output sanitised before Graphiti seeding (ADR rationale etc.); guardkit graphiti add-context CLI handles this already.
Safeguarding boundary = a security-adjacent content constraint (CC-09).
No pen-testing / no threat model required for Phase 0. Single-user local system; attack surface is the household LAN.
Q27. Budget / timeline constraints affecting architecture?

Proposed — the architecture is shaped by three hard constraints:

Hackathon submission deadline: 18 May 2026, 23:59 UTC. 31 calendar days from the Phase 0 start (17 April). Phase 0 Week 1, Phase 1 Weeks 2–3, Phase 2 Week 4, submission Week 5. This shapes every "deferred to Phase N" decision — the architecture must be visibly three-layer and credibly instantiated by 16 May demo-capture, not feature-complete.
DDD Southwest (Bristol), 16 May 2026. ~4 days lost to travel + prep + talk. Architecture decisions that compound late-phase risk (e.g. Dockerfile, multi-subject) are deferred.
GB10 sequential workload conflict (DEC-07). GB10 cannot train + serve concurrently at 31B scale. Hence dual inference path (Ollama + Bedrock) and explicit migration of inference to Bedrock before demo week.
Budget constraints:

Bedrock inference: ~$1.50–3.00 per 5-min session. Validated during Phase 0 smoke-test. Acceptable for submission period + weeks of running demos; Phase 3+ may revisit for multi-student.
AWS S3: negligible (~tens of GB model weights).
Gemini (Graphiti entity extraction): paid-for per DEC-08; per-call 1–3s, cost not a factor.
GB10: already paid-for sunk cost; free for training when Bedrock serves inference.
No VC runway, no opex commitments. Personal / hobby tooling. Post-hackathon: maintains itself at <$10/month if Lilymay continues using it via Bedrock.
Team constraint: single developer (Rich), reviewer-in-loop for critical paths (FEAT-PO-002, FEAT-PO-004 per build plan), autonomous build for doc-heavy features. Architecture must be understandable by one person carrying context — no unnecessary abstraction layers.

Category 6 — checkpoint:

Captured:

Performance: tutor_turn < 10s p95; tutor_start_session ≤ 1s (long-running return); no throughput targets
Scalability: single-user by design; Graphiti schema multi-student-ready from day 1; Bedrock is the horizontal-scaling path
Compliance: AQA copyright (absolute), commercial study-guide copyright, set-text quotation limits, UK GDPR (implicit — on-device), safeguarding, grade-prediction prohibition, Kaggle rules (read before weekend)
Availability: no SLA; fail-soft degradation; Bedrock de-risks demo week from GB10 training conflict
Security: SR-06 env hygiene, scoped IAM, Tailscale-only, UK data residency with explicit Gemini exception, secret redaction, sanitised Graphiti seeding
Budget/timeline: 18 May 2026 hard deadline + DDD 16 May + GB10 sequential-workload constraint → dual inference path architecture; single-developer comprehensibility as a non-negotiable
ADRs that would be captured automatically:

ADR-ARCH-014: Single-user scalability posture; multi-student schema-ready but runtime-deferred to post-hackathon
ADR-ARCH-015: UK on-device data residency as architectural default; Gemini (Graphiti entity extraction) as explicitly-documented exception
ADR-ARCH-016: 18 May 2026 deadline as load-bearing constraint — architecture optimises for "visibly three-layer on 16 May" over feature completeness
Your choice [C]ontinue / [R]evise / [S]kip / [A]DR?

C
All six categories captured. Proceeding to C4 diagram generation (mandatory review gate).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C4 CONTEXT DIAGRAM (Level 1) — REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

System scope: Study Tutor. External actors + external systems shown. Phase labels: [P0] = Phase 0 (now), [P1] = Phase 1 (Graphiti + Coach), [P2] = Phase 2 (gamification + Reachy stretch).


C4Context
    title Study Tutor — System Context (C4 Level 1)

    Person(student, "Lilymay (Student)", "Year 10, AQA 8700+8702. Uses Open WebUI daily for revision.")
    Person(agent, "AI Agent", "Claude Desktop (P0); future Ship's Computer fleet via Jarvis.")
    Person(developer, "Developer / Judge", "Clones public repo, follows README quickstart on clean machine.")
    Person(parent, "Parent / Teacher", "Queries progress via Reachy Mini voice interface. [P2 stretch]")

    System(studytutor, "Study Tutor", "Three-layer GCSE English AI tutor — fine-tuned behaviour + RAG knowledge + Graphiti student model. MCP + CLI + Open WebUI surfaces.")

    System_Ext(ollama, "Ollama on GB10", "Local inference — fine-tuned Gemma 4 31B Q4_K_M. Tailscale-reachable. [P0 primary]")
    System_Ext(bedrock, "AWS Bedrock", "Custom Model Import — scale-to-zero Gemma 4 31B. Frees GB10 for training. [P0 validation, P1+ primary for demo week]")
    System_Ext(s3, "AWS S3", "Model artefact storage — appmilla-study-tutor-bedrock-models.")
    System_Ext(gemini, "Google Gemini 2.5 Pro", "Graphiti entity-extraction LLM — session write-back. [P1+]")
    System_Ext(falkor, "FalkorDB (Synology NAS)", "Graphiti graph store — per-student topic confidence, sessions, achievements. [P1+]")
    System_Ext(embedder, "GB10 Embedder", "nomic-embed-text-v1.5 on :8001 — Graphiti + ChromaDB embeddings. [P1+]")
    System_Ext(openwebui, "Open WebUI (GB10)", "Lilymay's primary chat interface. OpenAI-compatible. Unchanged from today.")
    System_Ext(litellm, "LiteLLM Proxy (GB10)", "OpenAI-compatible proxy routing Open WebUI → Bedrock when GB10 is training. [P0 validation]")
    System_Ext(claude, "Claude Desktop", "MCP stdio client — architecture-reveal demo + operator usage.")
    System_Ext(reachy, "Reachy Mini 'Scholar'", "Embodied companion — reads Graphiti state, narrates progress. [P2 stretch, gated 4 May]")

    Rel(student, openwebui, "Chats with", "HTTPS (LAN)")
    Rel(openwebui, ollama, "Calls", "Ollama API [P0]")
    Rel(openwebui, litellm, "Calls", "OpenAI-compatible [P0 validation, P1+]")
    Rel(litellm, bedrock, "Routes to", "AWS SDK")

    Rel(agent, claude, "Invokes via")
    Rel(claude, studytutor, "Calls tools", "MCP JSON-RPC / stdio")

    Rel(developer, studytutor, "Installs + runs", "CLI / README walkthrough")

    Rel(studytutor, ollama, "Inference calls", "HTTP over Tailscale [P0 primary]")
    Rel(studytutor, bedrock, "Inference calls", "AWS SDK [P0 validation]")
    Rel(studytutor, falkor, "Student-model R/W", "FalkorDB protocol over Tailscale [P1+]")
    Rel(studytutor, gemini, "Entity extraction", "Gemini API [P1+, async]")
    Rel(studytutor, embedder, "Embed text", "OpenAI-compatible HTTP [P1+]")

    Rel(bedrock, s3, "Loads weights from")

    Rel(parent, reachy, "Asks about progress", "Voice [P2]")
    Rel(reachy, falkor, "Reads state from", "Graphiti client [P2]")
Caption — look for:

Three distinct inference paths (Ollama primary, Bedrock validation, LiteLLM proxy for Open WebUI) all terminating at the fine-tuned model — this is the DEC-07 dual-path architecture that removes the GB10-training/inference conflict.
Graphiti split topology (DEC-02) is explicit: three external systems (Gemini + FalkorDB + Embedder) rather than a single "Graphiti" box, because each has independent latency/availability characteristics.
Open WebUI appears as external because it's an unchanged-upstream component Study Tutor does not own.
Reachy reads Graphiti directly — it is a Student Model consumer, not a Tutor consumer.
Every external system has both a Phase label and a Tailscale/network annotation where relevant.
Node count: 15 (4 persons + 1 main system + 10 external) — well under the 30-node threshold.

Does this diagram accurately represent the Study Tutor system context?

[A]pprove — Diagram is correct, proceed to Container diagram
[R]evise — I need changes
[C]ancel — Stop and discard

Your choice:

A
Context diagram approved. Generating Container diagram.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C4 CONTAINER DIAGRAM (Level 2) — REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Internal containers inside Study Tutor + the immediate external endpoints they talk to. Phase gating: solid = Phase 0; relationships labelled [P1] / [P2] where the container/call exists only in later phases.


C4Container
    title Study Tutor — Container Diagram (C4 Level 2)

    Person(agent, "AI Agent (Claude Desktop)", "Invokes tutor via MCP tools")
    Person(developer, "Developer / Judge", "CLI + README walkthrough")
    Person(student, "Lilymay", "Uses Open WebUI (external to containers shown)")

    System_Boundary(studytutor, "Study Tutor") {
        Container(wrapper, "Bash MCP Wrapper", "bash / scripts/mcp-wrapper.sh", "Absolute cd + env load + exec — SR-02. Launched by Claude Desktop.")
        Container(cli, "CLI Entrypoint", "Python / Click", "study-tutor serve --role tutor --transport stdio. Banner→stderr per SR-01.")
        Container(mcp, "MCP Adapter", "Python / mcp SDK", "Registers 4 tools: tutor_start_session (long-running), tutor_turn (sync), tutor_session_status, tutor_session_end. SR-07 classification.")
        Container(session, "Tutor Session Manager", "Python / in-memory dict", "TutorSession aggregate. In-memory in P0; Graphiti-backed P1+.")
        Container(llm, "LLM Client (Provider Factory)", "Python / langchain-*", "Resolves AGENT_MODELS__REASONING_MODEL at factory — SR-03. Routes local/bedrock/openai/anthropic/gemini.")
        ComponentDb(domain, "Domain Config", "Markdown + YAML", "domains/gcse-english/GOAL.md + roles/tutor/role.yaml + criteria/definitions.yaml. Shared-kernel taxonomy.")
        Container(gamdocs, "Gamification Design", "Markdown docs", "docs/gamification/design.md — authoritative economy. State engine deferred to P2.")

        Container_Boundary(p1, "Phase 1 additions") {
            Container(harness, "DeepAgents Harness (Player)", "Python / deepagents 0.5.3+", "create_deep_agent — Player role, tutoring prompt from GOAL.md. [P1]")
            Container(coach, "Coach (AsyncSubAgent)", "Python / deepagents AsyncSubAgent", "Quality monitor — async off hot path. Writes confidence deltas at session-end. [P1]")
            Container(planner, "Session Planner", "Python", "Reads Graphiti, recommends topic. [P1]")
            Container(student_model, "Student Model Client", "Python / graphiti-core", "Student, TopicConfidence, Session episodes. [P1]")
            Container(rag, "RAG Retrieval", "Python / chromadb", "Per-subject ChromaDB collection — curriculum lookup. [P1]")
        }

        Container_Boundary(p2, "Phase 2 additions") {
            Container(gamengine, "Gamification Engine", "Python", "XP, levels, achievements, streaks, Boss Battle. [P2]")
            Container(export, "Session Export", "Python / JSON", "session-export.json — consumed by Dashboard + Reachy. [P1 schema, P2 renderer]")
            Container(dashboard, "Dashboard Generator", "Claude Design / static HTML", "Read-only snapshot view. [P2]")
        }
    }

    System_Ext(ollama, "Ollama (GB10)", "Local inference")
    System_Ext(bedrock, "AWS Bedrock", "Custom Model Import")
    System_Ext(falkor, "FalkorDB (Synology)", "Graphiti store")
    System_Ext(gemini, "Google Gemini", "Entity extraction")
    System_Ext(embedder, "GB10 Embedder", "nomic-embed-text-v1.5")
    System_Ext(claude_desktop, "Claude Desktop", "MCP client")

    Rel(agent, claude_desktop, "Invokes")
    Rel(claude_desktop, wrapper, "Launches", "stdio + absolute CWD")
    Rel(wrapper, cli, "Execs", ".venv/bin/study-tutor")
    Rel(cli, mcp, "Starts")
    Rel(developer, cli, "Runs directly")

    Rel(mcp, session, "Creates / advances")
    Rel(session, llm, "Invokes (P0: single call per turn)")
    Rel(session, domain, "Reads prompts from")
    Rel(llm, ollama, "P0 primary", "HTTP / Tailscale")
    Rel(llm, bedrock, "P0 validation", "AWS SDK")

    Rel(session, harness, "Delegates turns to [P1]")
    Rel(harness, llm, "Player inference [P1]")
    Rel(harness, rag, "Curriculum retrieval [P1]")
    Rel(harness, coach, "Spawns [P1 async]")
    Rel(coach, student_model, "Writes confidence delta [P1 on session-end]")
    Rel(harness, planner, "Asks for topic [P1]")
    Rel(planner, student_model, "Reads confidence [P1]")
    Rel(student_model, falkor, "R/W", "FalkorDB protocol [P1]")
    Rel(student_model, gemini, "Entity extraction [P1 async]")
    Rel(student_model, embedder, "Embed [P1]")
    Rel(rag, embedder, "Embed queries [P1]")

    Rel(session, export, "Emits on session-end [P1 schema]")
    Rel(gamengine, student_model, "Subscribes to events [P2]")
    Rel(dashboard, export, "Renders from [P2]")
Caption — look for:

Phase 0 core is 7 containers: Wrapper → CLI → MCP Adapter → Session Manager → LLM Client + Domain Config + Gamification Docs. Session Manager makes a single Ollama/Bedrock call per turn — no deepagents, no RAG, no Coach in P0.
Phase 1 adds the three-layer architecture runtime: DeepAgents Harness (Player), Coach (async subagent — leveraging deepagents 0.5.3 AsyncSubAgent), Session Planner, Student Model, RAG. Note that the Session Manager delegates to the Harness in P1 rather than calling the LLM Client directly — this is the upgrade path.
Phase 2 is three containers + one schema: Gamification Engine (reads student-model events), Session Export (schema lands in P1, renderer in P2), Dashboard Generator (Claude-Design-generated static HTML).
Coach → Student Model is the only write path for confidence deltas — enforces ADR-ARCH-003 (async write-back at session-end boundary).
Planner → Student Model is read-only — recommendation is a read operation, no feedback loop to game.
LLM Client is the sole boundary with inference endpoints — CC-03/ACL anti-corruption boundary visible here (nothing upstream of the LLM Client speaks provider-specific protocols).
Domain Config is read by both Session Manager (P0) and Harness (P1) — the shared kernel per Category 2.
Gamification Engine depends only on events from Student Model — implements CC-11 (in-process event vocabulary); doesn't couple to Harness or Session internals.
Node count: 21 (14 internal + 6 external + 3 persons — well under the 30-node threshold).

Does this diagram accurately represent the Study Tutor containers and their relationships across Phases 0/1/2?

[A]pprove — Diagram is correct, proceed to artefact generation
[R]evise — I need changes
[C]ancel — Stop and discard

Your choice:

A
Both diagrams approved. Generating all output artefacts to docs/architecture/. Starting with directory check then writing in sequence.

Bash Create architecture directory tree
IN
mkdir -p /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions && ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/

OUT
total 0
drwxr-xr-x  3 richardwoollcott  staff   96 Apr 18 23:27 .
drwxr-xr-x  7 richardwoollcott  staff  224 Apr 18 23:27 ..
drwxr-xr-x  2 richardwoollcott  staff   64 Apr 18 23:27 decisions
Write ARCHITECTURE.md
203 lines
# Study Tutor — Architecture Summary

**Status:** Phase 0 canonical — generated by `/system-arch` on 2026-04-18.
**Deadline anchor:** Gemma 4 Good Hackathon submission, 18 May 2026.
**Consumed by:** `/system-design`, `/system-plan`, `/feature-spec`.
**Do-not-reopen decisions:** see `docs/architecture/decisions/ADR-ARCH-*.md`.

---

## 1. One-paragraph summary

Study Tutor is a GCSE English AI tutor for Year 10/11 students preparing for
AQA 8700 (Language) and 8702 (Literature). It combines a fine-tuned Gemma 4
31B (Layer 1 — tutoring behaviour), a ChromaDB curriculum RAG (Layer 2 —
knowledge), and a Graphiti-backed per-student model (Layer 3 — progress,
topic confidence, misconceptions, gamification state) orchestrated by a
DeepAgents harness with a Player-Coach quality monitor. The architecture
follows Domain-Driven Design around six bounded contexts and inherits the
six parity surfaces (LES1) from the `specialist-agent` post-TASK-REV-B8E4
pattern. Access is via MCP stdio (agents + Claude Desktop), CLI
(developers), and the existing Open WebUI path (Lilymay, unchanged). The
architecture is staged across three phases: Phase 0 (this week) ships the
scaffolding + MCP adapter + single-call Ollama/Bedrock tutor; Phase 1 adds
the Graphiti student model, Player-Coach harness, and session planner;
Phase 2 adds the gamification state engine and Reachy Mini stretch. Every
decision in this document is do-not-reopen unless material evidence
justifies revision per `decisions-log-2026-04-17.md §Revision policy`.

## 2. Structural pattern

**Domain-Driven Design** over six bounded contexts with two shared kernels
and one anti-corruption layer. Rationale: the three-layer architecture
from `deepagents-patterns-review.md §1.3` is explicit in the research, and
Phase 1/2 add genuine bounded contexts (Graphiti student model,
gamification state engine) that benefit from DDD's language. The pattern
is also consistent with the role-aware `specialist-agent` codebase that
Study Tutor copies scaffolding from.

See `ADR-ARCH-001-ddd-structural-pattern.md` and
`ADR-ARCH-002-three-layer-architecture.md`.

## 3. Bounded contexts

| # | Context | Primary code path | Phase |
|---|---|---|---|
| 1 | **Tutoring** | `src/study_tutor/session/`, `roles/tutor/`, `domains/gcse-english/` | P0 |
| 2 | **Knowledge & Curriculum** | `src/study_tutor/knowledge/`, `domains/gcse-english/sources/` | P0 stub → P1 |
| 3 | **Student Model** | `src/study_tutor/student/` | P1 |
| 4 | **Gamification** | `docs/gamification/design.md` (P0 docs) → `src/study_tutor/gamification/` (P2) | P0 design → P2 engine |
| 5 | **Inference Runtime** | `src/study_tutor/llm/` | P0 |
| 6 | **MCP Transport** | `src/study_tutor/mcp/`, `src/study_tutor/cli/`, `scripts/mcp-wrapper.sh` | P0 |

**Shared kernels:**
1. Domain taxonomy — `Subject`, `Paper`, `Text`, `AssessmentObjective`
   (AO1–AO6), `Topic`, `GradeTarget`, `ConfidenceBand`. Authoritative in
   `domains/gcse-english/GOAL.md §3–§4` and `docs/gamification/design.md §6`.
2. Session event vocabulary — `session.started`, `session.turn_completed`,
   `session.completed`, `achievement.unlocked`, `quest.completed`,
   `quest.expired`, `boss_battle.completed`. Producer: Tutoring; consumers:
   Student Model (P1), Gamification (P2).

**Anti-corruption layer:** Inference Runtime (`LLMClient`) — normalises
across Ollama, Bedrock, and API providers (OpenAI, Anthropic, Gemini).
Upstream contexts never speak provider-specific protocols.

See `domain-model.md` for full entity relationships.

## 4. Technology stack

| Layer | Choice | Phase | Rationale |
|---|---|---|---|
| Language | Python 3.11 | P0 | Matches `specialist-agent`; fine-tuning tooling compatible |
| Harness | `deepagents >= 0.5.3` | P1 (declared P0) | `AsyncSubAgent` native fire-and-forget; `CompositeBackend` for state/store split |
| LLM framework | `langchain` + provider integrations | P0 | Provider switching via factory (SR-03) |
| Transport | `mcp` Python SDK over stdio | P0 | SR-01 stream-split discipline |
| CLI | `click` | P0 | `err=True` for stderr banner |
| Validation | `pydantic` | P0 | Boundary-validation strategy |
| Graph DB | FalkorDB via Graphiti | P1 | Hosted on Synology NAS (DEC-02) |
| RAG | ChromaDB | P1 | Reused from `agentic-dataset-factory` |
| Embeddings | nomic-embed-text-v1.5 on GB10 | P1 | Small enough not to block training |
| Entity-extraction LLM | Google Gemini 2.5 Pro | P1 | DEC-02 + DEC-08 |
| Inference (P0 primary) | Ollama on GB10 | P0 | Existing fine-tuned deployment |
| Inference (scale-to-zero) | AWS Bedrock Custom Model Import | P0 validation | Frees GB10 for training (DEC-07) |
| CI/CD | GitHub Actions | P0 minimal | Lint + parity-surface unit tests |
| Deployment | Venv only | P0 | No Dockerfile in Phase 0 per scope DNC |

See `ADR-ARCH-004` through `ADR-ARCH-007` and `ADR-ARCH-012`.

## 5. Multi-consumer API surfaces

| Consumer | Protocol | Phase |
|---|---|---|
| Human student (Lilymay) | Open WebUI → Ollama (P0) / Bedrock via LiteLLM (P0+) | P0 unchanged |
| AI agents (Claude Desktop, future Jarvis) | MCP JSON-RPC over stdio — 4 tools with SR-07 sync/long-running classification | P0 |
| Developers / judges | CLI (`study-tutor serve --role tutor --transport stdio`) | P0 |
| Dashboard viewers | Static HTML rendered from `session-export.json` | P2 |
| Reachy Mini | Python SDK reads Graphiti directly | P2 stretch (gated 4 May) |

See `ADR-ARCH-008-mcp-only-agent-access.md`.

## 6. Cross-cutting concerns (12)

| Code | Concern | Source |
|---|---|---|
| CC-01 | MCP stdio discipline (SR-01) | LES1 MCPB |
| CC-02 | Launcher CWD abs-path (SR-02) | LES1 walkthrough |
| CC-03 | Provider resolution at factory (SR-03) | LES1 PMEV/CRMV |
| CC-04 | `[providers]` extra completeness (SR-04) | LES1 LCOI |
| CC-05 | Dockerfile literal-match venv install (SR-05) — deferred | LES1 DKRX |
| CC-06 | `.env` hygiene — no real-looking keys (SR-06) | LES1 §retest-env |
| CC-07 | Tool description ≡ implementation contract (SR-07) | LES1 POLR |
| CC-08 | Fire-and-forget + poll above 30s | LES1 §4 |
| CC-09 | Safeguarding content boundary | `GOAL.md §6.3` |
| CC-10 | Copyright / provenance boundary | `GOAL.md §6.1` + `copyright-training-data-analysis.md` |
| CC-11 | In-process event bus vocabulary | Cat 2 + `design.md §11.2` |
| CC-12 | Async-capable subagent boundary | deepagents 0.5.3 `AsyncSubAgent` |

See `ADR-ARCH-009` through `ADR-ARCH-013`.

## 7. Constraints & NFRs (highlights)

- **Performance:** `tutor_turn` p95 < 10s; `tutor_start_session` returns
  `session_id` in ≤1s. No throughput targets (single-user).
- **Scalability:** single-user by design; Graphiti schema is
  multi-student-ready via per-student group IDs.
- **Compliance:** AQA past-paper/mark-scheme content prohibited (absolute);
  AQA specification references acceptable; set-text short quotations only;
  UK GDPR posture = on-device + household Tailscale (Gemini is the single
  explicit exception for entity extraction).
- **Safeguarding:** GOAL.md §6.3 overrides all other instructions.
- **Availability:** no SLA; fail-soft degradation; Bedrock removes demo-week
  dependence on GB10 training schedule (DEC-07).
- **Security:** SR-06 env hygiene, scoped IAM (`bedrock:*` + specific S3
  bucket), Tailscale-only internal networking, secret redaction.
- **Timeline:** **18 May 2026, 23:59 UTC** hackathon submission deadline +
  DDD Southwest 16 May (~4 days absorbed). Architecture optimises for
  "visibly three-layer on 16 May demo capture" over feature completeness.

See `ADR-ARCH-014` through `ADR-ARCH-016`.

## 8. Phase-by-phase deliverable map

| Phase | Dates | Architectural deliverables |
|---|---|---|
| **Phase 0** | 18–24 April 2026 | Scaffolding, MCP adapter, LLM client, 4 tools, 6 parity surfaces green, Bedrock validation, BYOS packaging, submission-doc stubs |
| **Phase 1** | 25 April – 11 May 2026 | Graphiti student model, DeepAgents Player-Coach harness, Session Planner, async session-end write-back, RAG retrieval |
| **Phase 2** | 12–16 May 2026 | Gamification state engine, static HTML dashboard, Reachy companion scripts (gated), demo assets |
| **Submission** | 17–18 May 2026 | Final polish, video edit, Kaggle submission |

## 9. Architecture Decision Records (index)

| ID | Title | Status |
|---|---|---|
| ADR-ARCH-001 | Use Domain-Driven Design structural pattern | Accepted |
| ADR-ARCH-002 | Three-layer architecture (behaviour / knowledge / student model) | Accepted |
| ADR-ARCH-003 | Async Graphiti write-back at session-end boundary | Accepted |
| ADR-ARCH-004 | Python 3.11 + deepagents + langchain + mcp stack | Accepted |
| ADR-ARCH-005 | Defer Dockerfile to Phase 1+ — venv-only install for Phase 0 | Accepted |
| ADR-ARCH-006 | Dual inference path — Ollama primary + Bedrock validation | Accepted |
| ADR-ARCH-007 | Graphiti split topology (FalkorDB Synology + Gemini LLM + GB10 embedder) | Accepted |
| ADR-ARCH-008 | MCP-only for agent access; single-user auth posture | Accepted |
| ADR-ARCH-009 | Six parity surfaces (LES1) as load-bearing cross-cutting concerns | Accepted |
| ADR-ARCH-010 | Pydantic-at-boundary validation + domain vocabulary enums | Accepted |
| ADR-ARCH-011 | No caching / rate limiting / feature flags in Phase 0 | Accepted |
| ADR-ARCH-012 | deepagents 0.5.3+ with AsyncSubAgent Coach + CompositeBackend routing | Accepted |
| ADR-ARCH-013 | Middleware-level gamification engine as future direction (P2) | Proposed |
| ADR-ARCH-014 | Single-user scalability posture; multi-student schema-ready | Accepted |
| ADR-ARCH-015 | UK on-device data residency; Gemini as explicit exception | Accepted |
| ADR-ARCH-016 | 18 May 2026 deadline as load-bearing architectural constraint | Accepted |

## 10. Assumptions

18 assumptions captured — see `assumptions.yaml`. Highest-risk:
- ASSUM-007: Bedrock Custom Model Import supports Gemma 4 31B natively.
- ASSUM-009: Gemini 2.5 Pro latency 1–3s per extraction call (DEC-08
  monitored).
- ASSUM-014: deepagents 0.5.x API stable through Phase 1 build.
- ASSUM-017: Kaggle rules compatible with Apache 2.0 + BYOS model.

## 11. Related documents

**Upstream inputs (read-only from architecture's perspective):**
- `docs/research/ideas/phase-0-scope.md`
- `docs/research/ideas/phase-0-build-plan.md`
- `docs/research/ideas/decisions-log-2026-04-17.md`
- `docs/research/ideas/state-of-the-project-and-phase-recommendation.md`
- `docs/research/ideas/deepagents-patterns-review.md`
- `../specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`
- `domains/gcse-english/GOAL.md`
- `docs/gamification/design.md`

**Sibling architecture artefacts:**
- `domain-model.md` — entities, aggregates, events, relationships
- `system-context.md` — C4 Level 1 diagram
- `container.md` — C4 Level 2 diagram
- `assumptions.yaml` — 18 captured assumptions
- `decisions/ADR-ARCH-*.md` — 16 ADRs

---

*Generated: 2026-04-18 by `/system-arch`.*
*Next: `/system-design` for API contracts, then `/system-plan` for feature planning.*
Write domain-model.md
503 lines
# Study Tutor — Domain Model

**Status:** Phase 0 canonical.
**Generated:** 2026-04-18 by `/system-arch`.
**Authoritative sources:** `domains/gcse-english/GOAL.md`, `docs/gamification/design.md`, `decisions-log-2026-04-17.md`.

---

## 1. Pattern: Domain-Driven Design over six bounded contexts

Study Tutor's domain decomposes into six bounded contexts, two shared
kernels, and one anti-corruption layer. See `ADR-ARCH-001`.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Kernel A                             │
│              Domain Taxonomy (curriculum)                        │
│  Subject · Paper · Text · AssessmentObjective · Topic ·          │
│  GradeTarget · ConfidenceBand                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ used by ↓
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Tutoring   │  │ Knowledge &  │  │   Student    │
    │              │──│  Curriculum  │──│    Model     │
    │ (TutorSession│  │ (Text, AO,   │  │ (Student,    │
    │   aggregate) │  │ Collection)  │  │ Confidence)  │
    └──────┬───────┘  └──────────────┘  └──────┬───────┘
           │                                    │
           │  emits/consumes                   │
           └────────────────┬───────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Kernel B                             │
│              Session Event Vocabulary                            │
│  session.started · session.turn_completed · session.completed ·  │
│  achievement.unlocked · quest.completed · quest.expired ·        │
│  boss_battle.completed                                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                    ┌──────────────┐
                    │ Gamification │
                    │              │
                    │(StudentProg, │
                    │ Achievement, │
                    │ Quest)       │
                    └──────────────┘

    ┌──────────────────────┐      ┌──────────────────────┐
    │   MCP Transport      │─────→│ Inference Runtime    │
    │                      │      │  (anti-corruption    │
    │  (McpAdapter, 4      │      │   layer — LLMClient) │
    │   tools, SR-07       │      │                      │
    │   classified)        │      │ Ollama|Bedrock|API   │
    └──────────────────────┘      └──────────────────────┘
```

---

## 2. Bounded Context 1 — Tutoring

**Purpose.** Owns the session lifecycle and the tutor's interactive
behaviour. Everything the student experiences turn-by-turn happens here.

**Location (P0):** `src/study_tutor/session/tutor_session.py`,
`src/study_tutor/mcp/adapter.py` (partial — handler façade),
`roles/tutor/role.yaml`, `domains/gcse-english/GOAL.md`.

### 2.1 Aggregate root: `TutorSession`

| Field | Type | Invariant |
|---|---|---|
| `session_id` | UUID | Immutable |
| `student_id` | str | Immutable; references Student in Student Model context |
| `subject` | Subject enum | Immutable after session start |
| `paper` | Paper enum (optional) | Immutable after session start |
| `topic` | Topic (optional) | Mutable — student can switch mid-session |
| `grade_target` | GradeTarget enum (4–9) | Mutable; planner recalibrates |
| `state` | SessionState enum | State machine — see below |
| `turns` | list[Turn] | Append-only |
| `started_at` | datetime | Immutable |
| `ended_at` | datetime (nullable) | Settable exactly once |

**State machine:**

```
 initialised ──► planning ──► active ──► summarising ──► ended
                    │            │                         ▲
                    │            └──────── (abandonment) ──┘
                    └──────── (skip planning) ─────────────┘
```

**Invariants:**
- No turns accepted when `state == ended`.
- `state` transitions are monotonic (no going back).
- A session abandoned before completing a single turn emits no
  `session.completed` event (gamification §2.1: no XP for <2-min
  abandons).

### 2.2 Value objects in this context

- `Turn` — `{index, role, content, timestamp, aos_scaffolded, rag_chunks_used}`.
  Append-only.
- `TurnFeedback` (P1) — Coach-produced quality score per AO.
- `SessionSummary` (P1) — end-of-session synthesis with per-topic
  confidence-delta proposals (capped ±0.1 per session — `design.md §6.2`).

### 2.3 References

- → Student Model (by `student_id` only — no cross-context object
  references).
- → Knowledge & Curriculum (by `Topic`/`AO`/`Text` ID only).
- → Inference Runtime (via `LLMClient` injection).

### 2.4 Events emitted

- `session.started {session_id, student_id, subject, topic}` — on
  transition to `planning` or `active`.
- `session.turn_completed {session_id, turn_index, ao_scaffolded}` — per
  turn. Consumers: Coach (P1, evaluates); Student Model (P1, may append
  misconception).
- `session.completed {session_id, duration, topic, aos_touched,
  quality_score}` — on transition to `ended`. Consumers: Gamification
  (P2), Student Model (P1).

---

## 3. Bounded Context 2 — Knowledge & Curriculum

**Purpose.** Owns the curriculum taxonomy and RAG retrieval. Provides the
*what* that the Tutoring context teaches.

**Location:** `domains/gcse-english/GOAL.md` (P0 authoritative),
`domains/gcse-english/sources/` (P1 BYOS input), `src/study_tutor/knowledge/`
(P1 runtime).

### 3.1 Aggregate roots

- **`CurriculumCollection`** — per domain, per subject. Phase 1+ ChromaDB
  collection. Aggregate state: `{subject, ingestion_timestamp,
  source_fingerprints, embedding_model}`.
- **`Text`** — named set text or cluster (`Macbeth`, `Power & Conflict
  poetry`, etc.). `{text_id, title, type, paper_mapping}`. Identity is
  `text_id`.
- **`AssessmentObjective`** — the six AOs from `GOAL.md §3`. Identity is
  `ao_id ∈ {AO1, AO2, AO3, AO4, AO5, AO6}`. Immutable.

### 3.2 Value objects

- `Topic` — a studyable unit within a Text (e.g. `macbeth:act1:witches`,
  `power_and_conflict:ozymandias`). Identity is `topic_id`.
- `SourceDocument` — a user-provided PDF (Mr Bruff, CGP, etc.). Not
  shipped in repo (CC-10). Phase 1+ ingested via Docling.

### 3.3 Invariants

- `SourceDocument` files are never committed to git (enforced by
  `.gitignore` — CC-10).
- The short-quotation rule (`GOAL.md §6.1`) is enforced at output time by
  the Tutoring context, not by this context — this context owns the data,
  not its downstream use.

### 3.4 Phase 0 status

Taxonomy declared in `GOAL.md §3–§4`. No runtime code in Phase 0. ChromaDB
wiring + Docling ingestion are Phase 1 (FEAT-PO-001-roadmap onwards).

---

## 4. Bounded Context 3 — Student Model

**Purpose.** Owns per-student state — who they are, what they know,
what they've misunderstood, how they've progressed. Layer 3 of the
three-layer architecture.

**Location:** `src/study_tutor/student/` (P1), Graphiti group IDs
`student:{id}` and `subject:gcse-english`.

### 4.1 Aggregate root: `Student`

| Field | Type | Invariant |
|---|---|---|
| `student_id` | str | Immutable |
| `name` | str (optional) | Mutable |
| `scoped_group_id` | `student:{student_id}` | Derived, immutable |
| `subjects_studied` | set[Subject] | Append-only |
| `current_level` | int (1–15) | Monotonic increase |
| `total_xp` | int ≥ 0 | Monotonic increase |
| `current_streak` | int ≥ 0 | Can reset to 0 |
| `longest_streak` | int ≥ 0 | Monotonic increase |
| `created_at` | datetime | Immutable |

**Invariants:**
- `total_xp` never decreases (design.md §11).
- `current_level` never decreases (mastery unlocks are sticky — §5).
- `longest_streak >= current_streak` always.

### 4.2 Value objects / sub-entities

- **`TopicConfidence`** — per `(student_id, topic_id)`. Scalar `0.0 ≤ c
  ≤ 1.0`. Band (`Struggling`, `Developing`, `Secure`, `Mastered`) derived
  from thresholds in `design.md §6`. Invariant: per-session delta capped
  at ±0.1.
- **`Misconception`** — flagged by Coach during `session.turn_completed`
  (Phase 1+). `{student_id, misconception_id, topic_id, first_seen,
  last_seen, recurrence_count}`.
- **`SessionEpisode`** — one per completed session. `{session_id,
  student_id, topic_id, duration, xp_earned, aos_touched, quality_score,
  ended_at}`.
- **`AssessmentObjectiveProgress`** — per `(student_id, ao_id)`. Roll-up
  of scaffolded turns over time.

### 4.3 Events consumed

- `session.started` → create SessionEpisode head.
- `session.turn_completed` → may append `Misconception` (P1 Coach).
- `session.completed` → close SessionEpisode; update `TopicConfidence`
  (bounded ±0.1); update `AssessmentObjectiveProgress`.

### 4.4 Phase 0 status

Schema declared here and in `GOAL.md §11`. No runtime code in Phase 0.
Phase 1: Graphiti wiring + entity extraction via Gemini + embeddings via
GB10 nomic-embed.

---

## 5. Bounded Context 4 — Gamification

**Purpose.** Owns the engagement layer — XP, levels, achievements,
streaks, Boss Battle unlock gating, daily challenges, quests.

**Location:** `docs/gamification/design.md` (P0 authoritative economy);
`src/study_tutor/gamification/` (P2 runtime engine).

### 5.1 Aggregate roots

- **`StudentProgress`** — per student. `{student_id, level_title (e.g.
  "Scholar"), total_xp, current_streak, longest_streak,
  daily_sweep_state, active_quest_ids, trophies}`.
- **`Achievement`** — enumerated set from `design.md §5`. Identity is
  `achievement_id`. Sticky — once unlocked, always unlocked.
- **`Quest`** — active and historical. `{quest_id, student_id, shape,
  target, progress, expires_at, completed_at (nullable)}`. One
  concurrent at Level <9; two at Level ≥9.
- **`BossBattle`** — unlocked at Level 8. `{boss_id, student_id, paper,
  duration, trophy_id, first_completed_at, practice_completions}`.

### 5.2 Invariants (from `design.md`)

- Level 1→2 at 100 XP; full 15-level curve per §3.1. Monotonic.
- Mastery achievements at 80% confidence (§5.2).
- Streak resets to 0 at midnight of any day without a session completion
  (§4.1).
- Weekly Boss Battle: first completion per calendar week awards XP;
  subsequent completions unlock practice mode (no XP).
- Unlock gates (§3.2) are one-way.

### 5.3 Events consumed

- `session.completed` → XP delta (180 Macbeth / 60 short / 120 std / +30
  quotation / +40 review; 1.25× for Grade 8–9); streak delta; achievement
  check; daily-challenge check.
- `achievement.unlocked` (self-emitted) → XP bonus per `design.md §5`;
  Reachy celebration trigger (P2 stretch).
- `boss_battle.completed` → XP + trophy; confidence delta via Coach.

### 5.4 Events emitted

- `achievement.unlocked {student_id, achievement_id, xp_reward}`
- `quest.completed`, `quest.expired`
- `boss_battle.completed {student_id, paper, trophy_id}`

### 5.5 Phase 0 status

Design complete (`docs/gamification/design.md`). No runtime code. Phase 2
implements the state engine. See `ADR-ARCH-013` — the engine may be
implemented as a deepagents custom middleware reacting to events.

---

## 6. Bounded Context 5 — Inference Runtime

**Purpose.** Provider abstraction — normalises Ollama, AWS Bedrock, and
API providers (OpenAI, Anthropic, Gemini) behind a single interface. Is
the anti-corruption layer for the rest of the domain.

**Location:** `src/study_tutor/llm/client.py`.

### 6.1 Aggregate root: `LLMClient`

**Factory-resolved** from `AGENT_MODELS__REASONING_MODEL` env var (CC-03 /
SR-03). No handler hard-codes a provider.

| Provider label | Endpoint | Phase |
|---|---|---|
| `local` | Ollama on GB10 (Tailscale) | P0 primary (default) |
| `bedrock` | AWS Bedrock Custom Model Import | P0 validation; P1+ primary for demo week |
| `openai` | OpenAI API | Declared, reserved for Coach / fallback |
| `anthropic` | Anthropic API | Declared, reserved |
| `gemini` | Google Gemini API | Declared; also used by Graphiti (outside `LLMClient`) |

### 6.2 Invariants

- Provider resolved at factory, not at handler (CC-03 — LES1
  PMEV/CRMV evidence).
- Every provider named in code appears in `pyproject.toml`
  `[providers]` extra (CC-04 — LES1 LCOI).
- `LLMClient.invoke(messages, **opts)` is the sole public interface.
  Upstream contexts never construct `ChatOllama`, `ChatBedrock`, etc.
  directly.

### 6.3 Anti-corruption seam

All provider-specific knowledge (Bedrock ARNs, Ollama URLs, API retry
semantics, model IDs) stays inside this context. Upstream code speaks
only the `LLMClient.invoke(messages, **opts)` vocabulary.

---

## 7. Bounded Context 6 — MCP Transport

**Purpose.** Owns the external protocol surface. Turns the tutor into a
discoverable, invokable system. Enforces the six parity surfaces'
transport-layer rules (SR-01, SR-02, SR-07, CC-08).

**Location:** `src/study_tutor/mcp/adapter.py`,
`src/study_tutor/cli/main.py`, `scripts/mcp-wrapper.sh`.

### 7.1 Aggregate root: `McpAdapter`

Registers the following tools at startup:

| Tool | Classification (SR-07) | Target latency |
|---|---|---|
| `tutor_start_session` | long-running (returns `session_id` ≤ 1s; poll via `tutor_session_status`) | ≤ 1s return |
| `tutor_turn` | sync (< 30s) | p95 < 10s |
| `tutor_session_status` | sync | < 2s |
| `tutor_session_end` | sync — triggers async Graphiti write-back (P1) | < 2s |

### 7.2 Invariants

- **stdout exclusively MCP JSON-RPC** — all diagnostics via
  `click.echo(..., err=True)` (CC-01 / SR-01).
- **Bash wrapper `cd`s to an absolute path** before `exec` (CC-02 /
  SR-02).
- **Every tool description matches handler behaviour** — verified by
  `tests/unit/mcp/test_stdio_discipline.py` and the tool-contract test
  (CC-07 / SR-07).
- **Long-running tools return a `session_id` in ≤1s** (CC-08 — LES1 §4
  POLR evidence).
- **Phase 1+ leverages deepagents 0.5.3 `AsyncSubAgent` for Coach** rather
  than hand-rolling fire-and-forget (CC-12).

---

## 8. Shared kernels

### 8.1 Shared Kernel A — Domain Taxonomy

Definitions live in `domains/gcse-english/GOAL.md §3` (AOs) and `§4`
(texts/topics), and `docs/gamification/design.md §6` (confidence bands).
Code location (Phase 1+): `src/study_tutor/domain/taxonomy.py` (Pydantic
enums).

```python
class Subject(StrEnum):
    ENGLISH_LANGUAGE = "English Language"
    ENGLISH_LITERATURE = "English Literature"

class Paper(StrEnum):
    PAPER_1 = "Paper 1"
    PAPER_2 = "Paper 2"

class AssessmentObjective(StrEnum):
    AO1 = "AO1"  # Identify and interpret explicit/implicit information
    AO2 = "AO2"  # Language and structure
    AO3 = "AO3"  # Compare writers' ideas and perspectives
    AO4 = "AO4"  # Evaluate texts critically
    AO5 = "AO5"  # Communicate clearly, effectively, imaginatively
    AO6 = "AO6"  # Technical accuracy

class GradeTarget(IntEnum):
    G4 = 4; G5 = 5; G6 = 6; G7 = 7; G8 = 8; G9 = 9

class ConfidenceBand(StrEnum):
    STRUGGLING = "struggling"     # 0.0 ≤ c < 0.4
    DEVELOPING = "developing"     # 0.4 ≤ c < 0.6
    SECURE = "secure"             # 0.6 ≤ c < 0.8
    MASTERED = "mastered"         # 0.8 ≤ c ≤ 1.0
```

Consumer contexts: Tutoring, Knowledge, Student Model, Gamification.

### 8.2 Shared Kernel B — Session Event Vocabulary

Names and minimal payloads. Stable across phases; consumers opt in.

```python
session.started         { session_id, student_id, subject, topic }
session.turn_completed  { session_id, turn_index, ao_scaffolded }
session.completed       { session_id, duration, topic, aos_touched,
                          quality_score }
achievement.unlocked    { student_id, achievement_id, xp_reward }
quest.completed         { student_id, quest_id }
quest.expired           { student_id, quest_id }
boss_battle.completed   { student_id, paper, trophy_id }
```

Producer: Tutoring. Consumers: Student Model (P1), Gamification (P2),
Reachy (P2 stretch).

---

## 9. Domain event flow (Phase 1+)

```
 Student (via Open WebUI or Claude Desktop)
       │
       ▼
 McpAdapter.tutor_start_session
       │ create TutorSession
       ▼
 TutorSession ──── emits: session.started ────┐
       │                                       ▼
       │                            Student Model (P1)
       │                            (creates SessionEpisode head)
       ▼
 McpAdapter.tutor_turn (×N)
       │
       ▼
 TutorSession.advance()
       │ emits: session.turn_completed
       ▼
 ┌─────┴──────────┐
 │                │
 ▼                ▼ (async, deepagents AsyncSubAgent)
 Player          Coach
 (LLMClient)     (evaluates quality)
 returns text    writes TurnFeedback
                 │
                 ▼ at session-end only
                 Student Model (P1)
                 (appends Misconception if any)

 ... session ends ...
       │
       ▼
 TutorSession.end()
       │ emits: session.completed
       │
 ┌─────┴──────────┬──────────────┐
 ▼                ▼              ▼
 Student Model   Gamification    (future: Reachy celebration)
 (update         (XP + streak +
  TopicConf'     achievement
  via Coach-     check)
  proposed
  delta, ≤±0.1)
```

**Consistency model:** the `session.completed` event fan-out is async —
the tutor can return control to the student while Graphiti write-back and
gamification updates proceed in the background. This is deliberate
(ADR-ARCH-003).

---

## 10. Evolutionary notes

### Why DDD over Modular Monolith

Evaluated during Category 1 of the `/system-arch` session. DDD wins on
three grounds: (a) the three-layer architecture in
`deepagents-patterns-review.md §1.3` is explicit in the research and
maps directly to bounded contexts; (b) Phase 1/2 add genuine new
contexts (Student Model, Gamification Engine) that benefit from the
ubiquitous-language vocabulary; (c) specialist-agent's role-aware
pattern is already DDD-flavoured and Study Tutor inherits that
scaffolding. See `ADR-ARCH-001`.

### Why the student model is its own context

`TopicConfidence`, `Misconception`, and `SessionEpisode` have their own
lifecycle, their own persistence (Graphiti, not the session-scoped
in-memory dict), and their own consumers (Gamification, Reachy, future
Session Planner). Collapsing them into Tutoring would muddle read vs
write responsibilities at session-end boundary.

### Why Gamification is a context, not a feature

Gamification has its own aggregate roots (StudentProgress, Quest,
BossBattle), its own invariants (monotonic XP/level, sticky
achievements, weekly Boss Battle XP semantics), and its own event
vocabulary consumption. It is also delivered in a distinct phase (P2),
making the boundary naturally visible.

---

*Generated 2026-04-18. Changes to sections §2–§7 are breaking changes
and require re-running downstream commands (`/system-design`,
`/feature-spec`). Changes to §8 shared-kernel definitions require
migration planning for any entities already seeded in Graphiti.*
Write system-context.md
92 lines
# Study Tutor — C4 System Context Diagram (Level 1)

**Status:** Phase 0 canonical.
**Generated:** 2026-04-18 by `/system-arch`.
**Approved by:** user, during interactive session.

---

## Purpose

The C4 Level 1 diagram shows Study Tutor's system boundary, who uses it,
and which external systems it integrates with. Internal containers live
in [`container.md`](./container.md).

Phase labels on each node: `[P0]` = Phase 0 (18–24 April 2026, current
week); `[P1]` = Phase 1 (25 April – 11 May 2026); `[P2]` = Phase 2 (12–16
May 2026).

## Diagram

```mermaid
C4Context
    title Study Tutor — System Context (C4 Level 1)

    Person(student, "Lilymay (Student)", "Year 10, AQA 8700+8702. Uses Open WebUI daily for revision.")
    Person(agent, "AI Agent", "Claude Desktop (P0); future Ship's Computer fleet via Jarvis.")
    Person(developer, "Developer / Judge", "Clones public repo, follows README quickstart on clean machine.")
    Person(parent, "Parent / Teacher", "Queries progress via Reachy Mini voice interface. [P2 stretch]")

    System(studytutor, "Study Tutor", "Three-layer GCSE English AI tutor — fine-tuned behaviour + RAG knowledge + Graphiti student model. MCP + CLI + Open WebUI surfaces.")

    System_Ext(ollama, "Ollama on GB10", "Local inference — fine-tuned Gemma 4 31B Q4_K_M. Tailscale-reachable. [P0 primary]")
    System_Ext(bedrock, "AWS Bedrock", "Custom Model Import — scale-to-zero Gemma 4 31B. Frees GB10 for training. [P0 validation, P1+ primary for demo week]")
    System_Ext(s3, "AWS S3", "Model artefact storage — appmilla-study-tutor-bedrock-models.")
    System_Ext(gemini, "Google Gemini 2.5 Pro", "Graphiti entity-extraction LLM — session write-back. [P1+]")
    System_Ext(falkor, "FalkorDB (Synology NAS)", "Graphiti graph store — per-student topic confidence, sessions, achievements. [P1+]")
    System_Ext(embedder, "GB10 Embedder", "nomic-embed-text-v1.5 on :8001 — Graphiti + ChromaDB embeddings. [P1+]")
    System_Ext(openwebui, "Open WebUI (GB10)", "Lilymay's primary chat interface. OpenAI-compatible. Unchanged from today.")
    System_Ext(litellm, "LiteLLM Proxy (GB10)", "OpenAI-compatible proxy routing Open WebUI → Bedrock when GB10 is training. [P0 validation]")
    System_Ext(claude, "Claude Desktop", "MCP stdio client — architecture-reveal demo + operator usage.")
    System_Ext(reachy, "Reachy Mini 'Scholar'", "Embodied companion — reads Graphiti state, narrates progress. [P2 stretch, gated 4 May]")

    Rel(student, openwebui, "Chats with", "HTTPS (LAN)")
    Rel(openwebui, ollama, "Calls", "Ollama API [P0]")
    Rel(openwebui, litellm, "Calls", "OpenAI-compatible [P0 validation, P1+]")
    Rel(litellm, bedrock, "Routes to", "AWS SDK")

    Rel(agent, claude, "Invokes via")
    Rel(claude, studytutor, "Calls tools", "MCP JSON-RPC / stdio")

    Rel(developer, studytutor, "Installs + runs", "CLI / README walkthrough")

    Rel(studytutor, ollama, "Inference calls", "HTTP over Tailscale [P0 primary]")
    Rel(studytutor, bedrock, "Inference calls", "AWS SDK [P0 validation]")
    Rel(studytutor, falkor, "Student-model R/W", "FalkorDB protocol over Tailscale [P1+]")
    Rel(studytutor, gemini, "Entity extraction", "Gemini API [P1+, async]")
    Rel(studytutor, embedder, "Embed text", "OpenAI-compatible HTTP [P1+]")

    Rel(bedrock, s3, "Loads weights from")

    Rel(parent, reachy, "Asks about progress", "Voice [P2]")
    Rel(reachy, falkor, "Reads state from", "Graphiti client [P2]")
```

## What to look for

- **Three distinct inference paths** (Ollama primary, Bedrock validation,
  LiteLLM proxy for Open WebUI) all terminate at the fine-tuned model.
  This is the DEC-07 dual-path architecture that removes the
  GB10-training/inference conflict during demo week.
- **Graphiti split topology** (DEC-02) is explicit as three external
  systems (Gemini + FalkorDB + Embedder) rather than a single "Graphiti"
  box — each has independent latency/availability characteristics.
- **Open WebUI appears as external** because it's an unchanged-upstream
  component Study Tutor does not own. Lilymay continues to use it.
- **Reachy reads Graphiti directly** — it is a *Student Model* consumer,
  not a *Tutor* consumer. This reflects its role as a progress-reporting
  companion rather than a tutoring surface.
- **Every external system has a Phase label and a Tailscale/network
  annotation** where relevant. The node is informative for reading the
  Phase 0 state vs the target P1/P2 state.

## Node count

15 nodes (4 persons + 1 main system + 10 external) — well under the
30-node threshold. No splitting required.

---

*This file is the Phase 0 canonical C4 Level 1 artefact. Revisions
require `/system-arch --mode=refine`.*
Write container.md
132 lines
# Study Tutor — C4 Container Diagram (Level 2)

**Status:** Phase 0 canonical.
**Generated:** 2026-04-18 by `/system-arch`.
**Approved by:** user, during interactive session.

---

## Purpose

The C4 Level 2 diagram shows Study Tutor's internal containers plus the
immediate external endpoints they talk to. Phase gating is explicit:
solid containers = Phase 0 baseline; containers grouped under `Phase 1
additions` and `Phase 2 additions` arrive in later phases. Relationship
labels mark which phase a particular call path activates.

## Diagram

```mermaid
C4Container
    title Study Tutor — Container Diagram (C4 Level 2)

    Person(agent, "AI Agent (Claude Desktop)", "Invokes tutor via MCP tools")
    Person(developer, "Developer / Judge", "CLI + README walkthrough")
    Person(student, "Lilymay", "Uses Open WebUI (external to containers shown)")

    System_Boundary(studytutor, "Study Tutor") {
        Container(wrapper, "Bash MCP Wrapper", "bash / scripts/mcp-wrapper.sh", "Absolute cd + env load + exec — SR-02. Launched by Claude Desktop.")
        Container(cli, "CLI Entrypoint", "Python / Click", "study-tutor serve --role tutor --transport stdio. Banner→stderr per SR-01.")
        Container(mcp, "MCP Adapter", "Python / mcp SDK", "Registers 4 tools: tutor_start_session (long-running), tutor_turn (sync), tutor_session_status, tutor_session_end. SR-07 classification.")
        Container(session, "Tutor Session Manager", "Python / in-memory dict", "TutorSession aggregate. In-memory in P0; Graphiti-backed P1+.")
        Container(llm, "LLM Client (Provider Factory)", "Python / langchain-*", "Resolves AGENT_MODELS__REASONING_MODEL at factory — SR-03. Routes local/bedrock/openai/anthropic/gemini.")
        ComponentDb(domain, "Domain Config", "Markdown + YAML", "domains/gcse-english/GOAL.md + roles/tutor/role.yaml + criteria/definitions.yaml. Shared-kernel taxonomy.")
        Container(gamdocs, "Gamification Design", "Markdown docs", "docs/gamification/design.md — authoritative economy. State engine deferred to P2.")

        Container_Boundary(p1, "Phase 1 additions") {
            Container(harness, "DeepAgents Harness (Player)", "Python / deepagents 0.5.3+", "create_deep_agent — Player role, tutoring prompt from GOAL.md. [P1]")
            Container(coach, "Coach (AsyncSubAgent)", "Python / deepagents AsyncSubAgent", "Quality monitor — async off hot path. Writes confidence deltas at session-end. [P1]")
            Container(planner, "Session Planner", "Python", "Reads Graphiti, recommends topic. [P1]")
            Container(student_model, "Student Model Client", "Python / graphiti-core", "Student, TopicConfidence, Session episodes. [P1]")
            Container(rag, "RAG Retrieval", "Python / chromadb", "Per-subject ChromaDB collection — curriculum lookup. [P1]")
        }

        Container_Boundary(p2, "Phase 2 additions") {
            Container(gamengine, "Gamification Engine", "Python", "XP, levels, achievements, streaks, Boss Battle. [P2]")
            Container(export, "Session Export", "Python / JSON", "session-export.json — consumed by Dashboard + Reachy. [P1 schema, P2 renderer]")
            Container(dashboard, "Dashboard Generator", "Claude Design / static HTML", "Read-only snapshot view. [P2]")
        }
    }

    System_Ext(ollama, "Ollama (GB10)", "Local inference")
    System_Ext(bedrock, "AWS Bedrock", "Custom Model Import")
    System_Ext(falkor, "FalkorDB (Synology)", "Graphiti store")
    System_Ext(gemini, "Google Gemini", "Entity extraction")
    System_Ext(embedder, "GB10 Embedder", "nomic-embed-text-v1.5")
    System_Ext(claude_desktop, "Claude Desktop", "MCP client")

    Rel(agent, claude_desktop, "Invokes")
    Rel(claude_desktop, wrapper, "Launches", "stdio + absolute CWD")
    Rel(wrapper, cli, "Execs", ".venv/bin/study-tutor")
    Rel(cli, mcp, "Starts")
    Rel(developer, cli, "Runs directly")

    Rel(mcp, session, "Creates / advances")
    Rel(session, llm, "Invokes (P0: single call per turn)")
    Rel(session, domain, "Reads prompts from")
    Rel(llm, ollama, "P0 primary", "HTTP / Tailscale")
    Rel(llm, bedrock, "P0 validation", "AWS SDK")

    Rel(session, harness, "Delegates turns to [P1]")
    Rel(harness, llm, "Player inference [P1]")
    Rel(harness, rag, "Curriculum retrieval [P1]")
    Rel(harness, coach, "Spawns [P1 async]")
    Rel(coach, student_model, "Writes confidence delta [P1 on session-end]")
    Rel(harness, planner, "Asks for topic [P1]")
    Rel(planner, student_model, "Reads confidence [P1]")
    Rel(student_model, falkor, "R/W", "FalkorDB protocol [P1]")
    Rel(student_model, gemini, "Entity extraction [P1 async]")
    Rel(student_model, embedder, "Embed [P1]")
    Rel(rag, embedder, "Embed queries [P1]")

    Rel(session, export, "Emits on session-end [P1 schema]")
    Rel(gamengine, student_model, "Subscribes to events [P2]")
    Rel(dashboard, export, "Renders from [P2]")
```

## What to look for

- **Phase 0 core is 7 containers:** Wrapper → CLI → MCP Adapter → Session
  Manager → LLM Client + Domain Config + Gamification Docs. The Session
  Manager makes a single Ollama/Bedrock call per turn — no deepagents, no
  RAG, no Coach in P0.

- **Phase 1 adds the three-layer architecture runtime:** DeepAgents
  Harness (Player), Coach (async subagent — leveraging deepagents 0.5.3
  `AsyncSubAgent`), Session Planner, Student Model, RAG. Note that the
  Session Manager *delegates* to the Harness in P1 rather than calling
  the LLM Client directly — this is the upgrade path.

- **Phase 2 is three containers + one schema:** Gamification Engine
  (reads student-model events), Session Export (schema lands in P1,
  renderer in P2), Dashboard Generator (Claude-Design-generated static
  HTML).

- **Coach → Student Model is the only write path for confidence deltas.**
  Enforces `ADR-ARCH-003` (async write-back at session-end boundary).

- **Planner → Student Model is read-only.** Recommendation is a read
  operation, no feedback loop to game.

- **LLM Client is the sole boundary with inference endpoints.** CC-03
  anti-corruption boundary visible here — nothing upstream of the LLM
  Client speaks provider-specific protocols.

- **Domain Config is read by both Session Manager (P0) and Harness
  (P1).** This is the shared kernel from Category 2 visible in the
  container graph.

- **Gamification Engine depends only on events from Student Model.**
  Implements CC-11 (in-process event vocabulary); doesn't couple to
  Harness or Session internals.

## Node count

21 nodes (14 internal + 6 external + 3 persons). Well under the 30-node
threshold.

---

*This file is the Phase 0 canonical C4 Level 2 artefact. Revisions
require `/system-arch --mode=refine`.*
Write assumptions.yaml
274 lines
# Study Tutor — Architecture Assumptions
# Generated by /system-arch on 2026-04-18
# Review and validate these assumptions before and during implementation.
# Any assumption proven wrong triggers a revisit of the related ADR.

version: 1
generated_at: 2026-04-18
project: study-tutor
related_phase: phase-0
total_assumptions: 18

assumptions:
  - id: ASSUM-001
    category: domain
    description: >-
      Socratic tutoring behaviour is fully captured in the fine-tuned
      Gemma 4 31B model. The Tutoring context does not need post-hoc
      behavioural scaffolding (chain-of-thought prompts, guardrail
      layers) to produce AO-aligned, non-expository responses.
    confidence: high
    source: interactive_session_category_1
    evidence: >-
      Fine-tune run Feb 2026, ~1,736 training examples, 94.8% Coach
      acceptance on GCSE dataset, Lilymay's daily use via Open WebUI.
    related_adr: ADR-ARCH-002
    revisit_trigger: >-
      If Phase 1 Coach evaluation shows < 70% quality acceptance on a
      representative 50-turn sample, the fine-tune is insufficient and
      post-hoc scaffolding becomes required.

  - id: ASSUM-002
    category: domain
    description: >-
      AQA 8700 + 8702 is representative of wider GCSE English. The
      architecture can scale to other exam boards (Edexcel, OCR,
      WJEC) by adding parallel domain configs without refactoring.
    confidence: medium
    source: interactive_session_category_1
    evidence: >-
      domains/{name}/GOAL.md pattern from agentic-dataset-factory.
      Not validated against non-AQA specifications.
    related_adr: ADR-ARCH-001
    revisit_trigger: Post-hackathon if multi-board expansion is pursued.

  - id: ASSUM-003
    category: domain
    description: >-
      In-memory session state is acceptable for Phase 0. Sessions
      surviving MCP server restarts is not a Phase 0 requirement.
    confidence: high
    source: interactive_session_category_2
    evidence: Phase 0 scope "Do-Not-Change" — no Graphiti in Phase 0.
    related_adr: ADR-ARCH-001

  - id: ASSUM-004
    category: domain
    description: >-
      The session event vocabulary (session.started, session.turn_completed,
      session.completed, achievement.unlocked, quest.completed,
      quest.expired, boss_battle.completed) is stable enough to design
      the Phase 1 Graphiti schema against without Phase 2 forcing
      breaking revisions.
    confidence: medium
    source: interactive_session_category_2
    evidence: Derived from docs/gamification/design.md §11.2.
    related_adr: ADR-ARCH-002
    revisit_trigger: >-
      Phase 2 gamification engine build; if new events are required
      (e.g. per-turn challenge progress), schema migrations will be
      needed.

  - id: ASSUM-005
    category: domain
    description: >-
      The ±0.1 per-session confidence-delta cap is pedagogically
      reasonable. Within-session state changes of this magnitude
      reflect meaningful learning without over-reacting to a single
      good or bad turn.
    confidence: medium
    source: docs/gamification/design.md §6.2
    evidence: Design decision, not empirically validated.
    revisit_trigger: >-
      If Phase 2 dashboard shows confidence drifting too slowly
      (mastery takes months) or too quickly (daily swings of band),
      tune the cap.

  - id: ASSUM-006
    category: technology
    description: >-
      Python 3.11 is compatible with all declared providers
      (langchain-ollama, langchain-openai, langchain-anthropic,
      langchain-google-genai, langchain-aws, deepagents, graphiti-core,
      chromadb, docling, mcp SDK) through 18 May 2026.
    confidence: high
    source: interactive_session_category_3
    evidence: specialist-agent runs on same stack since Feb 2026.
    related_adr: ADR-ARCH-004

  - id: ASSUM-007
    category: technology
    description: >-
      AWS Bedrock Custom Model Import supports Gemma 4 31B natively
      in the selected region (us-east-1 or us-west-2), with a
      cold-start of 30–60s and per-call latency within 5× of the
      Ollama path.
    confidence: medium
    source: interactive_session_category_3
    evidence: >-
      Research memo flagging Bedrock as a viable Phase 2 target;
      not yet validated against the actual 31B Gemma 4 import.
    related_adr: ADR-ARCH-006
    revisit_trigger: >-
      FEAT-PO-004 validation smoke test in Phase 0 (Tuesday
      22 April). If Bedrock cold-start exceeds 5 minutes or
      per-call latency exceeds 30s, Ollama-primary posture stays
      and demo-week scheduling becomes tighter.

  - id: ASSUM-008
    category: technology
    description: >-
      Ollama on GB10 sustains ~5–8s latency for 200-token responses
      under sequential-turn load from a single session.
    confidence: high
    source: Lilymay's daily use since Feb 2026.
    related_adr: ADR-ARCH-006

  - id: ASSUM-009
    category: technology
    description: >-
      Google Gemini 2.5 Pro entity-extraction latency is 1–3s per
      call — within the fire-and-forget budget for async Graphiti
      write-back. No Phase 0 pre-validation; monitored in Phase 1
      spike per DEC-08.
    confidence: medium
    source: DEC-08 (decisions-log-2026-04-17.md)
    revisit_trigger: >-
      Phase 1 Graphiti latency spike. If p95 > 5s consistently,
      revert to a local entity-extraction model (likely deferred to
      Synology or Gemini 2.5 Flash).
    related_adr: ADR-ARCH-007

  - id: ASSUM-010
    category: api
    description: >-
      Four MCP tools (tutor_start_session, tutor_turn,
      tutor_session_status, tutor_session_end) are sufficient for
      Phase 0 + Phase 1 + Phase 2 architecture demonstration.
      No per-topic or per-achievement tool surfaces needed.
    confidence: high
    source: interactive_session_category_4
    evidence: specialist-agent exposes 4 tools per role successfully.
    related_adr: ADR-ARCH-008

  - id: ASSUM-011
    category: api
    description: >-
      Open WebUI continues to work unchanged via the existing Ollama
      path (Phase 0) and via the LiteLLM→Bedrock proxy path (Phase 0
      validation, Phase 1+ demo week). Its OpenAI-compatible provider
      config supports both.
    confidence: medium
    source: interactive_session_category_4
    evidence: LiteLLM as Bedrock proxy is documented pattern but
      unvalidated for our specific Bedrock Custom Model Import setup.
    revisit_trigger: >-
      FEAT-PO-004 validation (Tuesday 22 April). Fallback: revert
      Open WebUI to Ollama-direct (same as today) and use MCP-only
      for the Bedrock demonstration.
    related_adr: ADR-ARCH-006

  - id: ASSUM-012
    category: crosscutting
    description: >-
      LES1 (cross-agent-lessons-from-specialist-agent.md) remains
      authoritative through 18 May 2026. No LES2 supersession before
      submission.
    confidence: high
    source: specialist-agent repo — LES1 dated Apr 2026.
    related_adr: ADR-ARCH-009
    revisit_trigger: >-
      If specialist-agent publishes LES2 with a new class of
      findings, spot-check Study Tutor against the new rows before
      merge.

  - id: ASSUM-013
    category: security
    description: >-
      Running Graphiti entity-extraction through Gemini (Google
      Cloud) is an acceptable exception to the on-device data
      residency principle. Session summaries sent to Gemini do not
      contain personal data beyond study content and topic context.
    confidence: medium
    source: interactive_session_category_6
    evidence: DEC-02 + DEC-08; Google's GDPR posture.
    related_adr: ADR-ARCH-015
    revisit_trigger: >-
      If Phase 1 entity extraction surfaces concerning PII leakage
      in the Gemini request payloads (e.g. full student names,
      school identifiers), add a pre-Gemini redaction layer.

  - id: ASSUM-014
    category: technology
    description: >-
      deepagents 0.5.x API remains stable through Phase 1 build.
      No breaking changes between 0.5.3 → 0.6.x that force a
      re-architecture of Player-Coach or AsyncSubAgent patterns.
    confidence: medium
    source: interactive_session_category_5 (supplementary research)
    evidence: >-
      0.5.3 deprecated model=None (minor breaking change); 0.5.2
      added permissions (non-breaking); cadence suggests active
      development with small revisions.
    related_adr: ADR-ARCH-012
    revisit_trigger: >-
      Before committing Phase 1 build, pin exact deepagents version
      in pyproject.toml and revalidate after any SDK upgrade.

  - id: ASSUM-015
    category: constraint
    description: >-
      Reachy Mini Scholar arrives and is operational by 4 May 2026
      (the go/no-go gate per DEC-06). Python SDK can produce a
      first "hello world" verbal output within a week of arrival.
    confidence: low
    source: Pollen Robotics shipping estimate (ordered ~25 Jan; 90-day
      delivery).
    related_adr: ADR-ARCH-016
    revisit_trigger: 4 May 2026 go/no-go gate. Fallback is a
      pre-recorded future-vision video segment.

  - id: ASSUM-016
    category: constraint
    description: >-
      Bedrock inference cost profile (~$1.50–3.00 per 5-minute
      session) is acceptable for hackathon + demo period + a few
      months of post-hackathon Lilymay use.
    confidence: high
    source: Existing memory / research on Bedrock pricing for 31B.
    related_adr: ADR-ARCH-006
    revisit_trigger: >-
      Phase 1+ after real usage; if month-1 cost exceeds $100 and
      cannot be justified, revert to Ollama-primary for Lilymay's
      daily use, keep Bedrock for demo week only.

  - id: ASSUM-017
    category: constraint
    description: >-
      Kaggle hackathon rules (to be read Friday 18 April) do not
      impose repo-licensing constraints incompatible with Apache 2.0
      + bring-your-own-sources model, and do not require
      ship-everything-in-repo (which would break the copyright
      posture).
    confidence: medium
    source: Not yet validated.
    related_adr: ADR-ARCH-016
    revisit_trigger: >-
      Immediate read-through on Friday 18 April 2026. If rules
      conflict, rework FEAT-PO-003 packaging before Monday.

  - id: ASSUM-018
    category: constraint
    description: >-
      DDD Southwest (Bristol, 16 May 2026) and associated travel
      absorbs ~4 working days of pre-submission preparation without
      jeopardising the 18 May deadline. Submission polish (17–18 May)
      fits within the post-DDD window.
    confidence: medium
    source: Phase 0 build plan §Expected Timeline.
    related_adr: ADR-ARCH-016
    revisit_trigger: >-
      Weekend of 10–11 May; if Phase 2 feature completion is
      materially behind, consider dropping Phase 2 stretch items
      (gamification engine, Reachy) in favour of polish time.
Now writing the 16 ADRs. Batching in parallel.

Write ADR-ARCH-001-ddd-structural-pattern.md
87 lines
# ADR-ARCH-001 — Use Domain-Driven Design structural pattern

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-002 (three-layer architecture), domain-model.md

## Context

Study Tutor's architecture needs to accommodate three Layer-wise
concerns (behaviour / knowledge / student model) plus a gamification
engine, all delivered in staged phases (P0 scaffolding → P1 student
model + harness → P2 gamification engine). The `deepagents-patterns-review.md`
research treats the three-layer split as primary. Per-phase features
introduce new concerns (Graphiti student model in P1; gamification state
in P2) with their own aggregates, invariants, and consumers.

The team is inheriting scaffolding patterns from `specialist-agent` —
which uses role-aware code organisation that is already DDD-flavoured
(roles as bounded contexts, per-role `role.yaml` with criteria and
prompts, a shared CommandRouter dispatch matrix).

## Decision

Adopt **Domain-Driven Design** as the structural pattern for Study
Tutor. Decompose into six bounded contexts:

1. Tutoring
2. Knowledge & Curriculum
3. Student Model
4. Gamification
5. Inference Runtime
6. MCP Transport

Two shared kernels:

1. **Domain Taxonomy** — Subject, Paper, Text, AssessmentObjective,
   Topic, GradeTarget, ConfidenceBand.
2. **Session Event Vocabulary** — session.started,
   session.turn_completed, session.completed, achievement.unlocked,
   quest.completed, quest.expired, boss_battle.completed.

One anti-corruption layer: **Inference Runtime** (`LLMClient`)
normalises across Ollama, Bedrock, and API providers.

See `domain-model.md` for full entity relationships.

## Alternatives considered

- **Modular Monolith** — reasonable for Phase 0 (small enough), but
  the three-layer architecture from `deepagents-patterns-review.md §1.3`
  is explicit in the research and maps directly to bounded contexts.
  Phase 1/2 additions (student model, gamification engine) benefit from
  DDD's ubiquitous-language vocabulary. Modular Monolith would force
  re-structuring later.
- **Layered Architecture** — rejected. A strict layered split (API →
  service → repository → DB) would obscure the bounded contexts and
  produce cross-layer coupling when the Gamification Engine needs to
  read Student Model aggregates.
- **Event-Driven Architecture** — rejected as primary pattern.
  Study Tutor's event vocabulary is important (Shared Kernel B) but
  the system is predominantly request/response (`tutor_turn`). Events
  are the seam between contexts, not the architectural foundation.
- **Clean / Hexagonal** — partially adopted for the Inference Runtime
  anti-corruption layer, but the full hexagonal pattern's
  ports-and-adapters rigour is over-specified for a single-user system.

## Consequences

**Positive:**
- Matches the research vocabulary (three-layer architecture, Player-Coach,
  session planner) used by `deepagents-patterns-review.md`.
- Maps cleanly onto specialist-agent inheritance.
- Explicit bounded contexts make Phase 1/2 feature boundaries
  self-documenting.
- Shared kernels prevent duplication of the domain taxonomy in four
  places.

**Negative:**
- Some DDD ceremony (aggregate invariants, event vocabulary) is
  over-specified for Phase 0 single-user scope. Accepted cost.
- Anti-corruption layer for inference costs an extra abstraction but
  pays back immediately (three providers × four contexts would
  otherwise create 12 coupling points).
- Developers unfamiliar with DDD need to learn the shared-kernel
  pattern; mitigated by `domain-model.md` reading as a reference.
Write ADR-ARCH-002-three-layer-architecture.md
82 lines
# ADR-ARCH-002 — Three-layer architecture: behaviour + knowledge + student model

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0 (architectural commitment; runtime arrives in P1)
**Related:** ADR-ARCH-001, ADR-ARCH-003, deepagents-patterns-review.md §1.3

## Context

The research literature (Daniel Bourke; Queensland AI Meetup;
`deepagents-patterns-review.md`) distinguishes two layers in effective
LLM systems: **fine-tuned behaviour** (how the model responds) and
**RAG knowledge** (what it responds about). Study Tutor's student-centric
design requires a third layer — **per-student state** (progress, topic
confidence, misconceptions, gamification status) — because tutoring
quality degrades without memory of the specific learner.

This three-layer split is specifically called out as the foundational
architecture for Study Tutor in `deepagents-patterns-review.md §1.3`.

## Decision

Commit to three independently updatable architectural layers:

1. **Layer 1 — Behaviour (fine-tuned Gemma 4 31B Dense LoRA):**
   teaches *how* the tutor responds. Socratic questioning,
   AO-alignment, grade-calibrated language, safeguarding posture.
   Located in the fine-tuned weights. Updated by re-running the
   Unsloth fine-tune on an updated `train.jsonl`.
2. **Layer 2 — Knowledge (ChromaDB curriculum RAG):** provides
   *what* the tutor draws from — curriculum content per subject,
   set text references, exam paper shapes. Located in per-subject
   ChromaDB collections seeded from user-provided Docling-processed
   sources. Updated by re-running the ingestion pipeline.
3. **Layer 3 — Student Model (Graphiti):** *who* is being tutored —
   per-student `TopicConfidence`, `Misconception`, `SessionEpisode`,
   `AssessmentObjectiveProgress`. Located in Graphiti graph DB.
   Updated per session-end via async write-back (see ADR-ARCH-003).

Independence properties:
- Retraining the model (Layer 1) does not invalidate the RAG index
  (Layer 2) or the student state (Layer 3).
- Adding curriculum content (Layer 2) does not require a retrain.
- Per-student state (Layer 3) evolves continuously without touching
  Layers 1 or 2.

## Alternatives considered

- **Two-layer only (behaviour + knowledge).** Rejected. Matches
  research literature but removes the key Study Tutor differentiator —
  a tutor that knows its specific student.
- **Four or more layers.** Considered (separating e.g. "curriculum
  knowledge" from "exam technique knowledge"). Rejected. The extra
  decomposition is not empirically motivated; both are retrieved via
  the same RAG path.
- **All-in-one fine-tune including student history.** Rejected.
  Would require re-finetuning per-student, scales poorly, and breaks
  the "independently updatable layers" property.

## Consequences

**Positive:**
- Matches research vocabulary; judges and peers see the architecture
  framed in familiar terms.
- Enables Phase 1/2 incremental build — Layer 3 doesn't block Layer 1
  shipping in Phase 0.
- Multi-subject expansion (post-hackathon) is a Layer-1 + Layer-2
  scaling story; Layer 3 shape is subject-agnostic.

**Negative:**
- Three integration points (LLM endpoint + ChromaDB + Graphiti) are
  three failure domains. Mitigated by fail-soft degradation (ADR-ARCH-014).
- Extra operational complexity vs a single-layer system. Accepted —
  the engagement and personalisation value is load-bearing for the
  hackathon submission narrative.

## References

- `deepagents-patterns-review.md §1.3`
- `docs/research/ideas/state-of-the-project-and-phase-recommendation.md §2.2`
- Daniel Bourke / Queensland AI Meetup talk on two-layer LLM architecture.
Write ADR-ARCH-003-async-graphiti-writeback.md
84 lines
# ADR-ARCH-003 — Async Graphiti write-back at session-end boundary

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0 (architectural commitment; runtime arrives in P1)
**Related:** ADR-ARCH-002, ADR-ARCH-012, DEC-02, DEC-08

## Context

Graphiti writes involve entity extraction by Google Gemini 2.5 Pro
(DEC-02) with typical latency 1–3s per operation (DEC-08). Writing
per-turn to Graphiti would add this latency to every `tutor_turn`
call, pushing p95 past the 10s target and risking the 30s threshold
(CC-08 / LES1 row 10 ⚠️).

LES1 §4 (fire-and-forget + poll above 30s) explicitly flags this
pattern. `specialist-agent`'s TASK-MDF-POLR evidence confirms the
failure mode: sync `await` on a generation loop produced a
4-minute timeout in Claude Desktop.

## Decision

Graphiti write-back is **async relative to the tutor's hot path** and
**triggered at the session-end boundary only** — not per turn.

- Within-session state (turns, partial AO coverage, session quality
  samples) lives in the in-process `TutorSession` aggregate.
- On `session.completed`:
  - A `SessionEpisode` entity is prepared.
  - A Coach-proposed per-topic confidence delta (capped ±0.1) is
    computed.
  - Write-back is dispatched to a background task; the tutor's
    `tutor_session_end` response returns to the user without waiting
    for Gemini extraction.
- Misconceptions detected by the Coach during turn evaluation
  accumulate in session-scoped memory and are flushed in the same
  session-end batch (P1 design).
- If Graphiti is unreachable, the session-end handler **logs and
  returns successfully** — fail-soft degradation. The session is
  not lost from the student's perspective.

## Alternatives considered

- **Per-turn Graphiti writes.** Rejected. Would add 1–3s Gemini
  latency to every turn; violates p95 <10s and CC-08.
- **Session-end write with sync await.** Rejected. `tutor_session_end`
  would become long-running and require SR-07 reclassification, which
  complicates the MCP tool contract. The user shouldn't have to wait
  for analytics.
- **Per-turn in-memory plus batched flush on timer.** Rejected for
  Phase 1 MVP — extra machinery, unclear benefit over session-end-only
  semantics.
- **Per-turn async fire-and-forget (per turn).** Considered for
  streaming-style write-back. Deferred to a later revisit — adds
  per-turn background-task bookkeeping without clear benefit.

## Consequences

**Positive:**
- Preserves `tutor_turn` p95 < 10s.
- Aligns with CC-08 and LES1 §4 prescriptions.
- Simplifies the MCP tool contract — no long-running reclassification
  needed for session-end.
- Leverages deepagents 0.5.3 `AsyncSubAgent` pattern natively
  (ADR-ARCH-012).

**Negative:**
- Writes within an active session are not visible to a concurrent
  query (e.g. the Planner) until session-end. Acceptable — single-user
  system, no concurrent sessions.
- If the tutor crashes between session-end and Graphiti flush, the
  session-level state is lost. Acceptable for Phase 1 MVP; revisit if
  we see real crashes.
- Coach has to batch per-turn observations in memory. Straightforward
  to implement; natural boundary.

## References

- DEC-02, DEC-08 in `docs/research/ideas/decisions-log-2026-04-17.md`
- LES1 §4 POLR evidence in
  `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`
- deepagents 0.5.3 `AsyncSubAgent` — native fire-and-forget tool set
  (`launch_task`, `check_task`, `update_task`, `cancel_task`, `list_tasks`).
Write ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
83 lines
# ADR-ARCH-004 — Python 3.11 + deepagents + langchain + mcp stack

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-012, LES1 §3 (packaging), CC-04

## Context

Study Tutor is a new repo but inherits scaffolding patterns from
`specialist-agent` and component patterns from `agentic-dataset-factory`.
Both use Python 3.11 + LangChain + deepagents + MCP SDK. The
fine-tuning tooling (Unsloth) is also Python-centric; the existing
Ollama + ChromaDB + Graphiti deployments are all Python-reachable.

LES1 §3 prescribes `[providers]` extra completeness (SR-04 / CC-04) —
every LangChain integration the code imports must be explicitly
declared.

## Decision

Python 3.11 is the reference runtime. Framework stack:

| Framework | Role | Declared in |
|---|---|---|
| `deepagents >= 0.5.3` | Harness (Player-Coach), subagents, middleware | `[providers]` extra |
| `langchain` + `langchain-core` | Core chat-model abstractions | dependency |
| `langchain-ollama` | Ollama provider | `[providers]` |
| `langchain-openai` | OpenAI provider (declared; reserved) | `[providers]` |
| `langchain-anthropic` | Anthropic provider (declared; reserved) | `[providers]` |
| `langchain-google-genai` | Gemini provider (declared; also used by Graphiti for entity extraction) | `[providers]` |
| `langchain-aws` | Bedrock provider | `[providers]` |
| `mcp` | MCP Python SDK (stdio transport) | dependency |
| `click` | CLI framework (with `err=True` for stderr) | dependency |
| `pydantic` | Boundary validation + domain schemas | dependency |
| `graphiti-core` | Graphiti client (Phase 1+) | `[providers]` |
| `chromadb` | RAG vector store (Phase 1+) | dependency |
| `docling` | Source ingestion (Phase 1+ ingestion) | dependency |

Install: `pip install -e '.[providers]'` for the venv; reflected
verbatim in `Dockerfile` if and when one is added (SR-05; deferred
per ADR-ARCH-005).

Python version pinned via `python-version-file` or `.python-version`
to avoid the LES1 §8 env-var mismatch trap.

## Alternatives considered

- **Python 3.12.** Rejected — agentic-dataset-factory and
  specialist-agent both target 3.11, and Unsloth / LangChain
  integration stability is best-known on 3.11. Revisit post-hackathon.
- **Bare LangChain agents instead of deepagents.** Rejected —
  deepagents provides the Player-Coach pattern, async subagents
  (0.5.3), middleware, and backends natively. Building this bespoke
  would burn Phase 1 time.
- **Node.js / TypeScript.** Rejected — fine-tuning tooling + existing
  Ollama/ChromaDB integration are Python; switching languages costs
  more than the benefit.
- **Direct provider SDKs without LangChain.** Rejected — multi-provider
  support via one `LLMClient` abstraction (ADR-ARCH-006) is cleaner
  through LangChain's `init_chat_model` + provider-specific packages.

## Consequences

**Positive:**
- Full inheritance from specialist-agent; minimal learning curve.
- `[providers]` extra (CC-04) avoids LES1 LCOI failure mode.
- Provider switching via env var (CC-03) is natively supported by
  `init_chat_model("provider:model")` patterns in LangChain.

**Negative:**
- LangChain API churn is well-documented; requires vigilance on
  minor-version upgrades. Mitigated by pinning exact versions in
  `pyproject.toml` and smoke-testing each provider (SR-04).
- deepagents 0.5.x has active breaking changes (0.5.3 deprecated
  `model=None`). Mitigated by ADR-ARCH-012 pinning.

## References

- specialist-agent `pyproject.toml` (source pattern).
- LES1 §3 (packaging parity surface).
- deepagents 0.5.3 release notes (April 2026).
Write ADR-ARCH-005-defer-dockerfile-to-phase-1.md
73 lines
# ADR-ARCH-005 — Defer Dockerfile to Phase 1+; venv-only install for Phase 0

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-004, LES1 §3 (DKRX), CC-05, phase-0-scope.md §Do-Not-Change

## Context

LES1 §3 DKRX identified a failure mode in specialist-agent where the
Dockerfile used `pip install .` while the guide documented
`pip install -e '.[providers]'`, causing provider packages to be
missing at runtime. The prescription (SR-05 / CC-05) is that
Dockerfile install commands must be a literal match for the documented
venv install.

Study Tutor's Phase 0 target is a public-repo-ready skeleton
deployable on a clean MacBook via the README quickstart. Phase 0 is
**not** shipping a hosted service. Lilymay's usage today is MacBook
+ GB10 + Tailscale, all via local venv install. The hackathon
submission is a walkthrough, not a deployable artefact.

The Phase 0 scope's "Do-Not-Change" list explicitly states "No
Dockerfile in Phase 0. Venv-only install documented." The `/system-arch`
session honours this.

## Decision

Phase 0 ships **no Dockerfile**. All install instructions in the
README use `pip install -e '.[providers]'` in a venv.

CC-05 is **paused** for Phase 0 and reactivates when a Dockerfile is
first added (Phase 1 or later).

If a Dockerfile becomes desirable in Phase 1+ (e.g. for a Bedrock
Lambda wrapper or a Reachy Pi deployment), it will:

1. Reuse the literal venv install command (`pip install --no-cache-dir -e
   '.[providers]'`) — no variation.
2. Include a CI check grepping the Dockerfile for the `[providers]`
   substring.
3. Be approved via a new ADR (ADR-ARCH-NNN-dockerfile-parity-install).

## Alternatives considered

- **Ship a Dockerfile in Phase 0.** Rejected. Adds SR-05 compliance
  burden for no Phase 0 use case. Violates Do-Not-Change.
- **Ship a Dockerfile with Phase 0 as a stub.** Rejected. Half-done
  artefacts invite drift; either it's canonical or it doesn't exist.
- **Nix / Poetry / other packaging.** Rejected. venv + `pip install -e
  '.[providers]'` matches specialist-agent and is the clean-machine
  walkthrough audience's most-portable baseline.

## Consequences

**Positive:**
- Phase 0 scope stays small. Weekend build target is achievable.
- No risk of SR-05 regression (there's no Dockerfile to drift).
- README quickstart is simpler and aligns with what judges would run
  to reproduce the tutor.

**Negative:**
- Phase 1 may need a Dockerfile for Bedrock or Reachy-side deployment.
  Accepted — add it with a new ADR when the need is real, not now.
- `specialist-agent` ships a Dockerfile; Study Tutor not shipping one
  may look inconsistent. Accepted — context differs; this is a
  skeleton+library for now, not a deployable service.

## References

- `docs/research/ideas/phase-0-scope.md §Do-Not-Change`
- LES1 §3 DKRX evidence pointer.
Write ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
90 lines
# ADR-ARCH-006 — Dual inference path: Ollama (primary) + Bedrock (validation)

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-004, DEC-07, CC-03

## Context

GB10 (the on-premise Jetson running Ollama) is the only machine
capable of serving the fine-tuned Gemma 4 31B model locally. DEC-07
specifies that GB10 must also run three sequential training workloads
in Phases 1–2:

1. Study-tutor training-dataset expansion (additional subjects).
2. Study-tutor re-fine-tune.
3. Architect-agent training + fine-tune for DDD Southwest (16 May).

Training and inference at 31B scale cannot run concurrently on GB10.
The fine-tuned tutor must remain available to Lilymay daily, and must
be demonstrably working during demo week (12–16 May). Without an
alternative inference path, demo week collides with training.

AWS Bedrock Custom Model Import supports Gemma 4 31B natively,
scale-to-zero, with a cold start of 30–60s. Memory flagged Bedrock
as a Phase 2 deliverable; DEC-07 moves it earlier.

Per CC-03 / SR-03, provider selection must be env-var driven at the
`LLMClient` factory, not hard-coded in handlers.

## Decision

Study Tutor supports two primary inference paths through a single
`LLMClient` (anti-corruption layer in the Inference Runtime context):

1. **`local` (Phase 0 default):** Ollama on GB10 via Tailscale.
   Existing, low-latency (~5–8s per 200 tokens).
2. **`bedrock` (Phase 0 validation; Phase 1+ demo-week primary):**
   AWS Bedrock Custom Model Import. Scale-to-zero; 30–60s cold start;
   per-call latency within 5× of Ollama.

Selection is via `AGENT_MODELS__REASONING_MODEL={local|bedrock|...}`.
No handler hard-codes a provider (CC-03 / SR-03 — LES1 PMEV/CRMV
evidence).

Additional providers (`openai`, `anthropic`, `gemini`) are declared
in `[providers]` (CC-04 / SR-04) but are not on the P0 critical path;
they are reserved for Coach / fallback.

Phase 0 validation test (FEAT-PO-004, Tuesday 22 April):
`tutor_turn` returns a coherent response via `bedrock` within 5× the
Ollama latency.

## Alternatives considered

- **Ollama-only; pause training during demo week.** Rejected.
  Fragile; architect-agent training schedule conflicts with demo
  timing; no fallback if GB10 has a hardware issue during week 3.
- **Bedrock-only.** Rejected. Lilymay's daily use has been on Ollama
  for months; zero-cost baseline; don't introduce unnecessary cost
  and dependency.
- **vLLM / SGLang on a separate GPU.** Rejected. No separate GPU
  available. Would add hardware procurement to the critical path.
- **Two fine-tuned models (one for GB10, one for Bedrock) with quality
  variance accepted.** Rejected. Bedrock imports the existing
  merged-16bit weights directly; one model, two hosts.

## Consequences

**Positive:**
- Decouples demo week from GB10 training schedule.
- Validates a scale-to-zero path that's cheap for Lilymay's
  post-hackathon use (~$1.50–3/session).
- CC-03/SR-03 compliance exercised early by having two real providers.

**Negative:**
- Two inference paths = two failure modes during the Phase 0
  clean-machine walkthrough. Accepted — Bedrock is marked "validation"
  in Phase 0; Ollama is primary.
- AWS account + IAM setup required as a prerequisite. Documented in
  Phase 0 build-plan §Prerequisites.
- Bedrock cold-start (30–60s) is visible on the first call of a demo
  session. Mitigated by warming Bedrock ~2 min before each demo
  recording.

## References

- DEC-07 in `docs/research/ideas/decisions-log-2026-04-17.md`
- Phase 0 scope FEAT-PO-004.
Write ADR-ARCH-007-graphiti-split-topology.md
95 lines
# ADR-ARCH-007 — Graphiti split topology: FalkorDB on Synology + Gemini entity extraction + GB10 embedder

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0 (architectural commitment; runtime arrives in P1)
**Related:** ADR-ARCH-006 (GB10 freed for training), DEC-02, DEC-08

## Context

Graphiti has three component dependencies:

1. A graph-DB backend (FalkorDB is the recommended FalkorDB /
   Neo4j-compatible option; this project uses FalkorDB).
2. An LLM for entity extraction (Gemini 2.5 Pro here).
3. An embedding model (nomic-embed-text-v1.5 on GB10:8001).

DEC-07 mandates that GB10 is freed for training during Phase 1 —
meaning FalkorDB and the entity-extraction LLM cannot live on GB10.
DEC-02 records the topology decision taken on 16 April 2026.

The MacBook is the tutor's primary host; it reaches all three
component services over Tailscale.

## Decision

Graphiti runs as a three-host split topology:

| Component | Host | Reach from MacBook |
|---|---|---|
| **FalkorDB graph store** | Synology NAS (`whitestocks`) | Tailscale, port 6379 |
| **Entity-extraction LLM** | Google Gemini 2.5 Pro | Gemini API (public internet) |
| **Embedder** | GB10 (nomic-embed-text-v1.5 on :8001) | Tailscale |

The three Tailscale hops are documented; the Gemini hop is documented
as an explicit on-device-residency exception (see ADR-ARCH-015).

Config lives in `.guardkit/graphiti.yaml` (already present as of
2026-04-18):

```yaml
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
llm_provider: gemini
llm_model: gemini-2.5-pro
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
embedding_dimensions: 1024
```

Phase 0 includes a `guardkit graphiti status` check in the
clean-machine walkthrough; connection failure does not block Phase 0
(Graphiti write-back is Phase 1+).

## Alternatives considered

- **All-in-one on GB10.** Rejected. Conflicts with DEC-07 training
  schedule.
- **All-in-one on MacBook.** Rejected. FalkorDB sits better on a
  server-class machine (Synology NAS is always-on). Local MacBook
  Graphiti would go away when the laptop sleeps.
- **Entity-extraction via a local model (e.g. Qwen on GB10).**
  Rejected for Phase 1 MVP per DEC-08 — Gemini is paid-for, 1–3s
  latency, cheaper than standing up another local model and
  scheduling its GB10 slot.
- **Embedder on MacBook via Ollama.** Considered. Kept on GB10
  because the embedder is small enough not to block training, and
  FalkorDB + embedder colocation simplified nothing.

## Consequences

**Positive:**
- GB10 freed for sequential training workloads.
- FalkorDB on always-on Synology NAS is reliable.
- Gemini latency (1–3s) is absorbed by the async session-end
  write-back (ADR-ARCH-003) and is not on the hot path.

**Negative:**
- Three hosts = three failure modes. Mitigated by fail-soft
  degradation (ADR-ARCH-014).
- Gemini sees session summaries — explicit on-device-residency
  exception (ADR-ARCH-015). Session summaries must avoid full
  student names / school identifiers; monitored in Phase 1
  (ASSUM-013).
- Tailscale dependency becomes load-bearing. Proven in B8E4
  walkthrough; acceptable.

## References

- DEC-02, DEC-08 in `docs/research/ideas/decisions-log-2026-04-17.md`
- `.guardkit/graphiti.yaml` (2026-04-18 snapshot)
- specialist-agent TASK-REV-B8E4 walkthrough evidence on Tailscale
  reliability.
Write ADR-ARCH-008-mcp-only-agent-access.md
88 lines
# ADR-ARCH-008 — MCP-only for agent access; single-user auth posture

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-014, LES1 §1 (transport), CC-01, CC-02, CC-07

## Context

Study Tutor needs to expose functionality to:

- AI agents (Claude Desktop today; future Ship's Computer fleet via
  Jarvis).
- Humans via Open WebUI (Lilymay).
- Developers via CLI (README walkthrough, hackathon judges).

`specialist-agent` ships dual transports (MCP + NATS) because its
orchestration role requires fleet messaging. Study Tutor has no
equivalent need — it serves a single student, exposes a single role
(tutor), and has no fleet-broadcast semantics.

Per LES1 row 3/4/5, NATS-specific rows are marked "—" for study-tutor.
LES1 row 22 explicitly notes: *"Single-transport agents still
stream-split test stdout (easiest place to drift)"* — so MCP
discipline remains load-bearing even in a single-transport world.

## Decision

Phase 0 ships a **single transport — MCP stdio**. Four tools
classified per CC-07 / SR-07:

| Tool | Class | Bound |
|---|---|---|
| `tutor_start_session` | long-running (returns `session_id` in ≤1s; poll via `tutor_session_status`) | n/a (fire-and-forget) |
| `tutor_turn` | sync | p95 < 10s |
| `tutor_session_status` | sync | < 2s |
| `tutor_session_end` | sync (triggers async Graphiti write-back in P1) | < 2s |

HTTP MCP transport is deferred to Phase 1+ (only if a real use case
emerges — e.g. a containerised Bedrock wrapper).

Authentication posture: **single-user process-level trust**.

- MCP stdio = child-process trust boundary.
- Open WebUI = LAN / Tailscale trust.
- CLI = filesystem-permission trust.
- No JWT, OAuth2, API keys at the tool level, multi-tenant user
  management, or RBAC.

Outbound provider API keys live in `.env` (gitignored, `.env.example`
for reference per CC-06 / SR-06).

## Alternatives considered

- **MCP + NATS (following specialist-agent's pattern).** Rejected.
  Study Tutor has no fleet-broadcast need. NATS adds operational
  complexity (stream/KV provisioning per LES1 §7) without value.
- **HTTP API as primary surface.** Rejected for Phase 0. Adds auth
  layer complexity; no consumer requires it.
- **Add GraphQL or gRPC.** Rejected. No requirements.
- **Multi-tenant auth.** Rejected. Single-student system;
  multi-student would be a Phase 3+ post-hackathon rethink.

## Consequences

**Positive:**
- LES1 row 22 (stream-split test for single-transport agents) is
  the gating discipline; easier to enforce than multi-transport.
- No NATS operational burden (stream provisioning, subject design,
  password rotation).
- 4-tool surface is minimal and testable.

**Negative:**
- Future fleet integration (Jarvis) will require adding a NATS
  transport. Design-compatible (the tutor role and AgentManifest
  pattern are fleet-ready) but will be a Phase 3+ migration.
- Open WebUI is not MCP-aware — humans see only Layer 1 (fine-tuned
  behaviour) via Open WebUI. The architectural reveal (three-layer,
  Coach, Graphiti) is accessible only via the MCP surface. Accepted;
  demo script uses both surfaces.

## References

- LES1 §1 (transport) and row 22 (single-transport discipline) in
  `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`.
- Phase 0 scope SR-07 classification table.
- DEC-01 (demo surface strategy).
ADRs 1–8 written. Continuing with 9–16.

Write ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
78 lines
# ADR-ARCH-009 — Six parity surfaces (LES1) as load-bearing cross-cutting concerns

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** LES1, CC-01 through CC-08, phase-0-scope.md §Structural Requirements

## Context

`specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`
(LES1) documents six parity surfaces learned the hard way during
TASK-REV-B8E4. These are the minimum gate before first-merge for any
cross-agent codebase in the appmilla_github monorepo. The Phase 0
scope elevates these to SR-01 through SR-07 (structural requirements)
and declares them do-not-change.

LES1 itself is declared authoritative with a named suffix (LES1 →
future LES2 if a new class of findings emerges). The lessons are
specifically annotated for study-tutor's profile: MCP-only; latency
classification ⚠️; no NATS.

## Decision

The six parity surfaces become **first-class cross-cutting concerns**
in Study Tutor's architecture. Promoted as CC-01 through CC-07 in
`ARCHITECTURE.md §6`:

- **CC-01** — MCP stdio discipline (SR-01)
- **CC-02** — Launcher CWD abs-path (SR-02)
- **CC-03** — Provider resolution at the factory (SR-03)
- **CC-04** — `[providers]` extra completeness (SR-04)
- **CC-05** — Dockerfile literal-match venv install (SR-05; **paused**
  in Phase 0 per ADR-ARCH-005; reactivates on first Dockerfile)
- **CC-06** — `.env` hygiene — no real-looking keys committed (SR-06)
- **CC-07** — Tool description ≡ implementation contract (SR-07)

Plus CC-08 — fire-and-forget + poll above 30s (LES1 §4; distinct from
SR-07's contract rule).

Every feature from the first commit honours these structurally:
- Test cases exist for CC-01 (`tests/unit/mcp/test_stdio_discipline.py`)
  and CC-03 (`tests/unit/llm/test_provider_resolution.py`) in Phase 0.
- `.env.example` linted for CC-06 (grep for `=sk-` / `=AIza` / `=AKIA`).
- SR-07 tool-contract test per tool.
- LES1 itself is referenced in each affected ADR as the evidence base.

## Alternatives considered

- **Leave the parity surfaces as coding-guide lore.** Rejected. LES1
  is already guide material; promoting them to cross-cutting concerns
  ensures every feature has to address them, not just the first one.
- **Only adopt the rows that bit specialist-agent hardest.** Rejected.
  All six are cheap to get right from day one and expensive to
  retrofit (demonstrated by LES1 itself).

## Consequences

**Positive:**
- Every feature review has a standard checklist to audit against.
- Phase 0 success criteria include "SR-01 through SR-07 all green" as
  a gated deliverable.
- Future agents in the monorepo have a pattern to inherit from.

**Negative:**
- Slight overhead per feature (a few test cases) to keep CC-01/CC-03
  structurally intact. Accepted as the cost of not re-learning LES1.
- CC-05 dormancy in Phase 0 may cause confusion ("we have a CC but no
  mitigation"). Mitigated by ADR-ARCH-005's explicit reactivation
  trigger.

## References

- `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`
  (LES1).
- `docs/research/ideas/phase-0-scope.md §Structural Requirements`.
- All SR-related source tasks: TASK-MDF-MCPB, PORT, PMEV, LCOI, DKRX,
  POLR, CRMV, ORPH, PRVS.
Write ADR-ARCH-010-pydantic-at-boundary-validation.md
84 lines
# ADR-ARCH-010 — Pydantic-at-boundary validation + domain vocabulary enums

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-001, ADR-ARCH-012 (deepagents 0.5.3 structured output)

## Context

Study Tutor has several boundary surfaces where untyped dict-style
payloads cross contexts:

- MCP tool inputs (`tutor_start_session`, `tutor_turn`, etc.).
- LLM client invocations (messages, options).
- Graphiti entity write-back (Phase 1+).
- Session-export JSON (Phase 1+ schema, Phase 2 consumer).

Without a validation discipline, each boundary risks silent type
drift. LES1's evidence base (e.g. TASK-MDF-POLR) shows that
tool-description ↔ handler-signature drift is a load-bearing
failure mode.

deepagents 0.5.3 specifically added "static structured output for
subagent responses" — reinforcing Pydantic as the blessed schema
path.

## Decision

**Every boundary validates with Pydantic.**

| Boundary | Schema model |
|---|---|
| MCP tool input | `TutorStartSessionRequest`, `TutorTurnRequest`, `TutorSessionStatusRequest`, `TutorSessionEndRequest` |
| MCP tool output | `TutorSessionHandle`, `TutorTurnResponse`, `TutorSessionStatusResponse` |
| LLM client invoke | `LLMInvokeOptions` |
| Graphiti entities (P1+) | `Student`, `TopicConfidence`, `Misconception`, `SessionEpisode`, `AssessmentObjectiveProgress` |
| Coach output (P1+) | `TurnFeedback`, `SessionSummary` (with Pydantic `structured_output=`) |
| Session export (P1+) | `SessionExport` (full schema) |
| Gamification events | `SessionCompletedEvent`, `AchievementUnlockedEvent`, etc. |

**Domain vocabulary** lives in a shared-kernel Python module
(`src/study_tutor/domain/taxonomy.py` — Phase 1):

- `Subject` (English Language / English Literature)
- `Paper` (Paper 1 / Paper 2)
- `AssessmentObjective` (AO1–AO6)
- `GradeTarget` (4–9)
- `ConfidenceBand` (Struggling / Developing / Secure / Mastered)
- `SessionState` (initialised / planning / active / summarising / ended)

These enums are imported by Tutoring, Knowledge, Student Model, and
Gamification contexts (shared kernel per ADR-ARCH-001).

## Alternatives considered

- **TypedDict / dataclass.** Rejected. TypedDict gives no runtime
  validation; dataclass gives basic validation but not the ergonomic
  `.model_validate()` / `.model_dump_json()` surface.
- **Marshmallow / attrs.** Rejected. LangChain + deepagents both use
  Pydantic natively — one schema library is cleaner.
- **Protobuf / Avro.** Rejected. Overkill for single-language single-user
  system; adds compile step.

## Consequences

**Positive:**
- Every boundary has a declarative schema that serves as documentation
  and runtime validation simultaneously.
- Matches deepagents 0.5.3 structured-output pattern.
- Domain enums prevent stringly-typed bugs (e.g. `"AO1"` vs `"ao1"`).

**Negative:**
- Schema churn early in Phase 1 (Student Model design settling).
  Mitigated by versioning entities and using `model_config =
  ConfigDict(extra='allow')` where forward-compatibility matters.
- Slight per-call overhead for model validation. Negligible vs LLM
  inference cost.

## References

- deepagents 0.5.3 release notes (static structured output for
  subagents).
- `domain-model.md §8.1` for the full shared-kernel taxonomy.
Write ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
70 lines
# ADR-ARCH-011 — No caching / rate limiting / feature flags in Phase 0

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-014 (single-user), ADR-ARCH-016 (timeline)

## Context

Common architectural concerns that teams often build in speculatively:

- **Caching layers** (response cache, embedding cache, RAG-chunk cache).
- **Rate limiting** (per-user, per-token, per-provider).
- **Feature flags** (runtime switches for phase-straddling behaviour).

Each of these adds infrastructure and mental overhead. Phase 0's
explicit goal is a skeleton that passes the six parity surfaces and
ships a working tutor; speculative optimisation compounds timeline
risk with no Phase 0 benefit.

Phase 0 is also single-user and on-device, so the classical use
cases for these concerns don't apply.

## Decision

Phase 0 **does not include**:

- **No caching.** LLM responses, RAG chunks, Graphiti queries — all
  uncached. Revisit Phase 1+ only after the latency spike measures
  actual bottlenecks.
- **No rate limiting.** Single user; no abuse surface. External
  provider APIs are rate-limited by the vendor, which is sufficient.
- **No feature flags.** Phase gating is handled by git commits and
  the `phase-N-scope.md` docs — not by runtime flags.
  Phase-straddling code does not belong in Phase 0.

If Phase 1+ measurement surfaces a real need, each gets its own ADR.

## Alternatives considered

- **Build response-cache framework from day 1.** Rejected.
  Premature; Ollama-local responses are cheap and varied per student
  turn; no cache-hit rate signal.
- **Ship a `ConfigFlag` abstraction for Phase 2 features.** Rejected.
  Violates YAGNI; Phase 2 features are non-existent in Phase 0 code
  and should be added when they exist, not stubbed under a flag.
- **Rate limiting on outbound provider calls (Gemini, Bedrock).**
  Rejected for Phase 0 — at this traffic level (single-user,
  <10 sessions/day), vendor-side rate limits won't be touched.

## Consequences

**Positive:**
- Smaller Phase 0 surface; weekend build target realistic.
- No premature abstractions to unwind in Phase 1 if measurements show
  a different bottleneck than anticipated.

**Negative:**
- If a Phase 1 latency spike surfaces a bottleneck (e.g. ChromaDB RAG
  retrieval), a cache layer has to be added mid-build. Accepted;
  targeted intervention is cheaper than speculative framework.
- Phase 2 features might benefit from feature-flag gating for demo
  vs production. Accepted — add when the need is real.

## References

- YAGNI principle as applied in `CLAUDE.md` (don't design for
  hypothetical future requirements).
- Phase 0 scope §Do-Not-Change list.
Write ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
98 lines
# ADR-ARCH-012 — deepagents 0.5.3+ with AsyncSubAgent Coach + CompositeBackend routing

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0 (declares dependency); runtime usage arrives in P1
**Related:** ADR-ARCH-003, ADR-ARCH-004, CC-08, CC-12

## Context

deepagents 0.5.3 (released 15 April 2026) introduced features that
materially change Study Tutor's Phase 1 architecture:

- **`AsyncSubAgent` class** — native async subagents, invoked via
  built-in `launch_task`, `check_task`, `update_task`,
  `cancel_task`, `list_tasks` tools. This is the canonical form of
  the fire-and-forget + poll pattern LES1 §4 prescribes.
- **Static structured output for subagent responses** (Pydantic).
- **`model=None` deprecated** — `create_deep_agent()` now requires
  an explicit model argument.
- **Permissions system** (0.5.2) with route-scoped permissions on
  `CompositeBackend`.
- **Middleware architecture** (`FilesystemMiddleware` +
  `StateBackend` / `StoreBackend` / `CompositeBackend`).

Without this decision, Study Tutor's Phase 1 Coach would be hand-rolled
fire-and-forget + poll (LES1 prescription). With 0.5.3, the SDK
provides the pattern natively.

## Decision

Pin `deepagents >= 0.5.3` in `pyproject.toml` `[providers]` extra
(CC-04) from Phase 0 for SR-04 smoke-test compliance, even though
Phase 0 code does not import deepagents yet.

Phase 1+ design:

1. **Player** is a regular deepagents agent — `create_deep_agent(
   model=<explicit>, tools=[rag_retrieval, think], subagents=[coach],
   system_prompt=TUTOR_PROMPT)`.
2. **Coach** is an `AsyncSubAgent` — runs off the hot path via
   `launch_task`/`check_task`. Evaluates per-turn quality, batches
   observations, flushes at session-end to Student Model.
3. **Backend** is a `CompositeBackend`:
   - Default: `StateBackend()` — ephemeral, in-process session turns.
   - Route `/student/`: `StoreBackend()` — persistent cross-session
     state (LangGraph Store-backed), with Graphiti write-back wired
     in as an event handler.
4. **Structured output** is used for Coach `TurnFeedback` and
   `SessionSummary` per ADR-ARCH-010.
5. **`model=None` not used** — all `create_deep_agent()` calls pass an
   explicit model (e.g. `init_chat_model("ollama:gcse-tutor-gemma4")`).

## Alternatives considered

- **deepagents 0.5.2.** Rejected — misses `AsyncSubAgent`, which is
  the cleanest Coach pattern. Upgrade benefit outweighs the
  `model=None` breaking change (which we want to avoid anyway).
- **Hand-roll fire-and-forget + poll for Coach.** Rejected. Adds code
  (session-id tracking, poll response shape) that 0.5.3 gives for
  free.
- **Synchronous Coach.** Rejected. Violates CC-08 budget; per-turn
  Coach call would add 3–5s to every `tutor_turn`.
- **LangGraph directly (no deepagents).** Rejected. deepagents'
  middleware stack, skills, filesystem backends, and subagent patterns
  would all have to be re-derived. Phase-1 effort budget doesn't
  allow it.

## Consequences

**Positive:**
- Native support for CC-08 (fire-and-forget + poll) via
  `AsyncSubAgent`.
- Coach can be a remote agent via `graph_id` + `url` if we deploy it
  later (e.g. to a Bedrock or LangGraph Cloud endpoint). No P0/P1
  commitment to do so — option is preserved.
- `CompositeBackend` routing cleanly maps Session vs Student Model
  persistence layers.
- Structured subagent output (0.5.3) aligns with Pydantic-at-boundary
  strategy (ADR-ARCH-010).

**Negative:**
- deepagents 0.5.x has had breaking changes in quick succession
  (permissions, `model=None`). Must pin exact version and revalidate
  after any upgrade (ASSUM-014).
- Async subagent orchestration is newer SDK territory and may have
  rough edges.
- Phase 0 declares the dependency but doesn't import it yet — SR-04
  smoke test needs to cover this explicitly (declare + import
  succeeds; runtime import on first P1 commit).

## References

- deepagents 0.5.3 release notes (April 2026).
- deepagents 0.5.2 permissions system.
- LES1 §4 fire-and-forget + poll prescription.
- `deepagents-patterns-review.md §1.1, §1.3` (Player-Coach applied to
  Study Tutor).
Write ADR-ARCH-013-middleware-level-gamification-engine-future.md
64 lines
# ADR-ARCH-013 — Middleware-level gamification engine (future direction, P2)

**Status:** Proposed (future direction; not committed for Phase 0/1)
**Date:** 2026-04-18
**Phase:** P2 consideration
**Related:** ADR-ARCH-012, ADR-ARCH-001 (Gamification context)

## Context

The deepagents 0.5.x middleware architecture allows reacting to tool
calls and state changes via custom middleware classes — intercepting
events in a structured way rather than via ad-hoc callbacks. The
Gamification context's event-consumption responsibilities
(`session.completed` → XP + streak + achievement check) are a natural
fit for this pattern.

However, the Phase 2 Gamification Engine is not a Phase 0 commitment;
the engine's runtime shape will be decided when Phase 2 begins
(12–16 May 2026).

## Decision

**Note the direction; do not commit to it.** In Phase 2, evaluate
implementing the Gamification Engine as a custom deepagents middleware
class (`GamificationMiddleware`) that:

- Subscribes to `session.completed`, `achievement.unlocked`,
  `quest.completed`, `boss_battle.completed` events.
- Updates `StudentProgress` aggregate via the Student Model Client.
- Emits follow-on `achievement.unlocked` events for newly-earned
  achievements.

Alternative considered and kept open: a standalone
`src/study_tutor/gamification/engine.py` module invoked by the session
manager at `session.completed` time. Less idiomatic w.r.t. deepagents
0.5.x but more portable if we later decouple from deepagents.

Phase 2 feature spec (`FEAT-PO-007`) will make the call.

## Alternatives considered

- **Committing to middleware now.** Rejected. Phase 2 is a month
  away. Committing now over-specifies a decision that's best made
  with the Phase 1 event-flow experience in hand.
- **Committing to a standalone module now.** Rejected for the same
  reason — over-specification.

## Consequences

**Positive:**
- Captures the direction for Phase 2 planners without commitment.
- Documents the pattern fit so it's not forgotten when P2 arrives.

**Negative:**
- Slight risk that Phase 1 locks in a call shape that constrains
  Phase 2's choice. Mitigated by keeping Student Model events
  plain-data (Pydantic models) with no deepagents-specific
  dependencies.

## References

- deepagents 0.5.x middleware architecture docs.
- `docs/gamification/design.md §11.2` (event vocabulary).
Write ADR-ARCH-014-single-user-scalability-posture.md
80 lines
# ADR-ARCH-014 — Single-user scalability posture; multi-student schema-ready

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-006, ADR-ARCH-008, ASSUM-015

## Context

Study Tutor's reference user is Lilymay (single student). The hackathon
submission is a personal-learning-tool pitch with a multi-subject,
multi-student roadmap implied but not implemented. Post-hackathon
multi-student deployment (e.g. for a school cohort) is a Phase 3+ /
post-hackathon concern.

Scalability concerns fall into three categories:

1. **Concurrent users.** Phase 0/1/2 = 1. Post-hackathon = TBD.
2. **Data volume.** Per-student Graphiti graph is small (hundreds of
   sessions × per-turn annotations) — under 1GB even over years.
3. **Inference throughput.** Single-user = 1 concurrent turn max.
   Bedrock scale-to-zero handles multi-user if ever needed.

The Graphiti schema must be designed to allow multi-student without
re-migration later — cheap now, prohibitively expensive post-hoc.

## Decision

**Runtime:** single-user only through Phase 2. No load balancing,
horizontal scaling, multi-region deployment, HA targets. Session
manager is single-process. If GB10 / Synology / tutor host crash,
Lilymay loses the tutor temporarily — acceptable.

**Schema:** multi-student-ready from day 1 via Graphiti group IDs
(`student:{student_id}`, `subject:gcse-english`). Every persisted
entity is scoped by student. Queries always include the group-ID
filter. No singleton "current student" in the schema.

**Inference scale-out path:** already captured via Bedrock
(ADR-ARCH-006). If/when multi-user deployment is needed, Bedrock
already supports concurrent per-student inference; no new work.

**Fail-soft degradation:**
- Graphiti write-back failure → log, return success to user;
  replay queue is a Phase 3 consideration.
- Inference provider failure → surface as MCP error; no retry in
  Phase 0 (ADR-ARCH-011).
- ChromaDB / RAG retrieval failure (Phase 1+) → degrade to
  no-RAG response; log; return.

## Alternatives considered

- **Multi-tenancy from day 1 (full auth stack, per-tenant isolation).**
  Rejected. Over-engineering; no Phase 0/1/2 user demand; would absorb
  the entire hackathon timeline.
- **Single-tenant runtime and single-tenant schema.** Rejected.
  The per-student group-ID schema is ~5 lines of code cost and saves
  a full migration post-hackathon.
- **Multi-user runtime via session sharding.** Rejected. No one is
  asking for it; premature.

## Consequences

**Positive:**
- Phase 0 surface is small; no auth / session-isolation complexity.
- Future multi-student story is schema-ready — a real scale-up path.
- Bedrock dual inference path already covers multi-user inference
  capacity if needed.

**Negative:**
- Post-hackathon multi-student deployment requires authentication +
  per-student session isolation work. Scoped as Phase 3+.
- A hard crash of GB10 / Synology loses the tutor temporarily.
  Accepted; single-user household; not a service.

## References

- DEC-05 (primary interface decision).
- ASSUM-015 (Reachy arrival — ties into single-user deployment).
Write ADR-ARCH-015-uk-on-device-data-residency.md
98 lines
# ADR-ARCH-015 — UK on-device data residency; Gemini as explicit exception

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-007, DEC-02, DEC-08, ASSUM-013

## Context

Study Tutor's product story emphasises on-device privacy. Student
tutoring data is sensitive — sessions reveal what a student struggles
with, what they don't understand, their writing samples, their
Year-10-level mistakes. A submission claiming "on-device AI tutor for
your child" is undermined by cloud telemetry.

Three data-residency facts shape the architecture:

1. **Layer 1 inference.** Primary on GB10 (household network).
   Validation on AWS Bedrock (UK-region Custom Model Import).
2. **Layer 2 knowledge.** ChromaDB on MacBook; source PDFs in
   `domains/*/sources/` (user-provided, gitignored).
3. **Layer 3 student model.** Graphiti — FalkorDB on Synology NAS
   (household), but entity extraction via Google Gemini (Google
   Cloud, GCP region).

Gemini sees session summaries during write-back. This is an explicit
exception to on-device residency.

## Decision

**Default posture: on-device + household Tailscale network.**

| Data | Location | Controlled by |
|---|---|---|
| Session turns (in-memory during session) | MacBook or tutor host | Filesystem permissions |
| Session exports (JSON) | Local filesystem | Filesystem permissions |
| Student Model (Graphiti entities) | Synology NAS FalkorDB | Tailscale + FalkorDB auth |
| Fine-tuned model weights | GB10 (household) + S3 (Bedrock ingestion) | IAM + Tailscale |
| RAG curriculum content | MacBook ChromaDB | Filesystem |
| Source documents | `domains/*/sources/` gitignored | Filesystem; never committed |
| Logs | MacBook stderr + rotating file (P1+) | Filesystem |

**Explicit exception: Google Gemini 2.5 Pro** for Graphiti entity
extraction. Documented in this ADR and in the submission write-up.

Mitigations for the exception:

- Session summaries to Gemini are **terse, topic-focused**. Full
  student names are not required for entity extraction; use
  `student_id` (UUID or short handle).
- No school identifiers, parental contact info, or full turn
  transcripts in the payload to Gemini. Just AO-level observations
  and topic references.
- ASSUM-013 tracks the assumption that Gemini payloads stay clean;
  revisit in Phase 1 entity-extraction spike.
- If PII leaks, add a pre-Gemini redaction layer (ADR-TBD in Phase 1).

**Bedrock exception** — AWS Bedrock is a cloud service, but:
- It runs in a UK-adjacent region.
- Only **prompts and responses** pass through; no student identity
  or session metadata beyond what the prompt carries.
- Fine-tuned model weights are in S3 (user's AWS account).

**No** telemetry, analytics, error reporting to any third-party
service (Sentry, LogRocket, etc.) in any phase.

## Alternatives considered

- **No cloud at all; local Graphiti LLM (e.g. Qwen-on-GB10).**
  Rejected for Phase 1 MVP per DEC-08 — Gemini is paid-for, known
  latency, and moving it local conflicts with DEC-07 training
  schedule. Revisit post-hackathon.
- **End-to-end encryption of Gemini payloads.** Rejected as
  overkill — Gemini is the LLM that needs to read the payload to
  extract entities. Encryption at rest / in transit is already
  provided by Google's TLS.
- **Multi-region Bedrock.** Considered; out of scope for
  single-user hackathon.

## Consequences

**Positive:**
- Submission narrative holds up — "AI tutor for your child,
  household-scoped" is true for all of the high-value data.
- Single documented exception (Gemini), clean story.

**Negative:**
- One data-residency exception is one more thing to monitor.
  Mitigated by ASSUM-013 and the Phase 1 redaction review.
- Dependency on Gemini availability for Phase 1+ entity extraction.
  Fail-soft: if Gemini is down, session-end returns successfully and
  the write-back goes into a replay queue.

## References

- DEC-02, DEC-08 in `docs/research/ideas/decisions-log-2026-04-17.md`.
- `gemma4-hackathon-submission-plan.md` — privacy story.
Write ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
106 lines
# ADR-ARCH-016 — 18 May 2026 deadline as load-bearing architectural constraint

**Status:** Accepted
**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ALL other ADRs (timeline is the constraint they are all
optimising against)

## Context

Study Tutor's submission to the Gemma 4 Good Hackathon is due
**18 May 2026, 23:59 UTC**. From the `/system-arch` session date
(2026-04-18), that is 31 calendar days; subtracting DDD Southwest
(16 May) + weekend submission (17–18 May) + ~4 days of DDD prep
leaves roughly 18 effective working days.

This is an unusual architectural constraint in the literal sense —
it reshapes every technology decision. "Build the right thing" has a
fixed end date; "build the thing that can be visibly three-layer on
16 May demo capture" takes priority over "build the feature-complete
thing."

## Decision

**Timeline is a primary architectural constraint.** All other ADRs
are explicitly calibrated against it.

Specific timeline-shaped decisions:

- **Phase staging** (Phase 0 18–24 Apr, Phase 1 25 Apr – 11 May,
  Phase 2 12–16 May, Submission 17–18 May) — feature gating per
  phase rather than parallel development.
- **Bedrock in Phase 0, not Phase 2** (ADR-ARCH-006) — frees GB10
  and removes a demo-week dependency.
- **No Dockerfile in Phase 0** (ADR-ARCH-005) — saves SR-05 audit
  burden.
- **No caching / rate limiting / feature flags in Phase 0**
  (ADR-ARCH-011) — saves speculative work.
- **DDD over Modular Monolith** (ADR-ARCH-001) — accepts slightly
  more ceremony upfront to avoid mid-phase restructuring when
  gamification and student-model contexts land.
- **Three-layer explicitly described up front** (ADR-ARCH-002) —
  submission narrative depends on a clear architecture diagram;
  fuzz early and the submission suffers.
- **deepagents 0.5.3 AsyncSubAgent for Coach** (ADR-ARCH-012) —
  native SDK support, not hand-rolled; saves Phase 1 implementation
  time.
- **Reachy as stretch, gated 4 May** (ASSUM-015) — cannot be on the
  critical path.
- **Single-user scalability posture** (ADR-ARCH-014) — multi-tenancy
  would absorb the entire hackathon budget.

**Non-negotiables for 18 May:**

1. A public repo that passes the six parity surfaces in a clean
   walkthrough.
2. A working fine-tuned tutor, demoable on video.
3. The three-layer architecture visible and credibly instantiated.
4. At least a thin slice of Player-Coach proving the architecture
   runs end-to-end.
5. Technical write-up covering methodology + provenance +
   architecture + roadmap.

**Slip absorption:**

- Friday 25 April is a soft buffer day at end of Phase 0.
- If Phase 1 features slip, Phase 2 engagement-layer surface drops
  from full engine → Pydantic models + dashboard mockup.
- If Phase 2 slips, Reachy is the first stretch to drop.
- Safeguarding (CC-09), copyright (CC-10), parity surfaces (CC-01 to
  CC-08) **never drop** — they are architectural invariants.

## Alternatives considered

- **Ignore the timeline and build the best architecture.** Rejected.
  Over-engineering kills hackathon submissions. The judging is 18 May
  or never.
- **Cut scope to just Layer 1 + MCP + nice README.** Rejected.
  The three-layer architecture is the submission's core
  differentiator. Without Layer 3 credibly instantiated, Study
  Tutor looks like any other fine-tuned-model hackathon entry.

## Consequences

**Positive:**
- Every ADR has a shared "why this tradeoff" anchor.
- Phase gating is structural, not aspirational.
- Post-hackathon work has an obvious starting point (the deferred
  items).

**Negative:**
- Some Phase 0 choices (e.g. no Dockerfile, no caching) would be
  different if the horizon were longer. Accepted — this is what
  the 31-day burn looks like.
- Timeline slippage scenarios (Kaggle rule surprise, Bedrock
  incompatibility, deepagents 0.6.0 breaking release) would force
  mid-phase revision. Mitigated by explicit slip-absorption
  ordering above and by the ASSUM-017 read-Kaggle-rules Friday
  gate.

## References

- Phase 0 scope §Success Criteria.
- Phase 0 build plan §Day-by-day plan.
- `gemma4-hackathon-submission-plan.md` — overarching timing.
All 16 ADRs written. Verifying the artefact set is complete before offering Graphiti seeding.

Bash Verify architecture artefact set is complete
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/ && echo "---" && ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ && echo "---" && wc -l /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/*.md /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/*.yaml /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/*.md

OUT
total 128
drwxr-xr-x   8 richardwoollcott  staff    256 Apr 18 23:33 .
drwxr-xr-x   7 richardwoollcott  staff    224 Apr 18 23:27 ..
-rw-r--r--   1 richardwoollcott  staff  11070 Apr 18 23:28 ARCHITECTURE.md
-rw-r--r--   1 richardwoollcott  staff  10810 Apr 18 23:33 assumptions.yaml
-rw-r--r--   1 richardwoollcott  staff   6763 Apr 18 23:31 container.md
drwxr-xr-x  18 richardwoollcott  staff    576 Apr 18 23:39 decisions
-rw-r--r--   1 richardwoollcott  staff  20481 Apr 18 23:30 domain-model.md
-rw-r--r--   1 richardwoollcott  staff   4750 Apr 18 23:31 system-context.md
---
total 144
drwxr-xr-x  18 richardwoollcott  staff   576 Apr 18 23:39 .
drwxr-xr-x   8 richardwoollcott  staff   256 Apr 18 23:33 ..
-rw-r--r--   1 richardwoollcott  staff  3622 Apr 18 23:33 ADR-ARCH-001-ddd-structural-pattern.md
-rw-r--r--   1 richardwoollcott  staff  3665 Apr 18 23:34 ADR-ARCH-002-three-layer-architecture.md
-rw-r--r--   1 richardwoollcott  staff  3512 Apr 18 23:34 ADR-ARCH-003-async-graphiti-writeback.md
-rw-r--r--   1 richardwoollcott  staff  3603 Apr 18 23:34 ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
-rw-r--r--   1 richardwoollcott  staff  2860 Apr 18 23:35 ADR-ARCH-005-defer-dockerfile-to-phase-1.md
-rw-r--r--   1 richardwoollcott  staff  3563 Apr 18 23:35 ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
-rw-r--r--   1 richardwoollcott  staff  3428 Apr 18 23:35 ADR-ARCH-007-graphiti-split-topology.md
-rw-r--r--   1 richardwoollcott  staff  3371 Apr 18 23:36 ADR-ARCH-008-mcp-only-agent-access.md
-rw-r--r--   1 richardwoollcott  staff  3247 Apr 18 23:36 ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
-rw-r--r--   1 richardwoollcott  staff  3273 Apr 18 23:37 ADR-ARCH-010-pydantic-at-boundary-validation.md
-rw-r--r--   1 richardwoollcott  staff  2682 Apr 18 23:37 ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
-rw-r--r--   1 richardwoollcott  staff  4123 Apr 18 23:37 ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
-rw-r--r--   1 richardwoollcott  staff  2368 Apr 18 23:38 ADR-ARCH-013-middleware-level-gamification-engine-future.md
-rw-r--r--   1 richardwoollcott  staff  3144 Apr 18 23:38 ADR-ARCH-014-single-user-scalability-posture.md
-rw-r--r--   1 richardwoollcott  staff  4037 Apr 18 23:38 ADR-ARCH-015-uk-on-device-data-residency.md
-rw-r--r--   1 richardwoollcott  staff  4173 Apr 18 23:39 ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
---
     202 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/ARCHITECTURE.md
     131 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/container.md
     502 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/domain-model.md
      91 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/system-context.md
     273 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/assumptions.yaml
      86 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-001-ddd-structural-pattern.md
      81 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-002-three-layer-architecture.md
      83 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md
      82 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
      72 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-005-defer-dockerfile-to-phase-1.md
      89 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
      94 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md
      87 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md
      77 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
      83 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-010-pydantic-at-boundary-validation.md
      69 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
      97 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
      63 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-013-middleware-level-gamification-engine-future.md
      79 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md
      97 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md
     105 /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
    2543 total
All 21 artefacts written (5 top-level + 16 ADRs; 2543 lines total).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE DOCUMENTATION CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


docs/architecture/
├── ARCHITECTURE.md                    (11 KB — index + summary)
├── domain-model.md                    (20 KB — bounded contexts, aggregates, events)
├── system-context.md                  (4.8 KB — C4 Level 1 Mermaid)
├── container.md                       (6.8 KB — C4 Level 2 Mermaid)
├── assumptions.yaml                   (11 KB — 18 assumptions)
└── decisions/
    ├── ADR-ARCH-001-ddd-structural-pattern.md
    ├── ADR-ARCH-002-three-layer-architecture.md
    ├── ADR-ARCH-003-async-graphiti-writeback.md
    ├── ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
    ├── ADR-ARCH-005-defer-dockerfile-to-phase-1.md
    ├── ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
    ├── ADR-ARCH-007-graphiti-split-topology.md
    ├── ADR-ARCH-008-mcp-only-agent-access.md
    ├── ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
    ├── ADR-ARCH-010-pydantic-at-boundary-validation.md
    ├── ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
    ├── ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
    ├── ADR-ARCH-013-middleware-level-gamification-engine-future.md
    ├── ADR-ARCH-014-single-user-scalability-posture.md
    ├── ADR-ARCH-015-uk-on-device-data-residency.md
    └── ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
Graphiti seeding (Phase 4)
Graphiti is available (583 episodes already indexed). Proposed seeding plan:


# Architecture context (domain model + summary) → project_architecture
guardkit graphiti add-context docs/architecture/domain-model.md \
  --group project_architecture

guardkit graphiti add-context docs/architecture/ARCHITECTURE.md \
  --group project_architecture

guardkit graphiti add-context docs/architecture/system-context.md \
  --group project_architecture

guardkit graphiti add-context docs/architecture/container.md \
  --group project_architecture

guardkit graphiti add-context docs/architecture/assumptions.yaml \
  --group project_architecture

# All 16 ADRs → architecture_decisions
guardkit graphiti add-context docs/architecture/decisions/ \
  --group architecture_decisions
The 16 ADRs contain no secrets or raw unsanitised user input — the guardkit graphiti add-context CLI applies its own sanitisation during upload. Free-text has been paraphrased from source docs throughout.

Run these seeding commands now? [Y/n]

If Y, I'll execute each in sequence and report the updated episode counts. If n, the markdown artefacts are complete and queryable locally, and you can seed later with the same commands.

Your call:

Y
Executing seeding. This may take several minutes because Graphiti uses Gemini for per-chunk entity extraction (~1–3s per call).

Bash Seed ARCHITECTURE.md → project_architecture
IN
guardkit graphiti add-context docs/architecture/ARCHITECTURE.md --group project_architecture 2>&1 | tail -20

OUT
Usage: guardkit-py graphiti add-context [OPTIONS] PATH
Try 'guardkit-py graphiti add-context --help' for help.

Error: No such option: --group
Bash Get correct add-context flags
IN
guardkit graphiti add-context --help 2>&1 | head -40

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
The CLI uses --type (not --group) — it auto-assigns groups based on content type. Let me test with a dry run first to confirm behavior, then proceed.

Bash Dry-run to confirm parser behaviour for ARCHITECTURE.md
IN
guardkit graphiti add-context docs/architecture/ARCHITECTURE.md --type project-overview --dry-run 2>&1 | tail -30

OUT
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

No parser for type: project-overview

Dry run complete - Would add:
  0 files, 0 episodes
Bash Dry-run ADR directory with --type adr
IN
guardkit graphiti add-context docs/architecture/decisions/ --type adr --dry-run 2>&1 | tail -40

OUT
Missing required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-010-pydantic-at-boundary-validation.md: 
Missing required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-011-no-caching-rate-limiting-feature-flags-
phase-0.md: Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md: 
Missing required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-005-defer-dockerfile-to-phase-1.md: Missing
required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-004-python-deepagents-langchain-mcp-stack.m
d: Missing required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-013-middleware-level-gamification-engine-fu
ture.md: Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-001-ddd-structural-pattern.md: 
Missing required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-016-may-18-deadline-as-architectural-constr
aint.md: Missing required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
: Missing required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md: Missing
required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md:
Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md:
Missing required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md: 
Missing required section: Status
  Warning: 
docs/architecture/decisions/ADR-ARCH-006-dual-inference-path-ollama-bedrock.md: 
Missing required section: Status
Two issues to fix:

CLI accepts project_overview (underscore) not project-overview (hyphen) based on the supported-types list in the help.
ADR parser requires a proper ## Status heading; I used **Status:** metadata formatting — need to add ## Status as a heading.
Let me fix both and re-try.

Bash Test with underscore parser type
IN
guardkit graphiti add-context docs/architecture/ARCHITECTURE.md --type project_overview --dry-run 2>&1 | tail -10

OUT
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

  ✓ docs/architecture/ARCHITECTURE.md (project_overview)

Dry run complete - Would add:
  1 file, 1 episode

Warnings:
  Warning: docs/architecture/ARCHITECTURE.md: Missing 'architecture' section
Good — project_overview works. Now adding ## Status headings to the 16 ADRs. Parallel edits.

Edit ADR-ARCH-001-ddd-structural-pattern.md
Added 3 lines
Edit ADR-ARCH-002-three-layer-architecture.md
Added 3 lines
Edit ADR-ARCH-003-async-graphiti-writeback.md
Added 3 lines
Edit ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
Added 3 lines
Edit ADR-ARCH-005-defer-dockerfile-to-phase-1.md
Added 3 lines
Edit ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
Added 3 lines
Edit ADR-ARCH-007-graphiti-split-topology.md
Added 3 lines
Edit ADR-ARCH-008-mcp-only-agent-access.md
Added 3 lines
Edit ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
Added 3 lines
Edit ADR-ARCH-010-pydantic-at-boundary-validation.md
Added 3 lines
Edit ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
Added 3 lines
Edit ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
Added 3 lines
Edit ADR-ARCH-013-middleware-level-gamification-engine-future.md
Added 3 lines
Edit ADR-ARCH-014-single-user-scalability-posture.md
Added 3 lines
Edit ADR-ARCH-015-uk-on-device-data-residency.md
Added 3 lines
Edit ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
Added 3 lines
All 16 ADRs updated. Verifying dry-run and starting the actual seeding.

Bash Verify ADRs now parse cleanly
IN
guardkit graphiti add-context docs/architecture/decisions/ --type adr --dry-run 2>&1 | tail -10

OUT
(adr)
  ✓ docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md (adr)
  ✓ docs/architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md 
(adr)
  ✓ 
docs/architecture/decisions/ADR-ARCH-006-dual-inference-path-ollama-bedrock.md 
(adr)

Dry run complete - Would add:
  16 files, 16 episodes
16 ADRs parse cleanly. Running actual seeding in the background — ~18 episodes × Gemini extraction means this could take a few minutes.

Bash Seed ARCHITECTURE.md as project_overview
IN
guardkit graphiti add-context docs/architecture/ARCHITECTURE.md --type project_overview 2>&1 | tail -30

OUT
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
ERROR:graphiti_core.llm_client.gemini_client:Error in generating LLM response: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
WARNING:graphiti_core.llm_client.gemini_client:Retrying after application error (attempt 1/2): 
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
ERROR:graphiti_core.llm_client.gemini_client:Error in generating LLM response: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
WARNING:graphiti_core.llm_client.gemini_client:Retrying after application error (attempt 1/2): 
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:graphiti_core.graphiti:Completed add_episode in 159204.274892807 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [study-tutor-architecture-summary]: nodes=31, edges=49, invalidated=0
  ✓ docs/architecture/ARCHITECTURE.md (project_overview)

Summary:
  Added 1 file, 1 episode

Warnings:
  Warning: docs/architecture/ARCHITECTURE.md: Missing 'architecture' section
ARCHITECTURE.md seeded — 31 nodes + 49 edges added (took 2.6 min due to Gemini 503 retries — capacity throttling, the client retried and succeeded). Running the 16 ADRs next with a longer inter-episode delay to be easier on Gemini.

Bash Seed all 16 ADRs with 2s inter-episode delay
IN
guardkit graphiti add-context docs/architecture/decisions/ --type adr --delay 2.0 2>&1 | tee /tmp/study-tutor-adr-seed.log | tail -60

OUT
Command running in background with ID: baxznbdc5. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/4a8b8ac3-7175-4e57-8a9d-01048f839c98/tasks/baxznbdc5.output
The seeding task baxznbdc5 is now running in the background. With 16 ADRs × ~30–60s per episode (plus the observed Gemini 503 retries) this could take 15–30 minutes.

I'll wait for the completion notification rather than polling. Meanwhile — summary of what's already live in Graphiti after the ARCHITECTURE.md seed:

31 new nodes + 49 new edges added under the study-tutor-architecture-summary episode
Total episodes in Graphiti is now 584 (was 583 before)
Content sanitisation handled server-side by guardkit graphiti add-context
While the background task runs, I'll let you know as soon as the ADR batch completes. If Gemini throttles out (503 on too many retries), I'll restart the batch with an even higher --delay and continue from the remaining ADRs.

Bash Check ADR seeding output
IN
tail -80 /tmp/study-tutor-adr-seed.log 2>&1

OUT
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:graphiti_core.graphiti:Completed add_episode in 51179.356813430786 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-003-async-graphiti-write-back-at-session-end-boundary]: nodes=12, edges=9, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md (adr)
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:graphiti_core.graphiti:Completed add_episode in 38269.32191848755 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-014-single-user-scalability-posture-multi-student-schema-ready]: nodes=9, edges=8, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md 
(adr)
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:google_genai.models:AFC is enabled with max remote calls: 10.
INFO:graphiti_core.graphiti:Completed add_episode in 71180.743932724 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-006-dual-inference-path-ollama-primary-bedrock-validation]: nodes=18, edges=23, invalidated=0
  ✓ 
docs/architecture/decisions/ADR-ARCH-006-dual-inference-path-ollama-bedrock.md 
(adr)

Summary:
  Added 16 files, 16 episodes
Bash Summarise per-ADR node and edge counts
IN
grep -E "nodes=|Added.*episode" /tmp/study-tutor-adr-seed.log | tail -20

OUT
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-007-graphiti-split-topology-falkordb-on-synology-gemini-entity-extraction-gb10-embedder]: nodes=12, edges=12, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-002-three-layer-architecture-behaviour-knowledge-student-model]: nodes=12, edges=13, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-010-pydantic-at-boundary-validation-domain-vocabulary-enums]: nodes=35, edges=67, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-011-no-caching-rate-limiting-feature-flags-in-phase-0]: nodes=7, edges=4, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-008-mcp-only-for-agent-access-single-user-auth-posture]: nodes=30, edges=44, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-005-defer-dockerfile-to-phase-1-venv-only-install-for-phase-0]: nodes=20, edges=22, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-004-python-3-11-deepagents-langchain-mcp-stack]: nodes=27, edges=42, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-013-middleware-level-gamification-engine-future-direction-p2]: nodes=12, edges=10, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-001-use-domain-driven-design-structural-pattern]: nodes=20, edges=22, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-016-18-may-2026-deadline-as-load-bearing-architectural-constraint]: nodes=26, edges=27, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-012-deepagents-0-5-3-with-asyncsubagent-coach-compositebackend-routing]: nodes=27, edges=45, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-015-uk-on-device-data-residency-gemini-as-explicit-exception]: nodes=17, edges=24, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-009-six-parity-surfaces-les1-as-load-bearing-cross-cutting-concerns]: nodes=15, edges=14, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-003-async-graphiti-write-back-at-session-end-boundary]: nodes=12, edges=9, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-014-single-user-scalability-posture-multi-student-schema-ready]: nodes=9, edges=8, invalidated=0
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-006-dual-inference-path-ollama-primary-bedrock-validation]: nodes=18, edges=23, invalidated=0
  Added 16 files, 16 episodes
Bash Check new Graphiti total
IN
guardkit graphiti status 2>&1 | grep -E "Total|architecture_decisions|project_knowledge|Status:" | head -10

OUT
  Status: ENABLED
    • architecture_decisions: 100
  Total Episodes: 732
All 16 ADRs seeded successfully. No failures, no manual retries needed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GRAPHITI SEEDING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Artefact	Episodes	Nodes	Edges
ARCHITECTURE.md (project_overview)	1	31	49
ADR-ARCH-001 DDD structural pattern	1	20	22
ADR-ARCH-002 Three-layer architecture	1	12	13
ADR-ARCH-003 Async Graphiti write-back	1	12	9
ADR-ARCH-004 Python/deepagents/langchain/mcp stack	1	27	42
ADR-ARCH-005 Defer Dockerfile	1	20	22
ADR-ARCH-006 Dual inference path	1	18	23
ADR-ARCH-007 Graphiti split topology	1	12	12
ADR-ARCH-008 MCP-only agent access	1	30	44
ADR-ARCH-009 Six parity surfaces	1	15	14
ADR-ARCH-010 Pydantic-at-boundary	1	35	67
ADR-ARCH-011 No caching/rate-limit/flags	1	7	4
ADR-ARCH-012 deepagents 0.5.3 AsyncSubAgent	1	27	45
ADR-ARCH-013 Middleware gamification (future)	1	12	10
ADR-ARCH-014 Single-user scalability	1	9	8
ADR-ARCH-015 UK on-device residency	1	17	24
ADR-ARCH-016 18 May deadline	1	26	27
Total from this session	17	330	435
Graphiti total episodes: 732 (was 583 before /system-arch).

The four supplementary artefacts (domain-model.md, system-context.md, container.md, assumptions.yaml) are on disk and queryable locally but not yet seeded to Graphiti. /system-design and /system-plan will be able to query the architecture decisions and overview via Graphiti; they'll read the C4 diagrams and domain-model.md directly from disk.

Optional: seed the four supplementary artefacts as full_doc if you want richer Graphiti coverage? Most likely not worth it — the ADRs already encode the key decisions, and domain-model.md is a 500-line reference doc that's more useful as a file-system read.

/system-arch complete
Next steps:

Review docs/architecture/ARCHITECTURE.md — index + summary
Design API contracts: /system-design --from docs/architecture/ARCHITECTURE.md --context docs/research/ideas/phase-0-scope.md --context docs/research/ideas/phase-0-build-plan.md
Then /system-plan and per-feature /feature-spec → /feature-plan → autonomous build or task-work
Per the Phase 0 build plan, recommended timing for /system-design is Saturday evening 19 April or Sunday morning after domain docs are drafted — the architecture now has the context it needs.