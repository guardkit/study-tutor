# API Contract — MCP Transport

**Bounded context:** MCP Transport
**Phase:** P0 (live)
**Status:** Accepted — design captures live behaviour in `src/study_tutor/mcp/{server.py, adapter.py}` and `scripts/mcp-wrapper.sh`
**Generated:** 2026-04-26 by `/system-design` (bias-to-defaults, Phase 0 scope)

---

## 1. Purpose

MCP Transport is a **thin façade** owning the external protocol surface for AI agents. It enforces transport-layer invariants (SR-01 / SR-02 / SR-07 / CC-08) and turns the tutor into a discoverable, invokable system. The tools themselves and their behavioural contracts belong to **Tutoring** — see `API-tutoring.md`.

This contract documents the **transport invariants** and **CLI surface**, not the per-tool semantics.

## 2. Surfaces owned

### 2.1 MCP stdio transport

- Protocol: MCP JSON-RPC over stdin/stdout (per the `mcp` Python SDK).
- Invocation: via `study-tutor serve --role tutor --transport stdio`.
- Registration: by Claude Desktop or any MCP client through `claude_desktop_config.json` pointing at `scripts/mcp-wrapper.sh`.

### 2.2 CLI

- Binary: `study-tutor` (entry point declared in `pyproject.toml`).
- Subcommand: `serve`.
- Flags: `--role <name>`, `--transport <stdio|http>`.
- HTTP transport is **not implemented** in P0; flag accepted but raises NotImplementedError. Deferred to P1+.

### 2.3 Bash wrapper

- Path: `scripts/mcp-wrapper.sh`.
- Pattern: `set -a && . /absolute/path/.env && set +a && export AGENT_MODELS__REASONING_MODEL=local && exec /absolute/path/.venv/bin/study-tutor serve --role tutor --transport stdio`.
- Required by SR-02 — must `cd /absolute/path/to/study-tutor` (or use absolute paths to env + venv binary as above) before `exec`.

## 3. Transport invariants (SR-01 / CC-01)

1. **stdout is exclusively MCP JSON-RPC.** Before the MCP handshake completes, stdout must produce zero bytes. After handshake, only protocol frames.
2. **All diagnostics route to stderr.** Banners, warnings, log lines, status messages — `click.echo(..., err=True)` or `print(..., file=sys.stderr)`. Loggers are configured to emit on stderr only.
3. **Banner is mandatory.** A "Study Tutor MCP server starting…" banner must appear on stderr at startup so operators see a sign-of-life. Empty stderr is a P0 regression.

**Conformance test:** `tests/unit/mcp/test_stdio_discipline.py` runs `serve --transport stdio < /dev/null` for ~3s and asserts:
- `stdout.log` is empty (no bytes before handshake);
- `stderr.log` contains the startup banner.

## 4. Launcher invariants (SR-02 / CC-02)

1. **Bash wrapper uses absolute paths.** Either `cd /absolute/path && exec …` or all paths in the `exec` line are absolute. Relative paths break under Claude Desktop's unspecified launcher CWD.
2. **`.env` is loaded explicitly.** `set -a && . /absolute/path/.env && set +a` before `exec`. Claude Desktop does not read `.env` for the spawned process.
3. **Provider override goes through env.** `export AGENT_MODELS__REASONING_MODEL=local` (or `bedrock`) before `exec` — never as a CLI flag — to keep SR-03 honest.

**Conformance check:** README's `claude_desktop_config.json` snippet uses the bash wrapper with absolute path. Spot-checked during the clean-machine walkthrough (FEAT-PO-003 Wednesday gate).

## 5. Tool registration invariants (SR-07 / CC-07)

1. **Tool description ≡ implementation contract.** A tool's MCP description string is the externally-visible contract. Behaviour must match. SR-07 disallows the "undefined middle" — every tool is **sync** (< 30s end-to-end) or **long-running** (returns a tracking ID immediately, behaviour exposed via a polled companion tool).
2. **Sync ceiling is 30s.** Inherits from MCP client timeouts (Claude Desktop's 240s ceiling is a hard upper bound; the operational target is < 30s).
3. **Long-running tools return a tracking ID in ≤ 1s** (CC-08). P0 has none after [decision D2 (2026-04-26)](../../research/ideas/phase-0-build-plan.md) reclassified `tutor_start_session` as sync.
4. **Phase-1 background work uses deepagents AsyncSubAgent.** Hand-rolled `asyncio.create_task(...)` is acceptable for the Phase-0 warm-up case (warm-up is fire-and-forget, not user-observable), but the Coach (P1) **must** use AsyncSubAgent (CC-12) per ADR-ARCH-012.

**Conformance check (recommended):** add a tool-contract test that introspects every registered MCP tool's description and asserts the classification keyword (`"sync"` or `"long-running"`) matches the handler's measured latency band over a sample.

## 6. Tool inventory (P0)

The MCPAdapter registers exactly four tools, all **sync** post-D2:

| Tool | Class | Source |
|---|---|---|
| `tutor_start_session` | sync | `MCPAdapter.tutor_start_session` (warm-up via `asyncio.create_task`) |
| `tutor_turn` | sync | `MCPAdapter.tutor_turn` (LLM call wrapped in `asyncio.to_thread`) |
| `tutor_session_status` | sync | `MCPAdapter.tutor_session_status` |
| `tutor_session_end` | sync | `MCPAdapter.tutor_session_end` (P1: triggers async Graphiti write inside; classification unchanged) |

Per-tool input/output schemas live in `docs/design/mcp-tools.json` and `docs/design/contracts/API-tutoring.md §3`.

## 7. Configuration surface

| Variable / file | Effect |
|---|---|
| `AGENT_MODELS__REASONING_MODEL` (env) | Default provider for tool handlers; resolved per call (SR-03). Set in the bash wrapper before `exec`. |
| `roles/tutor/role.yaml` | Loaded at adapter init; declares prompt locations and role metadata. |
| `roles/tutor/prompts/player.md` | Loaded at adapter init as the system prompt for `tutor_turn`. |
| `claude_desktop_config.json` (operator-side) | Registers the `study-tutor` MCP server using the bash wrapper. |

## 8. Error envelope

MCP Transport does not introduce its own error shape — handlers return the Tutoring context's error envelope (`API-tutoring.md §4`). MCP-level errors (malformed JSON-RPC, unknown tool name) are handled by the `mcp` SDK and surface as protocol-level errors.

## 9. Out of scope

- **HTTP transport.** Flag accepted, implementation deferred to P1+.
- **TLS / mTLS.** Out of scope — single-user, local + Tailscale only (ADR-ARCH-008/015).
- **Authentication / authorisation hooks.** Out of scope (ADR-ARCH-014).
- **Multi-role dispatch.** Scaffolded (`roles/`) but unused — single role (`tutor`) only in P0; multi-subject is post-hackathon (DEC-05).

## 10. Open questions for downstream phases

1. **P1 — HTTP transport.** If the dashboard (P2) or Reachy (P2 stretch) needs network access, decide between (a) HTTP MCP transport, (b) static export + read-only SDK, or (c) on-host-only SDK (Reachy). Currently leaning (b) per ARCHITECTURE.md §5.
2. **P1 — long-running reclassification.** If `tutor_start_session` adds Graphiti reads at session start that exceed 1s, reverse decision D2 and re-add the long-running classification + companion polling contract.
3. **P2 — multi-role.** If multi-subject expansion lands, the wrapper `--role` flag becomes load-bearing; today it is a no-op (`tutor` is the only registered role).
