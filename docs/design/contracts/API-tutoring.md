# API Contract — Tutoring

**Bounded context:** Tutoring
**Phase:** P0 (live)
**Status:** Accepted — design captures live behaviour in `src/study_tutor/mcp/adapter.py` and `src/study_tutor/session/tutor_session.py`
**Generated:** 2026-04-26 by `/system-design` (bias-to-defaults, Phase 0 scope)

---

## 1. Consumers

| Consumer | Surface | Phase |
|---|---|---|
| AI agents (Claude Desktop, future Jarvis) | MCP JSON-RPC over stdio | P0 |
| Developers / judges | CLI wrapping the MCP surface | P0 |
| Internal contexts (Student Model P1, Gamification P2) | In-process Events (Shared Kernel B) | P1+ |

REST / GraphQL / A2A / ACP are **out of scope** by ADR-ARCH-008 (single-user MCP-only posture). Open WebUI's interface for Lilymay points at Ollama directly (and at Bedrock via LiteLLM proxy P0+); it does not consume this contract.

## 2. Auth & posture

- **Authentication:** none. Single-user single-host (ADR-ARCH-014); MCP stdio transport is local + Tailscale only (ADR-ARCH-008/ADR-ARCH-015).
- **Authorisation:** N/A — Phase 0.
- **Rate limiting / quotas:** none (ADR-ARCH-011).

## 3. MCP tool surface

Four tools registered by `MCPAdapter`. SR-07 classification is the truthful classification per the live handler — see [decision D2 (2026-04-26)](../../research/ideas/phase-0-build-plan.md) reclassifying `tutor_start_session` from "long-running" to "sync".

### 3.1 `tutor_start_session`

| Property | Value |
|---|---|
| Classification | **sync** (warm-up LLM call is fire-and-forget; not a polled task) |
| Latency target | ≤ 1s return |
| Source | `MCPAdapter.tutor_start_session` (`src/study_tutor/mcp/adapter.py:49`) |

**Inputs:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `subject` | `string` | yes | Free text P0; `Subject` enum from Shared Kernel A in P1 |
| `topic` | `string` | no | Free text P0; `Topic` ID in P1 |
| `player_model` | `string` | no | Provider override; falls back to `_default_player_model()` from `AGENT_MODELS__REASONING_MODEL` (SR-03) |

**Output (success):**

```json
{ "session_id": "<uuid>" }
```

**Side effects:**
- Creates a `TutorSession` in the in-memory `SessionStore` with `status="active"`.
- Spawns an `asyncio.create_task(self._warm_up(provider))` to prime the Ollama model. Tracked in `_warmup_tasks` set; never crashes the handler (`# noqa: BLE001`).

**Errors:** none expected at P0.

### 3.2 `tutor_turn`

| Property | Value |
|---|---|
| Classification | **sync** |
| Latency target | p95 < 10s; hard ceiling 30s (SR-07) |
| Source | `MCPAdapter.tutor_turn` (`src/study_tutor/mcp/adapter.py:70`) |

**Inputs:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `session_id` | `string` (UUID) | yes | Returned by `tutor_start_session` |
| `user_message` | `string` | yes | The student's turn |
| `player_model` | `string` | no | Per-call provider override; SR-03 resolution |

**Output (success):**

```json
{ "tutor_response": "<string>" }
```

**Errors:**

| `error_type` | Trigger |
|---|---|
| `SessionNotFoundError` | `session_id` not present in store |
| `SessionEnded` | Session status is `ended` |

**Side effects:**
- Appends a `("user", user_message)` turn, then a `("tutor", response)` turn to `session.turns` (append-only invariant).
- Routes provider via `LLMClient(provider=resolved_provider).generate(user_message, player_prompt)`.
- LLM call runs inside `asyncio.to_thread(...)` so the async MCP framework isn't blocked by httpx.

### 3.3 `tutor_session_status`

| Property | Value |
|---|---|
| Classification | **sync** |
| Latency target | < 2s |
| Source | `MCPAdapter.tutor_session_status` (`src/study_tutor/mcp/adapter.py:102`) |

**Inputs:** `{ "session_id": "<uuid>" }`

**Output (success):**

```json
{
  "session_id": "<uuid>",
  "status": "active" | "ended",
  "turn_count": "<int>",
  "started_at": "<ISO 8601 datetime>"
}
```

**Errors:** `SessionNotFoundError` if `session_id` unknown.

### 3.4 `tutor_session_end`

| Property | Value |
|---|---|
| Classification | **sync** (Phase 0); P1 adds an async Graphiti write-back inside the handler — does not change the classification because the write is fire-and-forget |
| Latency target | < 2s |
| Source | `MCPAdapter.tutor_session_end` (`src/study_tutor/mcp/adapter.py:116`) |

**Inputs:** `{ "session_id": "<uuid>" }`

**Output (success):**

```json
{ "session_id": "<uuid>", "status": "ended" }
```

**Errors:** `SessionNotFoundError` if `session_id` unknown.

**Phase 1 evolution:** TODO comment at `adapter.py:122` — async Graphiti write-back per ADR-ARCH-003. SR-07 invariant: this side effect must **not** appear in the tool description (kept implementation-internal).

## 4. Error envelope

All four tools return errors as a flat dict (not a JSON-RPC error wrapper) so MCP clients see them as successful tool returns with structured error fields. This matches the live handler shape:

```json
{
  "error": "<human-readable message>",
  "error_type": "SessionNotFoundError" | "SessionEnded"
}
```

The closed set of `error_type` values is the contract. Adding a new `error_type` is a contract change requiring `/design-refine`.

## 5. Events emitted (Shared Kernel B)

P0 status: events vocabulary is **reserved** (CC-11). No in-process bus is wired today. The Tutoring context will be the sole producer once Phase 1 lands the Coach + Student Model wiring.

### 5.1 Producer

`Tutoring` only. No other context emits these events.

### 5.2 Event shapes

| Event | Payload (P0 reserved) | Phase live | Consumers |
|---|---|---|---|
| `session.started` | `{session_id, student_id, subject, topic, started_at}` | P1 | Student Model |
| `session.turn_completed` | `{session_id, turn_index, role, ao_scaffolded?}` | P1 | Coach (P1), Student Model (P1) |
| `session.completed` | `{session_id, duration_seconds, topic, aos_touched, quality_score, ended_at}` | P1 | Student Model, Gamification (P2), Reachy (P2 stretch) |

`achievement.unlocked`, `quest.completed`, `quest.expired`, `boss_battle.completed` are emitted by **Gamification**, not Tutoring — see Phase 2 design re-run.

### 5.3 Delivery semantics

- **In-process only.** No NATS, no external broker (CC-11; matches single-user posture from ADR-ARCH-014).
- **Synchronous fan-out is forbidden** — consumers must subscribe via the deepagents 0.5.3 AsyncSubAgent boundary (CC-12) or equivalent async hook; no consumer blocks `tutor_turn` return.
- **At-most-once.** No retry, no DLQ at P0/P1. A consumer crash on `session.completed` does not re-fire the event.

### 5.4 Schema authority

The canonical schemas live in `docs/design/events-schema.yaml`. Consumers validate at the subscriber boundary (Pydantic) per ADR-ARCH-010.

## 6. Versioning

- **Tool surface:** unversioned at P0 (single-user, no external consumers other than Lilymay's own Claude Desktop). Field additions are minor; field removals or `error_type` changes require `/design-refine`.
- **Event surface:** versionless at P0; the Shared Kernel B vocabulary is intentionally stable across phases (`domain-model.md §8.2`).

## 7. Conformance tests (existing)

| Test | Surface | Location |
|---|---|---|
| `test_stdio_discipline.py` | SR-01 (stdout = MCP only) | `tests/unit/mcp/test_stdio_discipline.py` |
| `test_provider_resolution.py` | SR-03 (factory-resolved provider) | `tests/unit/llm/test_provider_resolution.py` |
| Tool-contract test | SR-07 (description ≡ behaviour) | per `domain-model.md §7.2`, recommended addition |

## 8. Out-of-scope explicitly

- **REST / GraphQL / HTTP transport** — deferred indefinitely; ADR-ARCH-008 stands.
- **Multi-tenant authentication** — ADR-ARCH-014 (single-user posture).
- **Caching, rate limiting, feature flags** — ADR-ARCH-011.
- **`tutor_pause_session`, `tutor_resume_session`** — not requested; sessions are append-only and end-once.

## 9. Open questions for downstream phases

1. **P1 — schema growth:** `tutor_start_session` will likely accept `student_id`, `grade_target`, `paper` once Graphiti reads the student model. If Graphiti read latency exceeds 1s, reclassify the tool as **long-running** and add a `tutor_session_status` polling contract (the architecture's original SR-07 stance).
2. **P1 — error envelope evolution:** add `LLMUnavailable`, `ProviderTimeout` once Bedrock/Ollama failure modes are exercised via FEAT-PO-004.
3. **P2 — event consumers fanout:** if Gamification + Reachy + dashboard all subscribe to `session.completed`, evaluate whether the in-process bus needs an explicit subscriber registry or whether deepagents' AsyncSubAgent set is sufficient.
