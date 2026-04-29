# API Contract — Tutoring

**Bounded context:** Tutoring
**Phase:** P0 (live) + P1 forward-design (per ADR-ARCH-019, CC-13)
**Status:** Accepted — design captures live behaviour in `src/study_tutor/mcp/adapter.py` and `src/study_tutor/session/tutor_session.py`; Phase 1 evolution rows align to ADR-ARCH-019 + DDR-002 / DDR-003.
**Generated:** 2026-04-26 by `/system-design` (bias-to-defaults, Phase 0 scope)
**Refreshed:** 2026-04-27 by `/system-design --focus="Tutoring" --context ADR-ARCH-018 / ADR-ARCH-019 / graphiti-latency-spike-results.md` (sweep stale ADR-ARCH-003 references; align to every-write-point fire-and-forget; cross-reference DDR-001).

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

Four tools registered by `MCPAdapter`. SR-07 classification is the truthful classification per the live handler — `tutor_start_session` was reclassified from "long-running" to "sync" by [ADR-ARCH-017](../../architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md) (closes prior design decision D2; partially supersedes ADR-ARCH-008's SR-07 table). The 27 Apr 2026 [Graphiti latency spike](../../research/ideas/graphiti-latency-spike-results.md) corroborates the sync classification on the read side (`search_nodes` median 0.07s) and forces the every-write-point async commitment on the write side (`add_episode` median **78.98s**) per [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) / CC-13. Registered MCP description strings remain silent on Graphiti writes per [DDR-001](../decisions/DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md) (owned by MCP Transport; referenced here, not duplicated).

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

**Phase 1 evolution (per [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) / CC-13):** mid-session Graphiti writes land at *this* handler, not just at `tutor_session_end`. Specifically:

- **Coach-observed misconceptions** — written by the Coach `AsyncSubAgent` (CC-12 / [ADR-ARCH-012](../../architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md)) per [DDR-002](../decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md). The Coach owns its own write surface; the Tutor handler does not aggregate misconception observations.
- **Planner topic-confidence updates** — dispatched from the Tutor handler via the shared Graphiti write helper as `asyncio.create_task(...)` per ARCH-019.

Both sites are **fire-and-forget**: the handler's p95 < 10s and 30s hard ceiling are binding regardless of `add_episode` latency (78.98s median per the [27 Apr spike](../../research/ideas/graphiti-latency-spike-results.md)). Write failures emit a structured log line and **do not** raise from the handler. Per [DDR-001](../decisions/DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md), the registered MCP description string for `tutor_turn` does not enumerate these write sites.

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
| Classification | **sync** — < 2s return regardless of phase. The Phase 1 session-end Graphiti write is fire-and-forget per [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) / CC-13, so it does not enter the caller-facing budget. |
| Latency target | < 2s |
| Source | `MCPAdapter.tutor_session_end` (`src/study_tutor/mcp/adapter.py:116`) |

**Inputs:** `{ "session_id": "<uuid>" }`

**Output (success):**

```json
{ "session_id": "<uuid>", "status": "ended" }
```

**Errors:** `SessionNotFoundError` if `session_id` unknown.

**Phase 1 evolution (per [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md), supersedes the prior session-end-only ADR-ARCH-003 framing):** TODO comment at `adapter.py:122` — fire-and-forget `add_episode` for the session-end `SessionEpisode`, dispatched via the shared Graphiti write helper. The 27 Apr [latency spike](../../research/ideas/graphiti-latency-spike-results.md) measured `add_episode` median 78.98s; awaiting that on the caller path would breach SR-08 / CC-13 by ~15× the 5s threshold and 39× the 2s handler budget.

Implementation invariants:
- The handler returns `{ session_id, status: "ended" }` on the `active → ended` state transition; **does not** wait on Graphiti acknowledgement.
- Write failures emit a structured log line; they do not raise from the handler and are not surfaced to the caller (fail-soft per ARCH-019).
- Per [DDR-003](../decisions/DDR-003-session-completed-emits-on-state-transition.md), the `session.completed` event (Shared Kernel B) emits on the same state transition — *not* on Graphiti write success. Consumers (Student Model, Gamification) treat the event as the source of truth; the Graphiti episode is a secondary persistence artefact.
- Per [DDR-001](../decisions/DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md), the registered MCP description string for `tutor_session_end` does not enumerate this write (SR-07 / CC-07).

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
- **Event emit is decoupled from Graphiti write success** per [DDR-003](../decisions/DDR-003-session-completed-emits-on-state-transition.md) (every-write-point fire-and-forget, ARCH-019 / CC-13). `session.started` emits on the `→ active` transition; `session.turn_completed` emits after the `(user, tutor)` pair appends; `session.completed` emits on the `active → ended` transition. None of these emits await any Graphiti `add_episode` acknowledgement. The event vocabulary is the consumer-facing source of truth; Graphiti episodes are a secondary persistence artefact whose absence is observable on the next session-status read but does not block the event bus.

### 5.4 Schema authority

The canonical schemas live in `docs/design/events-schema.yaml`. Consumers validate at the subscriber boundary (Pydantic) per ADR-ARCH-010.

## 6. Versioning

- **Tool surface:** unversioned at P0 (single-user, no external consumers other than Lilymay's own Claude Desktop). Field additions are minor; field removals or `error_type` changes require `/design-refine`.
- **Event surface:** versionless at P0; the Shared Kernel B vocabulary is intentionally stable across phases (`domain-model.md §8.2`).

## 7. Conformance tests

### 7.1 Existing

| Test | Surface | Location |
|---|---|---|
| `test_stdio_discipline.py` | SR-01 (stdout = MCP only) | `tests/unit/mcp/test_stdio_discipline.py` |
| `test_provider_resolution.py` | SR-03 (factory-resolved provider) | `tests/unit/llm/test_provider_resolution.py` |
| Tool-contract test | SR-07 (description ≡ behaviour) | per `domain-model.md §7.2`, recommended addition |

### 7.2 Recommended additions (Phase 1)

| Test | Surface | Notes |
|---|---|---|
| Handler-latency test | CC-13 / SR-08 — `tutor_turn` p95 < 10s and `tutor_session_end` < 2s when the Graphiti write helper is patched to sleep ≥ 30s | Symmetric with the I-MCP8 test recommended in [`API-mcp-transport.md §10`](API-mcp-transport.md). Validates that no caller-facing path awaits Graphiti, even under pessimistic write-side latency (78.98s median per [27 Apr spike](../../research/ideas/graphiti-latency-spike-results.md)). |
| Event-emit-without-write test | DDR-003 — `session.completed` is emitted on state transition even when the Graphiti write helper raises | Asserts the fail-soft separation between the events bus (Shared Kernel B) and Graphiti persistence. |

### 7.3 Adjacent enforcement (cross-context, not duplicated here)

- **SR-07 substring test** — DDR-001 is enforced inside MCP Transport via [`API-mcp-transport.md §10` / `DM-mcp-transport.md §6` invariant I-MCP9](../models/DM-mcp-transport.md). The Tutoring contract relies on that test; it is not duplicated here because the registered MCP description strings are owned by `src/study_tutor/mcp/server.py` (MCP Transport), not by Tutoring.
- **CC-14 inference parameters** — explicit `num_ctx` / `num_predict` is enforced in the [Inference Runtime contract](API-inference-runtime.md) and data model. Tutoring inherits the guarantee through the `LLMClient` boundary; no Tutoring-side test is required.

## 8. Out-of-scope explicitly

- **REST / GraphQL / HTTP transport** — deferred indefinitely; ADR-ARCH-008 stands.
- **Multi-tenant authentication** — ADR-ARCH-014 (single-user posture).
- **Caching, rate limiting, feature flags** — ADR-ARCH-011.
- **`tutor_pause_session`, `tutor_resume_session`** — not requested; sessions are append-only and end-once.

## 9. Open questions for downstream phases

1. **P1 — schema growth + sync-classification reversion (per [ADR-ARCH-017](../../architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md)):** `tutor_start_session` will likely accept `student_id`, `grade_target`, `paper` once Graphiti reads the student model. ADR-ARCH-017 codifies a measurement-conditional reversion rule: revert to **long-running** + add a `tutor_session_status` polling contract iff `search_nodes` median exceeds ~3s at session-start read. The 27 Apr spike measured `search_nodes` at 0.07s, so the condition is not triggered today; re-evaluate after each Phase 1 milestone that adds a new read path.
2. **P1 — error envelope evolution:** add `LLMUnavailable`, `ProviderTimeout` once Bedrock/Ollama failure modes are exercised via FEAT-PO-004.
3. **P2 — event consumers fanout:** if Gamification + Reachy + dashboard all subscribe to `session.completed`, evaluate whether the in-process bus needs an explicit subscriber registry or whether deepagents' AsyncSubAgent set is sufficient.
4. **P1 — flush-point ownership (resolved by [DDR-002](../decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md), 2026-04-27):** Coach `AsyncSubAgent` owns its own misconception writes; Tutor handler owns the planner topic-confidence updates and the session-end episode. Open follow-up: when the Session Planner becomes its own deepagents component (rather than Tutor-handler-internal logic), revisit whether it migrates to the AsyncSubAgent boundary too.
5. **P1 — write-failure observability:** structured-log line per failure (today's plan), aggregate counter, or both? Recommend both once Phase 1 lands more than one write site, so demo-week inspection can distinguish "one transient failure" from "every write failing". The structured-log line is mandatory (CC-13); the counter is a polish item.
6. **P1 — flush-point taxonomy in `DM-tutoring.md §11`:** if more than the two foreseen mid-session flush sites land (misconceptions, topic-confidence), reify a `FlushPoint` value object so each site has a stable name in logs/metrics. Deferred until a third site appears.
