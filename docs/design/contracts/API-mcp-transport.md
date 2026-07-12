# API Contract — MCP Transport

**Bounded context:** MCP Transport
**Phase:** P0 (live), with Phase 1 evolution under CC-13
**Status:** Accepted — design captures live behaviour in `src/study_tutor/mcp/{server.py, adapter.py}` and `scripts/mcp-wrapper.sh`
**Generated:** 2026-04-26 by `/system-design` (bias-to-defaults, Phase 0 scope)
**Refreshed:** 2026-04-27 by `/system-design --focus="MCP Transport"` to absorb [ADR-ARCH-017](../../architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md), [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md), [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md), and the [27 Apr 2026 Graphiti latency spike](../../research/ideas/graphiti-latency-spike-results.md) (`add_episode` median 78.98s).

**Addendum 2026-07-12 (Phase-R S-R2 — gamification settlement):** `tutor_session_end` gains the **same nullable `gamification` block** its HTTP sibling `end_session` gains in [API-session-cross-device.md §5 Revision 2](API-session-cross-device.md). Additive and nullable — the block is **absent until the engine settles the session**, so pinned MCP clients (Claude Desktop) are unaffected. The block shape and field semantics are the contract's ([API-session-cross-device.md §5 Rev 2](API-session-cross-device.md)): `{xp_awarded, total_xp, level_number, level_name, level_up, achievements_unlocked:[{id,name,xp}], streak_days, streak_extended}`. Per the D14 fence (scope & build plan D14; [ADR-ARCH-030](../../architecture/decisions/ADR-ARCH-030-gamification-settlement-pure-engine-finalize-transaction.md) D7) the adapter holds **no** settlement logic the HTTP path lacks — settlement is `SessionService.finalize_session`; `tutor_session_end` is a thin tool-shape skin that surfaces the same banked decision. This addendum touches only the `tutor_session_end` **output**; the four-tool inventory, the sync classification, and the transport invariants are unchanged.

---

## 1. Purpose

MCP Transport is a **thin façade** owning the external protocol surface for AI agents. It enforces transport-layer invariants (SR-01 / SR-02 / SR-07 / CC-08 / CC-13) and turns the tutor into a discoverable, invokable system. The tools themselves and their behavioural contracts belong to **Tutoring** — see `API-tutoring.md`. CC-14 (runtime LLM parameters explicit) is owned by Inference Runtime / Tutoring; this contract notes only its presence on the cross-cutting checklist (see §5.5).

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

## 5. Tool registration invariants (SR-07 / CC-07 / CC-13)

1. **Tool description ≡ implementation contract.** A tool's MCP description string is the externally-visible contract. Behaviour must match. SR-07 disallows the "undefined middle" — every tool is **sync** (< 30s end-to-end) or **long-running** (returns a tracking ID immediately, behaviour exposed via a polled companion tool).
2. **Sync ceiling is 30s.** Inherits from MCP client timeouts (Claude Desktop's 240s ceiling is a hard upper bound; the operational target is < 30s).
3. **Long-running tools return a tracking ID in ≤ 1s** (CC-08). P0 has none — `tutor_start_session` is sync per [ADR-ARCH-017](../../architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md) (closes design decision D2 from the 2026-04-26 pass).
4. **Phase-1 background work uses deepagents AsyncSubAgent.** Hand-rolled `asyncio.create_task(...)` is acceptable for the Phase-0 warm-up case (warm-up is fire-and-forget, not user-observable), but the Coach (P1) **must** use AsyncSubAgent (CC-12) per ADR-ARCH-012.
5. **Graphiti write side-effects are implementation-internal (CC-13 / SR-07).** When Phase 1 adds Graphiti writes inside `tutor_turn` (mid-session: Coach misconceptions, planner topic-confidence updates) and `tutor_session_end` (session-end episode), those writes are **fire-and-forget at every write point** per [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) (broadens the prior session-end-only ARCH-003 framing). The MCP tool description string for those tools **does not** enumerate the Graphiti write — see [DDR-001](../decisions/DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md). Empirical anchor: the [2026-04-27 Graphiti latency spike](../../research/ideas/graphiti-latency-spike-results.md) measured `add_episode` median **78.98s** — ~15× the 5s SR-08 threshold and ~26× the original DEC-08 1–3s assumption. Awaiting any such write on the caller path is a guaranteed SR-07 / CC-08 violation. Read-path reads (`search_nodes` median 0.07s) remain compatible with the sync classification of `tutor_start_session` / `tutor_session_status`.

### 5.5 CC-14 (runtime LLM parameters) — pointer
CC-14 (every Modelfile sets explicit `num_ctx` / `num_predict`, with smoke-test assertions via `ollama show` *and* runner-log inspection) is owned by **Inference Runtime** / **Tutoring**. MCP Transport carries it on its cross-cutting checklist for completeness only; the contract surface (tool descriptions, schemas, error envelope) does not change with CC-14.

### 5.6 Phase 1 reversion-conditional rule (from ADR-ARCH-017)
If a future Phase 1 measurement shows that the Graphiti student-model **read** at session start pushes `search_nodes` median > ~3s, `tutor_start_session` reverts to **long-running** and a `_status` / `_cancel` companion tool is added. The 27 Apr spike measured 0.07s — the condition is **not** triggered today. The reversion path is documented here so an `/arch-refine` flip is unsurprising rather than disruptive.

**Conformance check (recommended):** add a tool-contract test that introspects every registered MCP tool's description and asserts the classification keyword (`"sync"` or `"long-running"`) matches the handler's measured latency band over a sample. The same test should assert that no MCP tool description enumerates a Graphiti operation (CC-13 / DDR-001).

## 6. Tool inventory (P0 + P1 evolution)

The MCPAdapter registers exactly four tools, all **sync** per ADR-ARCH-017:

| Tool | Class | Source | P1 Graphiti side-effects (per CC-13 / ADR-ARCH-019) |
|---|---|---|---|
| `tutor_start_session` | sync | `MCPAdapter.tutor_start_session` (warm-up via `asyncio.create_task`) | Reads student-model context (`search_nodes`, 0.07s — sync-safe). No writes. Reversion to long-running gated on §5.6 measurement. |
| `tutor_turn` | sync | `MCPAdapter.tutor_turn` (LLM call wrapped in `asyncio.to_thread`) | **Mid-session writes are fire-and-forget at every write point** — Coach-observed misconceptions and planner topic-confidence updates use deepagents `AsyncSubAgent` (CC-12) or `asyncio.create_task` per ARCH-019. Tool description does not enumerate these writes (DDR-001). |
| `tutor_session_status` | sync | `MCPAdapter.tutor_session_status` | Read-only. May read student-model state (sync-safe). |
| `tutor_session_end` | sync | `MCPAdapter.tutor_session_end` | **Session-end Graphiti episode write is fire-and-forget** per ARCH-019 — no longer the single write point, but still a write point. Handler returns < 2s regardless of `add_episode` latency (78.98s median). Tool description does not enumerate this write (DDR-001). **S-R2 addendum (2026-07-12):** output gains the nullable `gamification` settlement block (see header addendum); settlement is the synchronous `SessionService.finalize_session` ([ADR-ARCH-030](../../architecture/decisions/ADR-ARCH-030-gamification-settlement-pure-engine-finalize-transaction.md)), not adapter logic (D14 fence). |

Per-tool input/output schemas live in `docs/design/mcp-tools.json` and `docs/design/contracts/API-tutoring.md §3`. The tool **input/output schema set is unchanged** by ADR-019: the contract surface is identical to P0; only the implementation-internal write topology broadens.

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
2. **P1 — long-running reclassification (RESOLVED for current spike measurement).** ADR-ARCH-017 §"Phase 1 reversion condition" sets the rule: revert iff `search_nodes` median > ~3s at session-start read. The 27 Apr spike measured 0.07s, so the condition does not fire today. Re-evaluate if the Phase-1 student-model read path adds entity hops or a co-located text retrieval that changes the latency shape.
3. **P2 — multi-role.** If multi-subject expansion lands, the wrapper `--role` flag becomes load-bearing; today it is a no-op (`tutor` is the only registered role).
4. **P1+ — tool-contract test for DDR-001.** Add a test that asserts no MCP tool description string contains substrings like "Graphiti", "FalkorDB", "episode", or "write-back" (case-insensitive). Cheaper than per-PR review and catches accidental SR-07 leakage as Phase 1 features add write sites.
