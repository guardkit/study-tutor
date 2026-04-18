# ADR-ARCH-004 — Python 3.11 + deepagents + langchain + mcp stack

## Status

Accepted

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
