---
id: TASK-PO02-001
title: Python package scaffold and config files
status: completed
created: 2026-04-20T00:00:00Z
updated: 2026-04-20T12:45:00Z
completed: 2026-04-20T12:45:00Z
completed_location: tasks/completed/TASK-PO02-001/
priority: high
task_type: scaffolding
tags: [phase-0, scaffold, packaging]
complexity: 3
parent_review: TASK-REV-PO02
feature_id: FEAT-PO-002
wave: 1
implementation_mode: task-work
dependencies: []
estimated_minutes: 60
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-20T12:30:00Z
  notes: |
    Scaffolding task — no unit tests. Verification gates executed manually:
    - pyproject.toml: valid TOML, correct package name, python>=3.11, entrypoint, [providers] extra
    - .venv/bin/pip install -e '.[providers]' completed without error
    - SR-04: pip show passed for all 5 providers (langchain-{openai,anthropic,google-genai,aws,ollama})
    - src/study_tutor/ tree with empty __init__.py in cli/llm/mcp/session — imports cleanly
    - .env.example: only <angle-bracket> placeholders + AGENT_MODELS__REASONING_MODEL=local; no real-looking keys (SR-06)
    - AGENTS.md: ALWAYS/NEVER/ASK for Tutor role
    - .mcp.json: valid JSON with study-tutor stanza template
    - .gitignore: all 7 required patterns present
    - command_history.md: first entry is /feature-plan FEAT-PO-002
---

# Python package scaffold and config files

## Description

Lay down the Python package skeleton for `study_tutor`, including `pyproject.toml` (with `[providers]` extra per **SR-04**), empty `src/study_tutor/` module tree, top-level config files, and the venv.

Reference source for patterns: [`/Users/richardwoollcott/Projects/appmilla_github/specialist-agent`](../../../specialist-agent) — copy shapes, do **not** copy architect/PO-specific content.

## Acceptance Criteria

- [ ] `pyproject.toml` defines package `study_tutor`, Python ≥3.11, entrypoint `study-tutor = study_tutor.cli.main:serve`, and `[project.optional-dependencies].providers` listing `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`, `langchain-aws`, `langchain-ollama` (or `ollama` HTTP client).
- [ ] `.venv` created with `python3.11 -m venv .venv`; `.venv/bin/pip install -e '.[providers]'` completes without error.
- [ ] SR-04 check passes: `pip show` succeeds for every declared provider in `[providers]`.
- [ ] `src/study_tutor/` directory tree created with empty `__init__.py` files in `cli/`, `llm/`, `mcp/`, `session/`. No logic yet.
- [ ] `.env.example` at repo root with placeholder values in `<angle-bracket>` form (SR-06). Must include `AGENT_MODELS__REASONING_MODEL=local` as the default. Must NOT contain any value that could be mistaken for a real key (no `sk-test-xxxx`, no `not_needed`).
- [ ] `AGENTS.md` at repo root declaring ALWAYS / NEVER / ASK boundaries — copy shape from specialist-agent, adapt for tutor scope.
- [ ] `.mcp.json` template at repo root (used as reference for Claude Desktop config).
- [ ] `.gitignore` includes `.venv/`, `.env`, `__pycache__/`, `*.pyc`, `dist/`, `build/`, `*.egg-info/`. (FEAT-PO-003 extends this further; don't pre-empt its scope.)
- [ ] `command_history.md` at repo root with the first entry being the `/feature-plan FEAT-PO-002` invocation.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation Notes

- **Copy-paste discipline:** do not wholesale-copy `pyproject.toml` from specialist-agent. Copy the *shape* and *extras pattern*; rewrite metadata fields by hand. Rename `[project.scripts]` to `study-tutor`.
- **Providers extra:** `langchain-aws` is listed now even though FEAT-PO-002 only stubs Bedrock (`NotImplementedError`). This is per SR-04 — the extras declaration must match future imports so FEAT-PO-004 doesn't need a `pyproject.toml` edit.
- **Do NOT commit:** `.venv/`, `.env`, any `*.pdf`, any `*.gguf`.
- First commit message suggestion: `Phase 0 kickoff: scaffold package, copy patterns from specialist-agent`.

## Reference Files

- Source of patterns: `../specialist-agent/pyproject.toml`, `../specialist-agent/AGENTS.md`, `../specialist-agent/.env.example`, `../specialist-agent/.mcp.json`
- Scope: [docs/research/ideas/phase-0-scope.md §SR-04, §SR-06](../../../docs/research/ideas/phase-0-scope.md)
- Plan: [docs/research/ideas/phase-0-build-plan.md:111-148](../../../docs/research/ideas/phase-0-build-plan.md#L111-L148)
