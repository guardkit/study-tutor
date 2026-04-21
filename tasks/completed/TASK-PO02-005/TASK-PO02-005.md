---
id: TASK-PO02-005
title: MCP adapter + CLI + bash wrapper
status: completed
created: 2026-04-20T00:00:00Z
updated: 2026-04-20T08:20:00Z
completed: 2026-04-20T08:20:00Z
completed_location: tasks/completed/TASK-PO02-005/
previous_state: in_review
state_transition_reason: "All acceptance criteria met; 18/18 tests passing; SR-01 + SR-02 smoke-tests green via wrapper from foreign CWD"
priority: high
task_type: feature
tags: [phase-0, mcp, cli, bash-wrapper, sr-01, sr-02, sr-07]
complexity: 6
parent_review: TASK-REV-PO02
feature_id: FEAT-PO-002
wave: 2
implementation_mode: task-work
dependencies: [TASK-PO02-002, TASK-PO02-003, TASK-PO02-004]
estimated_minutes: 120
consumer_context:
  - task: TASK-PO02-002
    consumes: role_manifest_path
    framework: "PyYAML + pathlib (load role.yaml at serve-time, resolve paths relative to repo root)"
    driver: "pyyaml"
    format_note: "Path MUST resolve from absolute repo root, not CWD (SR-02). The bash wrapper cd's to absolute path before exec'ing serve; CLI receives role name via --role flag and constructs roles/<name>/role.yaml path from the wrapper-set CWD."
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-20T08:15:00Z
  passed: 18
  failed: 0
  notes: |
    tests/unit/mcp/test_adapter.py — 6 handler/server smoke tests (new).
    Existing suites (llm: 7, session: 5) still green.
    SR-01 verified: stdout empty after 2s serve; banners on stderr only.
    SR-02 verified: wrapper cd'd to abs repo root from /tmp and role.yaml resolved.
---

# MCP adapter + CLI + bash wrapper

## Description

The heart of FEAT-PO-002 — the MCP server that Claude Desktop talks to. Delivers:

1. **`src/study_tutor/mcp/adapter.py`** — registers four MCP tools (`tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end`) using the specialist-agent fire-and-forget pattern.
2. **`src/study_tutor/cli/main.py`** — `study-tutor serve --role tutor --transport stdio` entrypoint. All banners and logs go to stderr (**SR-01**).
3. **`scripts/mcp-wrapper.sh`** — bash wrapper that `cd`s to absolute repo path, sources `.env`, sets `AGENT_MODELS__REASONING_MODEL=local`, and exec's the serve command (**SR-02**).
4. Updates `claude_desktop_config.json` snippet in `README.md` and `.mcp.json` for reference.

This task is the **SR-01, SR-02, and SR-07 locus**. The separate parity-test task (TASK-PO02-006) verifies the results with unit tests.

## Acceptance Criteria

### MCP adapter

- [ ] Four tools registered in `src/study_tutor/mcp/adapter.py`:
  - `tutor_start_session(subject: str, topic: str | None = None)` — **long-running** classification. Returns `{"session_id": "<uuid>"}` in ≤1s. Description text MUST say "long-running, returns session_id immediately".
  - `tutor_turn(session_id: str, user_message: str)` — **sync** classification. Target <30s. Returns `{"tutor_response": "..."}`. Description must say "sync, typically returns within 15s".
  - `tutor_session_status(session_id: str)` — **sync**, pure read. Returns `{"session_id", "status", "turn_count", "started_at"}`. Description: "sync, returns current session state".
  - `tutor_session_end(session_id: str)` — **sync**, Phase-0 no-op beyond flipping status. Description: `"marks session ended"`. MUST NOT say "triggers async Graphiti write" in Phase 0 (SR-07 violation per review finding).
- [ ] Fire-and-forget pattern for `tutor_start_session`: spawn a `warm_up()` call to `LLMClient` (no-op generate) in the background using `asyncio.create_task`. This prevents a cold-start timeout on the first `tutor_turn` (per review risk register).
- [ ] Every handler reads `player_model = params.get("player_model") or _default_player_model()` — no hard-coded provider anywhere (SR-03).
- [ ] `_run_tutor_session()` helper does one `LLMClient.generate()` call per turn, injecting the player prompt from `roles/tutor/prompts/player.md` as the `system` arg.

### CLI + stdio discipline

- [ ] `study-tutor serve --role tutor --transport stdio` is the invocation. Click-based CLI is fine.
- [ ] All banners, log lines, and diagnostics go to stderr via `click.echo(..., err=True)` or `print(..., file=sys.stderr)`. **Stdout is reserved for MCP JSON-RPC only** (SR-01).
- [ ] Stream-split test passes (full unit test lives in TASK-PO02-006):
  ```bash
  .venv/bin/study-tutor serve --role tutor --transport stdio < /dev/null > stdout.log 2> stderr.log &
  sleep 3; kill %1
  test ! -s stdout.log && echo "SR-01 green"
  ```

### Bash wrapper

- [ ] `scripts/mcp-wrapper.sh` exists with executable permissions (`chmod +x`).
- [ ] Wrapper `cd`s to the **absolute** repo path (not relative, not `$PWD`). SR-02 compliance.
- [ ] Wrapper sources `.env` via `set -a && . /absolute/path/.env && set +a`, exports `AGENT_MODELS__REASONING_MODEL=local` (default), and exec's `/absolute/path/.venv/bin/study-tutor serve --role tutor --transport stdio`.
- [ ] README has a `claude_desktop_config.json` snippet using the wrapper.

### Integration

- [ ] Claude Desktop, after restart with the wrapper added to `claude_desktop_config.json`, shows `study-tutor` in its MCP server list with **exactly 4 tools**.
- [ ] From a Claude Desktop chat, `tutor_start_session(subject="English Literature", topic="Macbeth")` returns a `session_id`, then `tutor_turn(session_id, "Tell me about the witches in Act 1")` returns a coherent tutor response. (Live smoke is automated in TASK-PO02-007; this task's acceptance is "the loop closes once.")
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Seam Tests

Contract is with TASK-PO02-002 (role manifest path). Seam tests are consolidated in TASK-PO02-006's parity-surface test file (`tests/unit/mcp/test_stdio_discipline.py`) since they share the SR-01/SR-02 concern. No separate seam test needed here — the contract is enforced by the bash wrapper behaviour and tested end-to-end in TASK-PO02-007.

## Implementation Notes

- **Pattern source:** `specialist-agent/src/specialist_agent/mcp/adapter.py` — copy `_start_po_session()` / `_run_po_session()` shape for the long-running tutor_start_session pattern.
- **Cold-start warm-up:** after creating the session, spawn `asyncio.create_task(LLMClient(provider=player_model).generate(""))` to load the Ollama model weights into memory. Ignore the result. Saves the user from a 30s timeout on first turn.
- **`tutor_session_end` description:** this was explicitly flagged in the review as an SR-07 violation risk. Description text: `"marks session ended"`. In-code comment: `# TODO(phase-1): add async Graphiti write per DEC-02`. Do NOT write the Graphiti code now.
- **Provider-agnostic handlers:** even though Phase 0 only supports `"local"`, handlers MUST route through `player_model` param → `_default_player_model()` → LLMClient factory. FEAT-PO-004 then lights up `"bedrock"` with zero handler changes.
- **Role loading:** read `roles/tutor/role.yaml` at serve startup, resolve `player_prompt_path` from the absolute repo root that the bash wrapper's `cd` established.

## Reference Files

- Pattern source: `../specialist-agent/src/specialist_agent/mcp/adapter.py`
- Scope: [docs/research/ideas/phase-0-scope.md §SR-01, §SR-02, §SR-07, §3. MCP adapter](../../../docs/research/ideas/phase-0-scope.md)
- Plan: [docs/research/ideas/phase-0-build-plan.md:150-175](../../../docs/research/ideas/phase-0-build-plan.md#L150-L175)
