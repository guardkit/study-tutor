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
