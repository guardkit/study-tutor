# Spec — Adaptive Loop Repair + Gamification Engine (Lane B, GB10)

**Status:** BINDING spec for the Lane B orchestrated build — 2026-07-12. Build to it verbatim; do not redesign. On any conflict with code reality, the spec's *intent* wins and a dated note is filed here. Parent doc: `docs/research/ideas/gamification-engine-and-app-ux-scope-and-build-plan.md` (decisions D1–D14, rulings R1–R13 — all recommendations adopted 2026-07-12 unless Rich reopens them).
**Upstream (binding, read in full before building):** `docs/gamification/design.md` (economy contract) · ADR-ARCH-023 · `docs/design/contracts/API-session-http-binding.md` · `docs/design/contracts/API-session-cross-device.md`.
**Verified ground truth as of `main` @ `a81ec5d`** — re-verify on the box before building.

---

## §1 W0 — session-end ordering fix (own commit, precedes everything)

1. **Failing test first**: an integration test driving the *composed service path* against self-provisioned Postgres — `SessionService.start_session → turn(s) → end_session(completion=…)` — asserting the confidence row and misconception rows actually land. This fails today because `end_session` (`session/service.py:406-416`) calls `store.end_session` (status→'ended', own txn) before `record_session_completion`, whose gate is `ON CONFLICT … WHERE status != 'ended'` (`postgres.py:780-794`).
2. **Minimal fix**: reorder so the completion write performs (or precedes) the status transition; do NOT build `finalize_session` yet (that is §4). Fake store idempotency must be aligned to status-based semantics (`fakes.py:222-224` + fake `end_session`) so fakes and Postgres agree.
3. **Audit**: count sessions with `status='ended'` and no confidence/misconception children since 2026-07-09 (post NAS-wipe scope: one student, days of data); record the count in the PR description. No data reconstruction is attempted.

## §2 B0 — adaptive-loop repair (D13/D14)

### §2.1 Planning moves into the core (D14)
- `SessionService.start_session` invokes `plan_session` under the existing 2.0 s budget/degrade pattern (`mcp/adapter.py:265-299` is the reference to *relocate*, then delete from the adapter along with `self._plan_sessions`).
- Plan facts persist on the session row at start: `topic` (exists), plus new columns `text_name TEXT NULL`, `focus_aos` (reuse existing `aos_scaffolded` session column at start-time, or add `planned_aos` if that column's end-time semantics must be preserved — builder decides, coach verifies both readers updated). `opening_prompt` is NOT persisted; it is returned in the start response.
- Planner inputs fixed: pass `ao_mapping` (from the curriculum/AO source the planner already understands) and `session_completions` (recent ended sessions from the store) — today both default empty (`adapter.py:268`, `pipeline.py:215,339`), which blanks `focus_aos` and makes every misconception "unrevisited".
- Read-key fix: `plan_session` must be keyed by the same identity the confidence writes use (ownership `student_id`, `wiring.py:52`), not the MCP tool's subject slug (`adapter.py:227-251`).
- HTTP `POST /api/sessions/start` response gains additive fields `topic`, `opening_prompt`, `focus_aos` (contract addendum, §6.2). MCP keeps its `plan_summary` shape, now sourced from the service's plan.

> **Builder note — 2026-07-12 (S-R3, plan-fact persistence choice).** §2.1 left the builder two options for persisting `focus_aos` at start without a Phase-R migration; **S-R3 took the first — reuse the existing `aos_scaffolded` session column at start-time.** `SessionService.start_session` now persists `plan.topic_name` into `session.topic` and `plan.focus_aos` into `session.aos_scaffolded` on the created row (`create_session` gained an additive `aos_scaffolded=` kwarg; both readers — the Postgres adapter and the fake — already surface the column verbatim, so no reader changed semantics). This is honest because the end-of-session write already set `aos_scaffolded` to the plan's `focus_aos` (the completion carries it), so start and end now agree on the same value; `end_session` reads the persisted `aos_scaffolded` back to assemble the completion, giving byte-identical writes across HTTP and MCP. A **distinct `planned_aos` column** (to separate "planned focus AOs" from "AOs actually scaffolded" once per-turn scaffold signals exist) is **deferred to the §3 Phase-E migration**. `text_name` persistence remains Phase-E (S-E4); `opening_prompt` is returned in the start response only, never persisted.

> **Builder note — 2026-07-12 (S-E1, planned_aos NOT added).** The §3 Phase-E migration (revision `b7d1e4f92a3c`) **did not add `planned_aos`.** Per-turn scaffold signals already have a durable home on the EXISTING `session_turn.ao_scaffolded` column (set per turn, not on the session row), so the "AOs actually scaffolded" series is reconstructable from the turns without splitting the session-row column. `session.aos_scaffolded` therefore keeps its coherent dual start/end role (S-R3): the plan's `focus_aos` at start, the same value read back to assemble the completion at end. Adding `planned_aos` now would create a second, redundant session-row column with no reader — a YAGNI violation. `b7d1e4f92a3c` adds only the required `session.text_name` (S-E4 will populate it; the §4.2 finalize RETURNING reads it) plus `session.settled_at`, `achievement.session_id`, and `topic_confidence_history`. If a future stage needs "planned vs actual focus AOs" separated at the session-row grain, it adds `planned_aos` then and moves both readers.

### §2.2 Planner rules upgraded to design.md §6.3 verbatim (R11)
Priority order after Rule 1 (learner override): **(a)** any topic in Struggling band (<40) regardless of recency; **(b)** weakest topic below Mastered not studied in the last **3 days** (replaces the 48 h ASSUM-001 cooldown, `rules.py:65,163-167`); **(c)** anti-repetition: never recommend the topic that was recommended the previous **4 consecutive London days** (needs recent-plans lookback — derivable from persisted session plan facts, §2.1); **(d)** existing Rule 4 (unrevisited misconception) and Rule 6 (random from Developing) keep their slots. Mastered-band topics are excluded from (b). All day arithmetic in Europe/London (D6).

### §2.3 Confidence bootstrap (R12)
`build_session_completion` creates a `ConfidenceUpdate` for **first-seen topics at baseline 50** (mid-Developing) before applying the session delta — i.e. drop the `if current_confidence is not None` guard (`completion.py:140`); the store write is already an upsert deriving band + `last_revised_at` (`postgres.py:839-864`). The baseline constant lives beside the economy constants (§4.4) and is ratified into design.md §13.

### §2.4 Completion assembly moves into the core (D14)
`build_session_completion` is invoked inside `SessionService.end_session` for ALL transports; the MCP adapter passes only its topic hint. The HTTP handler's `completion=None` (`http/app.py:369`) is deleted. TASK-APP1-04 is closed with a dated note.

### §2.5 Session context reaches the Player
- `SessionState` (`tutoring/adapters/session_state.py:30-44`, a declared breaking-change contract — coordinate both adapters) gains: `topic_confidence_band: str|None`, `weakest_topics: tuple[str,...]` (≤3), `recent_misconceptions: tuple[str,...]` (≤3), `grade_target: str|None` (from student profile; GOAL.md §7 default Grade 6).
- Populated once, in the service, from a single store read per turn (or cached per session) — never in transport adapters.
- `LLMPlayerAdapter.respond/respond_stream` weaves a compact "Session context" block (topic, text, band phrasing per design §6.1, misconceptions-to-revisit, grade-target register per GOAL.md §7) into the generation prompt via the reserved seam (`llm_player_adapter.py:149-159`). The block is ≤ ~120 words, assembled from typed fields — no free-form store text.

### §2.6 In-session memory (R13)
Player generation includes a transcript window: last **12 turns**, token-capped (cap constant beside the prompt assembly, oldest dropped first), rehydrated from the durable store via the service. Applies to `respond` and `respond_stream`. `LLMClient.generate` (`llm/client.py:178-185`) gains a messages-list path; single-message callers unchanged.

### §2.7 Voice/WS wiring parity (§1.2 placeholders — verify on the box first)
- REST voice turn: wire the real orchestrator `ReplyFn` factory into `VoiceTurnService` (`voice/service.py:328-351`, wiring `cli/main.py:948-953`) — the placeholder echo is deleted.
- WS streaming: provide a real `ReplyStreamFn` factory (async-iterator product) where `ws.py:190-192` currently passes the non-streaming `ReplyFn`; add a test that drives one WS turn end-to-end against the fake LLM.
- If runtime verification on the GB10 shows different wiring than `main` (deployment drift), file a dated note and build against `main`.

> **Builder note — 2026-07-12 (S-R4, box verification).** Read-only `docker exec cat` on `study_tutor_http` (`/workspace/study-tutor/src/study_tutor`) confirms the deployed wiring **matches `main`** — no drift: `voice/service.py` still holds the placeholder echo `_create_reply_fn` ("I understand your question: …") at the turn seam, and `http/ws.py` still passes `app.state.reply_fn_factory` (the non-streaming `ReplyFn`) into `turn_stream`'s `reply_stream_fn` slot. S-R4 therefore built against `main`. S-R4 wiring: REST voice turn now drives the real orchestrator via an injected `reply_fn_factory` (echo deleted); WS streaming gets a real `ReplyStreamFn` factory (`_build_http_reply_stream_fn_factory` → `SessionService.build_turn_session_state` → `PlayerCoachOrchestrator.run_turn_stream_tokens`, a new token-yielding seam). Player context (§2.5) and the in-session memory window (§2.6) are assembled once in `SessionService.build_turn_session_state` and consumed by both transports (D14) — never in an adapter.

## §3 B1 — migration (second Alembic revision ever; `down_revision='3c7cd4bca034'`)

Adds, following the initial revision's conventions exactly (TIMESTAMPTZ via `sa.TIMESTAMP(timezone=True)`, `<table>_<col>_check` / `_fkey` / `_pkey` names, `<table>_<purpose>_idx`):
1. `session.settled_at TIMESTAMPTZ NULL` — the settlement work-queue marker.
2. `achievement.session_id TEXT NULL REFERENCES session` — replay support (D1).
3. `topic_confidence_history (id BIGSERIAL PK, student_id TEXT NOT NULL REFERENCES student ON DELETE CASCADE, topic_name TEXT NOT NULL, percentage INTEGER NOT NULL CHECK (0<=percentage<=100), session_id TEXT NULL, recorded_at TIMESTAMPTZ NOT NULL, source TEXT NOT NULL)` + `topic_confidence_history_recent_idx ON (student_id, recorded_at DESC)` — modeled on the `misconception` table. Written by §2.3/§4 settlement from day one (D2 — unbackfillable).
4. Session plan-fact columns per §2.1 if the builder chose new columns.
Also in this stage: update the hardcoded inventories in `tests/knowledge/store/test_migration_schema.py` (7 tables → 8, index set, downgrade-base list); the new revision's `downgrade()` covered; any new self-provisioning test module claims a fresh container name + port (55433/55434 taken; use 55435); **never read the env DSN in migration tests** (root `conftest.py:30-50` guard stays untouched). `schema_reference.sql` becomes a **living reference**: update its DDL and replace the "byte-for-byte first migration" framing in both files with "kept in sync by hand; `alembic upgrade head` is the source of truth".

## §4 B2 — engine + finalize_session

### §4.1 Pure core
`src/study_tutor/gamification/engine.py`: `decide(prior: PriorFacts, session: SessionFacts, now: datetime) → GamificationDecision {xp_awarded, total_xp_after, level_before, level_after, level_up, streak_days, streak_extended, unlocked: [AchievementAward{id, name, xp}] , near_achievements: [NearAchievement{id, name, progress, target, hint}]}`. No I/O; injected clock; London-day helpers shared with the projection. Reuses (moves) the level table and band functions from the R05 module, whose docstring already declares itself superseded.

### §4.2 finalize_session (single transaction, replaces the two-call sequence)
Order within one `engine.begin()`: **(1)** `UPDATE session SET status='ended', last_activity=:now … WHERE session_id=:sid AND status='active' RETURNING started_at, topic, text_name, …` — the sole gate; a non-matching UPDATE means already-ended → **replay path**: read banked `xp_awarded` + achievements where `achievement.session_id=:sid` and return the identical decision. **(2)** read prior facts (SUM xp, session dates for streaks, confidence rows, achievement ids held). **(3)** engagement facts: `SELECT min(ts), max(ts), count(*) FROM session_turn WHERE session_id=:sid` — engagement duration = max−min; zero rows → 0 XP, still settled (D5). **(4)** savepoint (`begin_nested()`): call `decide()`; write `session.xp_awarded` **and `settled_at=:now`** (stamped inside the savepoint so a fault leaves it NULL for the sweep, no compensating update needed), insert achievement rows (`ON CONFLICT DO NOTHING`, with `session_id`), append `topic_confidence_history` rows, run the existing confidence/misconception helpers. On any settlement exception: roll back to the savepoint, commit the end, log at ERROR (D3). **(5)** post-commit: the service emits `session.completed` with an `events-schema.yaml`-conforming payload (D8 — schema doc revised in the same stage; `subject_slug` carries the actual subject; emit-after-commit replaces DDR-003's emit-before-write, noted in the ADR). `record_session_completion` is reduced to a thin wrapper or deleted; the phantom-insert branch (`postgres.py:764-776`) does not survive (unknown session ⇒ `SessionNotFoundError`).

### §4.3 Sweep CLI
`study-tutor settle-sessions` click subcommand (modeled on `seed-students`, `cli/main.py:980`): settles every `status='ended' AND settled_at IS NULL` session through the same `decide()`; idempotent; per-row logging; engagement fallback to `started_at/last_activity` when a session has no turns. It is the recovery path AND the one-time historical backfill. Running it against the live NAS store is an **attended** operation, never an unattended stage.

### §4.4 Economy constants (ratified values — design.md §13 patch ships in the docs stage)
`src/study_tutor/gamification/economy.py`: XP bands on engagement seconds `<120→0 · <900→60 · <1500→120 · ≥1500→180`; 15 level thresholds verbatim (0/100/300/600/1000/1500/2200/3100/4200/5600/7300/9400/11900/14900/18500); streak milestones 3/7/14/30/60/100; timezone `Europe/London`; confidence baseline 50; cascade order streak → XP milestones → level milestones, iterated to a fixed point (D7). **Any change here requires the matching design.md edit in the same commit.**

### §4.5 W1 achievement catalog (16 — computable from session rows alone)
Consistency: `first_steps` +50 (first completed ≥2-min session — R4) · `three_day_run` +100 · `week_one` +200 · `fortnight_force` +400 · `thirty_days` +800 · `sixty_strong` +1200 · `century` +2000 (streak milestones) · `morning_star` +150 / `evening_scholar` +150 (5 sessions *started* before 09:00 / after 19:00 London; abandoned sessions don't count — R3). Milestone: `first_century` +50 (100 XP) · `kilo` +100 · `five_kilo` +250 · `ten_kilo` +500 · `scholar` +300 (L6) · `master` +700 (L10) · `grandmaster` +2000 (L15). IDs are stable snake_case strings; names/XP per design.md §5. `no_weak_spots` is **deferred to B4** with its ≥5-topics guard (R5). Near-achievement hints are static per-achievement strings with progress interpolation.

## §5 B3 — projection swap + API

- `get_gamification_state` switches to banked reads: `total_xp = SUM(session.xp_awarded) + SUM(achievement.xp_awarded)`; streak/longest-streak derived from ended-session London dates (existing pure functions, re-based); `recent_xp` keeps its 7-day window. Duration-derivation is deleted; the port docstring (`port.py:92-97`) re-documented.
- `GET /api/student-model` additive enrichment (§6.2 addendum): `total_xp`, `level_number`, `xp_into_level`, `xp_to_next_level`, `longest_streak`, `recent_achievements: [{id,name,unlocked_at,xp_awarded}]` (last 5), `near_achievements` becomes `[{id,name,description,progress,target,hint}]` (top 3), `next_unlock: {level, feature}`. Existing fields keep exact names/semantics; `data_available` unchanged.
- `POST /api/sessions/{id}/end` response gains **nullable** `gamification: {xp_awarded, total_xp, level_number, level_name, level_up, achievements_unlocked:[{id,name,xp}], streak_days, streak_extended}` — contract **Revision 2** (§6.1). MCP `tutor_session_end` gains the same block via its own contract addendum.
- Test plan: pure band/level tests survive as §13 pins (inputs become engagement seconds); projection/streak tests rewritten against banked facts with London cases crossing UTC midnight (e.g. 23:30 UTC summer study = next London day); concurrent double-end test asserting exactly-once settlement + identical replay payloads; the R05 endpoint tests extend (shape grows, old fields identical).

## §6 Contract actions (docs precede code; /design-refine)

1. **Revision 2** of `API-session-cross-device.md` §5 (`end_session` response) — first-ever original-verb shape change: re-pin CONTRACT_SHA in the binding header, record new BINDING_SHA, note "nullable block; absent until the engine settles the session".
2. **Additive addenda** to `API-session-http-binding.md` §2.2 (student-model enrichment) and for `start_session` response fields (§2.1: `topic`, `opening_prompt`, `focus_aos`). No SHA re-pin for addenda.
3. `events-schema.yaml` revised honestly: `session.completed` payload matches the actual emit (post-commit), `subject_slug` semantics fixed, the Graphiti-era delivery rationale rewritten, gamification events documented as "derived at settlement; delivered via API responses; bus emission deferred".
4. Courtesy note to fleet-gateway (no code change required — it passes the student-model dict opaquely): near_achievements now carries objects; Scholar's narration prompt may want to mention `progress`/`target`.

## §7 Out of scope (Lane B) — do not build

Daily challenges · quests · Boss Battles · streak freeze · XP bonuses/×1.25 multiplier · confidence→difficulty linkage · parent endpoints (KC-D5) · event-bus subscribers · any MCP-adapter logic the HTTP path lacks (D14) · Keycloak integration (table-token auth stands, D10).

---

*Written 2026-07-12 from the verified reviews in the parent scope doc (runs `wf_29f79e88-efd`, `wf_70d314d1-ce4`, `wf_f41e9839-be8`). All rulings R1–R13 adopted at their recommended values; reopening one reopens only its named section.*
