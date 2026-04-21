# FEAT-PO-002 — Fine-tuned English tutoring runtime

**Feature ID:** FEAT-PO-002
**Parent review:** [TASK-REV-PO02](../../in_review/TASK-REV-PO02-plan-feat-po-002-tutoring-runtime.md)
**Execution:** `/task-work` reviewer-in-loop
**Target completion:** Saturday 19 April — Sunday 20 April 2026 (weekend, ~7.5h)

## What this is

The Phase 0 critical-path runtime. Ships the Python package scaffold, MCP adapter with four tutor tools, Ollama-backed LLM client (with Bedrock stub for FEAT-PO-004), in-memory tutor session state, and the two code-level parity-surface tests (SR-01 stdio, SR-03 provider resolution).

Completion gate: Claude Desktop issues a `tutor_turn` call and receives a coherent response from the fine-tuned Gemma 4 31B model on GB10 via Ollama.

## Why it exists

FEAT-PO-002 is the *critical path* — every other Phase 0 feature either depends on it (FEAT-PO-003 packaging, FEAT-PO-004 Bedrock) or references it (FEAT-PO-005 write-up). If this feature ships cleanly, Phase 0 is submittable for the Gemma 4 Good Hackathon on its own.

The surrounding context — domain config (FEAT-PO-001), repo packaging (FEAT-PO-003), Bedrock ops (FEAT-PO-004), write-up (FEAT-PO-005) — all assume this runtime exists.

## Task breakdown

7 subtasks across 3 waves. Full dependency graph and rationale in [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md).

### Wave 1 — Foundation (~1.5h)

| Task | Title | Mode |
|------|-------|------|
| [TASK-PO02-001](TASK-PO02-001-python-package-scaffold.md) | Python package scaffold | `/task-work` |
| [TASK-PO02-002](TASK-PO02-002-role-manifest.md) | Role manifest + player prompt shell | direct |

### Wave 2 — Runtime (~4h)

| Task | Title | Mode |
|------|-------|------|
| [TASK-PO02-003](TASK-PO02-003-llm-client.md) | LLM client + provider resolution | `/task-work` |
| [TASK-PO02-004](TASK-PO02-004-tutor-session.md) | In-memory tutor session state | `/task-work` |
| [TASK-PO02-005](TASK-PO02-005-mcp-adapter-cli-wrapper.md) | MCP adapter + CLI + bash wrapper | `/task-work` |

### Wave 3 — Hardening (~2h)

| Task | Title | Mode |
|------|-------|------|
| [TASK-PO02-006](TASK-PO02-006-parity-tests.md) | Parity surface tests | `/task-work` |
| [TASK-PO02-007](TASK-PO02-007-smoke-test.md) | Live smoke test | direct |

## Start here

```bash
/task-work TASK-PO02-001
```

## See also

- Review report: [.claude/reviews/TASK-REV-PO02-review-report.md](../../../.claude/reviews/TASK-REV-PO02-review-report.md)
- Build plan: [docs/research/ideas/phase-0-build-plan.md](../../../docs/research/ideas/phase-0-build-plan.md)
- Phase 0 scope: [docs/research/ideas/phase-0-scope.md](../../../docs/research/ideas/phase-0-scope.md)
- Feature YAML: `.guardkit/features/FEAT-PO-002.yaml`
