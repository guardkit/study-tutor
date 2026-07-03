# Study Tutor — C4 Container Diagram (Level 2)

**Status:** Phase 0 canonical.
**Generated:** 2026-04-18 by `/system-arch`.
**Revised:** 2026-07-03 by `/arch-refine` (ADR-ARCH-023) — Graphiti/FalkorDB student model → study-tutor-owned Postgres; synchronous session-end write; mandatory C4 re-review gate approved.
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
    System_Ext(postgres, "Postgres (study-tutor-owned)", "JSONB student store — own instance, port 5434, nightly pg_dump")
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
  Per **`ADR-ARCH-023`** (D2) this is a **synchronous session-end Postgres
  transaction**; the async CC-13 / `ADR-ARCH-019` write-back is retired
  (no `add_episode` remains — the 79s LLM-per-write tax is gone).

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

23 nodes (15 internal + 5 external + 3 persons). Well under the 30-node
threshold.

---

*This file is the canonical C4 Level 2 artefact. Revisions require
`/system-arch --mode=refine` or the `/arch-refine` mandatory C4 re-review
gate (last: 2026-07-03, ADR-ARCH-023).*
