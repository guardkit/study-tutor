# FEAT-PO-002 smoke-test follow-ups

Defects and drift discovered during [TASK-PO02-007 live smoke test](../../../.claude/reviews/TASK-PO02-007-smoke-log.md) (2026-04-21).

**None of these blocked the Phase 0 gate** — the smoke log declared end-of-Saturday **GREEN** and FEAT-PO-002 is submittable. These are the punch list of content-quality and hygiene items to sequence *before* multi-subject expansion or the FEAT-PO-004 Bedrock wire-up.

## Tasks

| Task | Title | Priority | Complexity |
|------|-------|----------|------------|
| [TASK-PO02F-001](TASK-PO02F-001-quote-fidelity-rag-scope.md) | Scope RAG grounding for quote fidelity | high | 5 (scoping only) |
| [TASK-PO02F-002](TASK-PO02F-002-ollama-num-predict-ceiling.md) | Set explicit `num_predict` ceiling on Ollama requests | high | 2 |
| [TASK-PO02F-003](TASK-PO02F-003-fix-stale-default-model-tag.md) | Fix stale `DEFAULT_OLLAMA_MODEL` fallback in `client.py` | low | 1 (micro) |

## Why the folder

These are cross-cutting follow-ups that don't belong inside `feat-po-002-tutoring-runtime/` (that feature is closing) and aren't yet coherent enough to justify promoting into a new FEAT. Keep them here until they're either scheduled or promoted into a proper feature folder (likely FEAT-PO-006 "RAG grounding" once scoped).
