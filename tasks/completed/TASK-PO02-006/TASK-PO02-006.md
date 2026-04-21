---
id: TASK-PO02-006
title: Parity surface verification and unit tests
status: completed
created: 2026-04-20T00:00:00Z
updated: 2026-04-20T00:00:00Z
completed: 2026-04-20T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-PO02-006/
priority: high
task_type: testing
tags: [phase-0, parity-surfaces, sr-01, sr-02, sr-03, sr-04, sr-06, sr-07]
complexity: 4
parent_review: TASK-REV-PO02
feature_id: FEAT-PO-002
wave: 3
implementation_mode: task-work
dependencies: [TASK-PO02-005]
estimated_minutes: 75
test_results:
  status: passed
  total: 21
  passed: 21
  failed: 0
  last_run: 2026-04-20T00:00:00Z
parity_log: .claude/reviews/TASK-PO02-006-parity-log.md
---

# Parity surface verification and unit tests

## Description

Formally verify all six parity surfaces that FEAT-PO-002 is responsible for (SR-05 Dockerfile is pass-through in Phase 0 — no Dockerfile shipped). Two surfaces are code-tested (**SR-01 stdio discipline**, **SR-03 provider resolution**); the other four are shell-verified with a documented checklist.

Per the **review finding (focus area 1): shift-left parity tests**. The two unit tests should be written earlier if possible — but this task is the formal acceptance gate that they exist and pass.

## Acceptance Criteria

### Code-level unit tests

- [ ] `tests/unit/mcp/test_stdio_discipline.py` exists. Tests:
  - Spawning `study-tutor serve --role tutor --transport stdio` with stdin closed writes **zero bytes to stdout** in the first 3 seconds.
  - Banner/log output is present on stderr.
  - Follows the `specialist-agent/tests/unit/mcp/test_stdio_discipline.py` pattern (copy shape, adapt module path).
  - Passes: `.venv/bin/pytest tests/unit/mcp/test_stdio_discipline.py -v`.
- [ ] `tests/unit/llm/test_provider_resolution.py` exists. Tests (end-to-end env-var → factory flow):
  - `_default_player_model()` returns `"local"` when `AGENT_MODELS__REASONING_MODEL` is unset.
  - `_default_player_model()` returns `"bedrock"` when env is set to `"bedrock"`.
  - `LLMClient(provider="bedrock").generate(...)` raises `NotImplementedError` mentioning FEAT-PO-004.
  - No handler in `adapter.py` references a provider string literal (grep assertion).
  - Passes: `.venv/bin/pytest tests/unit/llm/test_provider_resolution.py -v`.

### Shell verification checklist (SR-02, SR-04, SR-06, SR-07)

- [ ] **SR-02 (CWD absolute path):** `grep -E '^cd /' scripts/mcp-wrapper.sh` returns a match with an absolute path. No `$PWD` or relative paths. Documented in README.
- [ ] **SR-04 (providers extras completeness):** for each provider in `pyproject.toml [providers]`, `.venv/bin/pip show <provider>` succeeds. If any fails, update `pyproject.toml` and reinstall.
- [ ] **SR-06 (.env hygiene):**
  - `grep -E '=(sk-[a-zA-Z0-9]+|AIza[a-zA-Z0-9]+|not_needed|sk-test)' .env.example` returns nothing.
  - All placeholder values are `<angle-bracket>` form.
  - `.env` is in `.gitignore`; `git status` with a populated `.env` shows it as untracked/ignored.
- [ ] **SR-07 (tool description ≡ behaviour):** read the four MCP tool description strings in `adapter.py`. Verify each matches the handler:
  - `tutor_start_session`: description says "long-running", handler returns `{"session_id"}` in ≤1s.
  - `tutor_turn`: description says "sync", handler completes synchronously.
  - `tutor_session_status`: description says "sync, returns current session state", handler is pure read.
  - `tutor_session_end`: description says "marks session ended" (NOT "triggers async Graphiti write").

### Documentation

- [ ] `.claude/reviews/TASK-PO02-006-parity-log.md` written documenting: exact commands run, output captured, any drift fixed, and a final "Six parity surfaces: GREEN" line.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation Notes

- **SR-05** (Dockerfile parity) is a structural pass-through in Phase 0 — no Dockerfile ships. Note this explicitly in the parity log with a forward-reference to Phase 1 re-activation.
- If any shell check fails, **fix the underlying issue** in the relevant source task's file — do NOT silence the check. SR-01/SR-03 failures specifically should escalate back to TASK-PO02-005 / TASK-PO02-003 for a fix commit.
- Tests in this task run against the artefacts of TASK-PO02-001 through TASK-PO02-005. If those are incomplete, this task is blocked.

## Reference Files

- Specialist-agent test patterns: `../specialist-agent/tests/unit/mcp/test_stdio_discipline.py`, `../specialist-agent/tests/unit/llm/test_provider_resolution.py` (if present — otherwise adapt from specialist-agent's MCP test suite)
- Scope: [docs/research/ideas/phase-0-scope.md §Structural Requirements SR-01 → SR-07](../../../docs/research/ideas/phase-0-scope.md)
- Plan: [docs/research/ideas/phase-0-build-plan.md:183-199, :453-454](../../../docs/research/ideas/phase-0-build-plan.md#L183-L199)
