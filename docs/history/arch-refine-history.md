# /arch-refine — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /arch-refine — 2026-07-03T05:53:02Z

### Prompt

```
/arch-refine \
  --target docs/architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md \
  --context docs/research/ideas/student-model-postgres-migration-scope-and-build-plan.md \
  --context docs/gamification/design.md
```

### Assistant response

I'll execute the `/arch-refine` command. Since you've passed `--target` (a direct ADR path), I'll skip semantic disambiguation but still confirm the selection before any changes. Let me start by loading the target ADR, the context files, and checking Graphiti availability.

Both context files and the target ADR are loaded. Before I present the selection and confirmation gate, I need the current state of the ADRs this refinement will cascade into, plus any C4 diagrams that the re-review gate would cover. Let me gather those.

This is the **G-ADR ratification gate** from the build plan §5a — and my read of the surrounding ADRs surfaces some important nuances I need to reflect accurately before touching anything. Let me pull the C4 diagrams and the index so my impact analysis and the mandatory C4 re-review gate are concrete.

I now have the full dependency picture. This invocation is the **G-ADR ratification gate** from the build plan (§5a / §9 Step 1), and my read of the surrounding ADRs surfaces several things that change how it should be applied. Let me lay them out before touching anything — the command requires explicit confirmation before applying changes.

---

## Graphiti availability (Tier 1)

`.guardkit/graphiti.yaml` → `enabled: true` (FalkorDB `whitestocks:6379`, vLLM `qwen-graphiti`). So config-level `graphiti_available = true`, but connectivity is unverified and this is the very stack ADR-023 decommissions. I'll run the Tier‑2 check only if you opt to seed at the end (Phase 8) — and flag the irony of seeding a "drop Graphiti" ADR *into* Graphiti then.

---

## ✓ SELECTED: ADR-ARCH-023 — drop Graphiti/FalkorDB, adopt study-tutor-owned Postgres (JSONB)

**Current state:** `Status: Proposed` (dated 2026-07-02). Header already declares `Supersedes: ADR-ARCH-003, -007, -019` and "Retires the CC-13 invariant of ADR-ARCH-021."

## This is a ratification, not a supersession — the key deviation

The command's literal Phase 3 mints a *new* ADR that supersedes the target. **That is wrong here.** ADR-023 is *already* the superseding record; minting a new one would create a nonsensical **ADR-025 that supersedes ADR-023** (and 024 already exists). The gate's actual job (§5a/§9): flip **023 → Accepted** and make its declared supersessions effective.

## Change-set I propose to apply

| ADR | Current | Action | Note |
|---|---|---|---|
| **023** (target) | Proposed | → **Accepted** | ratify in place |
| **007** Graphiti split topology | Accepted | → **Superseded by 023** | FalkorDB/Gemini/embedder split is dropped |
| **019** async write-back every point | Accepted | → **Superseded by 023** | D2 reverts writes to synchronous |
| **003** async write-back session-end | **already Superseded by 019** | **no-op** | leave pointing at 019 — preserves the 003→019→023 chain; repointing to 023 would erase 019 from history |
| **021** typed-entity seed | Accepted | **annotate only** | its CC-13 single-call-site invariant is retired by 023; ADR stays Accepted |
| **022** corpus retrieval | Proposed | **out of scope** | build plan §5a: ratify on its own track; doesn't gate SMP |

> Note: the build plan says "flip 003/007/019." 003 is already superseded, so it's a no-op — I've reflected that above.

## ⚡ Impact analysis

**🔍 C4 re-review gate — TRIGGERED (mandatory).** Removing FalkorDB + Gemini-as-extractor and swapping `student_model` from `graphiti-core` to a Postgres client is a topology change:
- **system-context.md (L1):** removes `FalkorDB`, `Gemini (entity-extraction)`; retargets `Reachy → reads state` and the main-system blurb ("Graphiti student model") to Postgres. Embedder stays (ChromaDB).
- **container.md (L2):** `student_model` tech `graphiti-core → StudentStore/Postgres`; drops `falkor`/`gemini` externals, adds a Postgres `ContainerDb`; Coach→student_model write flips from "async fire-and-forget per CC-13" to **synchronous**; MCP tool-description strings lose the CC-13/019 fire-and-forget notes.

⚠️ **ADR-023 under-documented this** — unlike ADR-019 and ADR-022 (which each carry a "C4 re-review status: unchanged" section), ADR-023 has none, yet it's the one that *does* change topology. I'll regenerate both diagrams and present them for mandatory [A/R/C] approval after you confirm scope.

**Downstream flagged stale** (reframe now or defer to `/system-design`): `docs/gamification/design.md` (§2/§6/§11 "maintained in Graphiti"), `docs/planning/feature-roadmap.md` (FEAT-PH1-001), `docs/architecture/domain-model.md` (write-back narrative), `ADR-ARCH-022` parenthetical, and `ARCHITECTURE.md` (index is stale — lists only 16 ADRs through 019, wrong statuses).

**Excluded from this gate regardless** — source (`async_write.py`, `queries.py`, `graphiti_client.py`, `episodes.py`, `seed_uuids.py`, `student_model.py`), `pyproject.toml`, `.env`, seed script. ADR-023 D5 and the build plan defer these to the **W1/W3 FEAT-SMP builds**; a ratification must not touch implementation.

Two decisions before I proceed:

Approach confirmed (ratify in place) and scope confirmed (full reconciliation). One mandatory gate remains before any file is written: the **C4 re-review**. Per the command, revised L1 + L2 must be approved and `[C]ancel` here discards *everything* — so nothing is written until you approve these.

Here are the regenerated diagrams.

---

### 🔍 C4 Level 1 — System Context (REVISED — ADR-ARCH-023)

```mermaid
C4Context
    title Study Tutor — System Context (C4 Level 1) — REVISED (ADR-ARCH-023)

    Person(student, "Lilymay (Student)", "Year 10, AQA 8700+8702. Uses Open WebUI daily for revision.")
    Person(agent, "AI Agent", "Claude Desktop (P0); future Ship's Computer fleet via Jarvis.")
    Person(developer, "Developer / Judge", "Clones public repo, follows README quickstart on clean machine.")
    Person(parent, "Parent / Teacher", "Queries progress via Reachy Mini voice interface. [P2 stretch]")

    System(studytutor, "Study Tutor", "Three-layer GCSE English AI tutor — fine-tuned behaviour + RAG knowledge + Postgres student model. MCP + CLI + Open WebUI surfaces.")

    System_Ext(ollama, "Ollama on GB10", "Local inference — fine-tuned Gemma 4 31B Q4_K_M. Tailscale-reachable. [P0 primary]")
    System_Ext(bedrock, "AWS Bedrock", "Custom Model Import — scale-to-zero Gemma 4 31B. Frees GB10 for training. [P0 validation, P1+ primary for demo week]")
    System_Ext(s3, "AWS S3", "Model artefact storage — appmilla-study-tutor-bedrock-models.")
    System_Ext(postgres, "Postgres (study-tutor-owned NAS)", "Student-model store — JSONB; per-student topic confidence, XP, streaks, achievements, sessions. Own instance, port 5433, nightly pg_dump. [P1+]")
    System_Ext(embedder, "GB10 Embedder", "nomic-embed-text-v1.5 on :8001 — ChromaDB corpus embeddings. [P1+]")
    System_Ext(openwebui, "Open WebUI (GB10)", "Lilymay's primary chat interface. OpenAI-compatible. Unchanged from today.")
    System_Ext(litellm, "LiteLLM Proxy (GB10)", "OpenAI-compatible proxy routing Open WebUI → Bedrock when GB10 is training. [P0 validation]")
    System_Ext(claude, "Claude Desktop", "MCP stdio client — architecture-reveal demo + operator usage.")
    System_Ext(reachy, "Reachy Mini 'Scholar'", "Embodied companion — reads Postgres student-model state, narrates progress. [P2 stretch, gated 4 May]")

    Rel(student, openwebui, "Chats with", "HTTPS (LAN)")
    Rel(openwebui, ollama, "Calls", "Ollama API [P0]")
    Rel(openwebui, litellm, "Calls", "OpenAI-compatible [P0 validation, P1+]")
    Rel(litellm, bedrock, "Routes to", "AWS SDK")

    Rel(agent, claude, "Invokes via")
    Rel(claude, studytutor, "Calls tools", "MCP JSON-RPC / stdio")

    Rel(developer, studytutor, "Installs + runs", "CLI / README walkthrough")

    Rel(studytutor, ollama, "Inference calls", "HTTP over Tailscale [P0 primary]")
    Rel(studytutor, bedrock, "Inference calls", "AWS SDK [P0 validation]")
    Rel(studytutor, postgres, "Student-model R/W", "SQL / asyncpg over Tailscale [P1+]")
    Rel(studytutor, embedder, "Embed text", "OpenAI-compatible HTTP [P1+]")

    Rel(bedrock, s3, "Loads weights from")

    Rel(parent, reachy, "Asks about progress", "Voice [P2]")
    Rel(reachy, postgres, "Reads state from", "SQL [P2]")
```

**Δ L1:** removed `FalkorDB` + `Google Gemini (Graphiti entity-extraction)` and the `studytutor → gemini` edge; added `Postgres (study-tutor-owned NAS)`; retargeted `studytutor → postgres` and `reachy → postgres`; embedder reworded to ChromaDB-only; main-system blurb now "Postgres student model." **Privacy note:** dropping the Gemini extractor *closes* ADR-015's on-device-residency exception — learner data no longer leaves for extraction. **Node count → 14** (4 persons + 1 system + 9 external).

---

### 🔍 C4 Level 2 — Container (REVISED — ADR-ARCH-023)

```mermaid
C4Container
    title Study Tutor — Container Diagram (C4 Level 2) — REVISED (ADR-ARCH-023)

    Person(agent, "AI Agent (Claude Desktop)", "Invokes tutor via MCP tools")
    Person(developer, "Developer / Judge", "CLI + README walkthrough")
    Person(student, "Lilymay", "Uses Open WebUI (external to containers shown)")

    System_Boundary(studytutor, "Study Tutor") {
        Container(wrapper, "Bash MCP Wrapper", "bash / scripts/mcp-wrapper.sh", "Absolute cd + env load + exec — SR-02. Launched by Claude Desktop.")
        Container(cli, "CLI Entrypoint", "Python / Click", "study-tutor serve --role tutor --transport stdio. Banner→stderr per SR-01.")
        Container(mcp, "MCP Adapter", "Python / mcp SDK", "Registers 4 tools, all sync per SR-07 (ADR-ARCH-017): tutor_start_session (sync; warm-up fire-and-forget), tutor_turn (sync; any mid-session student-model write is a ms-scale Postgres upsert), tutor_session_status (sync), tutor_session_end (sync; session-end write is one synchronous Postgres transaction per ADR-ARCH-023).")
        Container(session, "Tutor Session Manager", "Python / in-memory dict", "TutorSession aggregate. In-memory in P0; Postgres-backed P1+.")
        Container(llm, "LLM Client (Provider Factory)", "Python / langchain-*", "Resolves AGENT_MODELS__REASONING_MODEL at factory — SR-03. Routes local/bedrock/openai/anthropic/gemini.")
        ComponentDb(domain, "Domain Config", "Markdown + YAML", "domains/gcse-english/GOAL.md + roles/tutor/role.yaml + criteria/definitions.yaml. Shared-kernel taxonomy.")
        Container(gamdocs, "Gamification Design", "Markdown docs", "docs/gamification/design.md — authoritative economy. State engine deferred to P2.")

        Container_Boundary(p1, "Phase 1 additions") {
            Container(harness, "DeepAgents Harness (Player)", "Python / deepagents 0.5.3+", "create_deep_agent — Player role, tutoring prompt from GOAL.md. [P1]")
            Container(coach, "Coach (AsyncSubAgent)", "Python / deepagents AsyncSubAgent", "Quality monitor — async off hot path. Batches per-turn observations; confidence deltas + misconception logs are written synchronously in the session-end StudentStore transaction (ADR-ARCH-023 D2). [P1]")
            Container(planner, "Session Planner", "Python", "Reads the StudentStore (SQL), recommends topic. [P1]")
            Container(student_model, "Student Model (StudentStore)", "Python / Postgres (asyncpg, JSONB)", "Student, TopicConfidence, Session, Achievement, Quest rows. Synchronous session-end write replacing GraphitiWriteHelper. [P1]")
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
    System_Ext(postgres, "Postgres (study-tutor-owned)", "JSONB student store — own instance, port 5433, nightly pg_dump")
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
    Rel(coach, student_model, "Writes confidence delta + misconceptions [P1, sync at session-end per ADR-ARCH-023]")
    Rel(harness, planner, "Asks for topic [P1]")
    Rel(planner, student_model, "Reads confidence [P1]")
    Rel(student_model, postgres, "R/W", "SQL / asyncpg [P1]")
    Rel(rag, embedder, "Embed queries [P1]")

    Rel(session, export, "Emits at session-end [P1 schema; export channel is a local file write]")
    Rel(gamengine, student_model, "Subscribes to events [P2]")
    Rel(dashboard, export, "Renders from [P2]")
```

**Δ L2:** `student_model` tech `graphiti-core → Postgres (asyncpg, JSONB)`; removed `falkor` + `gemini` externals and the `student_model → falkor`, `student_model → gemini`, `student_model → embedder` edges; added `postgres` external + `student_model → postgres`; Coach + MCP + Planner + Session strings flipped from async/fire-and-forget to synchronous session-end. **Node count → 23** (15 internal + 5 external + 3 persons).

---

**If you approve**, I write everything in one batch: **023 → Accepted**; **007 + 019 → Superseded by 023**; **021** CC-13 annotation; both **C4 diagrams** above (incl. their prose/node-count sections); **ARCHITECTURE.md** (index rows 003/007/019/021 + add 020–024, summary + tech-stack + phase-map reframe); and the full-reconciliation prose in **gamification/design.md** (§2/§6/§11), **feature-roadmap.md** (FEAT-PH1-001), **domain-model.md** (write-back narrative), and the **ADR-022** parenthetical. Source/deps/config stay untouched (W1/W3 build targets).

Approved. Writing the full change-set now. Let me track this with a todo list and read the two downstream files I haven't seen yet (feature-roadmap, domain-model) so I edit them precisely.

All files loaded. Setting up tracking and executing the batch. First: the four ADR status changes (independent files), plus a grep for the two ADR statuses I need for the ARCHITECTURE.md index.

ADR statuses done (020=Accepted, 024=Proposed, multi-subject=Accepted noted for the index). Now the C4 Level 1 — mermaid block, prose, node count, and header provenance.

C4 Level 1 done. Now the C4 Level 2 — the larger diagram plus its prose, node count, and header.

Both C4 diagrams reconciled. Now ARCHITECTURE.md — summary, tech stack, Reachy row, CC-13, phase map, the ADR index (flip 007/019 + add 020–024), and counts.

ARCHITECTURE.md reconciled. Now the gamification design doc — the Graphiti references in §2, §6, §9, §11, §12, and the §11.2 "atomic" claim that ADR-023 makes literally true.

gamification design reconciled. Now feature-roadmap.md — a reconciliation banner plus the FEAT-PH1-001 row, SR-08, the dependency-graph node, and the "look for" line.

feature-roadmap reconciled. Now the largest prose file — domain-model.md: §4 location/keys, §4.4, §6.1 Gemini, §7.1 tool row, the §9 event-flow diagram + consistency model, §10 rationale, and the footer.

domain-model.md done. Now the light ADR-022 touch (its heading still literally says "Graphiti → fleet-memory", which is exactly the stale parenthetical ADR-023 flagged), plus a verification grep to confirm the C4 diagrams have no dangling `falkor`/`gemini` node ids.

Good — C4 node-ids are clean (the one `gemini` hit is the LLM provider-factory list, correctly retained). The grep caught two live assertions I should fix in ARCHITECTURE.md (§2 and §7), plus a moot Graphiti-read caveat in domain-model. Fixing those, then a final clean-grep.

All ADR statuses correct and the 003→019→023 chain is intact. One more honest reconciliation: the build plan's own §0 status tracker still says "G-ADR pending" — completing the gate makes that stale. Updating it.

All reconciliation edits are in. Let me confirm the exact file set changed, then finalize.

Two files show as changed that I did **not** edit — `docs/handoffs/study-tutor-mobile-voice-conversation-starter.md` (modified) and `ADR-ARCH-024` (untracked). The session started "clean," so let me look at what's in that handoff diff before I report — I won't claim work I didn't do.

That diff is entirely **ADR-ARCH-024 voice-STT work** — not mine. It was already in the working tree (the session-start "clean" snapshot predated it). I'll keep it separate in the summary so you don't bundle it by accident.
