# HANDOFF — the double-active server build (fresh spark session, 2026-08-04)

> **✅ DONE 2026-08-04 (same day, spark)** — built, adversarially reviewed
> (16-agent pre-deploy pass; 2 would-be blockers refuted empirically, 4
> confirmed findings fixed incl. the MCP door now RESUMING), deployed, and
> live-proven. Receipts: commit `19a0211`, migration head `346cd366b66e`,
> safety dump `pre-one-active-migration-20260804.sql`, hermetic 1709/0,
> plan Tutoring-core + Suites rows, known-issues tail (the Mac's promotion
> instruction). Retained as the build's design record — do not re-work.

**Written:** 2026-08-04 on the spark, at origin/main `d95add0`, as the prior
spark session ran out of context. **One build task carries over** — everything
else from the 2026-08-04 server queue
([`HANDOFF-spark-server-queue-2026-08-04.md`](HANDOFF-spark-server-queue-2026-08-04.md))
is DONE, deployed, and ledgered.

## Ground yourself first (non-negotiable)

1. Root [`CLAUDE.md`](../../CLAUDE.md) → the mission
   ([`study-tutor-mission-statement-2026-08-01.md`](../study-tutor-mission-statement-2026-08-01.md))
   + THE PLAN ([`study-tutor-plan-of-record.md`](../study-tutor-plan-of-record.md)).
   Sessions end by updating the plan/known-issues cells they move; known-issues
   discipline: fix one, delete its section.
2. [`known-issues.md`](known-issues.md) — the "Per-turn text-following" entry's
   tail carries THE RULING this handoff builds (quoted below).
3. `git pull --ff-only` before anything — the Mac pushes to the same main.

## Standing fences (verbatim)

- Six-verb contract + §7 frozen: **no shape edits** — this build is a semantics
  normalisation recorded as a **dated in-place annotation** in
  `docs/design/contracts/API-session-http-binding.md` (the §2.2 subject-filter
  annotation, 2026-08-02, is the exact precedent for form).
- Broker isolation: never connect to any NATS broker.
- Hermetic-first: `uv run pytest -m "not integration and not live and not
  keycloak" -q` green before any deploy (baseline: **1701 passed, 0 failures**).
- Division of labour (standing since 2026-08-03): **spark = server side, Mac =
  `app/` only.** The Mac's interlock for this build is one line (below).

## THE BUILD: `resume_if_active: false` → end-then-create (Rich's (b) ruling)

**The ruling (Rich, 2026-08-04, in-session):** option (b) — the service
normalises `start_session(resume_if_active=False)` when an active
`(student, subject)` session exists to **end the active session, then create
fresh** ("one-active by construction"). No new failure mode, no contract shape
change (`resumed: false` in the response already covers it).

**Why (receipt):** `create_session` (`store/postgres.py`, the
`resume_if_active` branch ~line 1577+) unconditionally INSERTs when the flag is
false — no unique-active constraint exists — so a second active
`(student, subject)` session is mintable, corrupting the one-active model that
D8 cross-device pickup (`last_activity DESC LIMIT 1`) relies on. The app no
longer exercises the path (it sends `true` + a `resumed` backstop since
`69d7d5f`), but the robot and future clients can.

**The fake is already the reference:** the Mac implemented (b) in
`FakeSessionApi` (`bb5a4fa`, pinned by
`app/test/unit/fake_start_fresh_semantics_test.dart` — TWO hermetic pins).
**Read those two tests first and mirror their semantics exactly** — fake and
server must agree by test, not by hope.

### Design sketch (adjust to what the code prefers, but keep the semantics)

1. **Service-level normalisation** (`session/service.py`, `start_session` —
   note it already normalises empty subjects to `SUBJECT_DEFAULT` at the top,
   ADR-ARCH-032 D4; this lands beside that): when `resume_if_active` is False,
   end any active `(student_id, subject)` session BEFORE creating. "End" should
   ride the real end path so settlement/gamification bank properly — look at
   how `end_session` / `finalize_session` compose (the ended session settles;
   an abandoned-by-start-fresh session should not lose its XP). Check what the
   FAKE does about settlement in its (b) pins and match.
2. **The DB backstop** (recommended in the ruling discussion, silent in normal
   flow): a **partial unique index** on `(student_id, subject) WHERE
   status='active'` — new alembic revision on head `d5a9c2e7f814`, following
   its file's conventions + the mandated `schema_reference.sql` hand-sync.
   Mind the ordering inside the service so the index never fires on the
   normalised path. Run against the NAS with the usual safety dump first
   (prior dump: `/opt/study-tutor/backups/pre-subject-migration-20260802.sql`;
   make a fresh one, same pattern).
   ⚠ Pre-check on live data: `SELECT student_id, subject, count(*) FROM
   session WHERE status='active' GROUP BY 1,2 HAVING count(*)>1;` — if any
   existing double-actives exist, end the older ones (via SQL status flip is
   acceptable for strays; note counts in the receipt) BEFORE creating the
   index, or the migration fails.
3. **Binding annotation**: dated in-place note on the `start_session` row /
   §2.1-adjacent text: `resume_if_active: false` semantics clarified
   2026-08-04 (end-then-create; one-active invariant now structural). No
   re-pin.
4. **Hermetic pins (server)**: mirror the fake's two tests at the service
   level (start-fresh ends the previous active session — and it SETTLES;
   the new session is created; `resumed=false`; other students/subjects
   untouched). Suite green (1701 baseline).
5. **Deploy** (the ritual below) and tell the Mac: *"(b) is deployed —
   promote the pin into the shared s5 contract body."* That's its whole
   interlock; then edit the known-issues tail per its own instruction
   ("PROMOTE the pin … then delete this note") — the Mac deletes after its
   promotion run, or you coordinate in one fold.

## Deploy ritual (as run four times on 2026-08-03/04 — copy it)

```bash
# 0. Check no one is mid-session (Lilymay uses this for real now):
docker run --rm postgres:16 psql "$STUDY_TUTOR_PG_DSN" -tAc \
  "SELECT session_id,last_activity FROM session WHERE status='active' AND last_activity > now() - interval '10 minutes';"
# 1. Hermetic suite green, commit, push (pull --ff-only first).
# 2. Migration (if the backstop index ships): fresh safety dump, then
#    STUDY_TUTOR_PG_DSN=<from deploy/http/.env> uv run alembic upgrade head
# 3. TAG=latest ./scripts/docker-build.sh && docker tag study-tutor:latest study-tutor:kc-a2
# 4. cd deploy/http && docker compose up -d \
#    && docker compose -p study_tutor_http_kc -f docker-compose.yml -f docker-compose.keycloak.yml --env-file .env.kc up -d
# 5. healthz both; boot log shows rag_wired + voice_services_wired;
#    live-prove the new behaviour (two starts with resume_if_active:false as
#    suite-runner via <bearer-suite> — second start ends the first; counts via psql).
```

## State of the world (verified 2026-08-04, origin `d95add0`)

- **Prod `:8100`/`:8101`**: image from `6d1c8e5`-era main — verified streaming
  (ADR-ARCH-027), incremental think filter, subject-scoped RAG, scoped
  authenticated `__dev__/reset`, VoiceConfig fail-loud. Both healthy.
- **Dev token table** (`deploy/http/.env`, gitignored, reconstructed +
  verified): `<bearer-lilymay>`→`lilymay`, `<bearer-alex>`→`alex`,
  `<bearer-suite>`→`suite-runner` (student row seeded). kc mode (`:8101`) uses
  Keycloak, table unused there.
- **Suites**: python hermetic 1701/0; dart 423/423; live 48/48 as
  `suite-runner` in 6:44 (2026-08-04, post-isolation — lilymay's rows
  byte-identical across the run).
- **NAS Postgres** at migration head `d5a9c2e7f814`; nightly dumps; the
  2026-08-03 transcript wipe is an **accepted loss** (dated in the plan — do
  not reopen).
- **Voice env pins** (load-bearing): `STT_MODEL=parakeet-tdt-0.6b-v3`,
  `TTS_MODEL=qwen3-tts-0.6b`, base URLs `host.docker.internal:9000/v1`.
- **llama-swap `:9000`** serves `gemma4-tutor`, coach, `embed` (Qwen3, 1024-dim
  — matches the baked re-embedded store), speech models. Read-only for build
  lanes; memory has operational gotchas.

## NOT this session's scope (unless Rich says so)

- Attended: iOS voice walk; Lilymay's own phone install (both Rich's).
- Roadmap weight (Rich's words): Lane 1 step 3 content packs (his scans) and
  Lane 1 step 1 subject evals (`fleet-evals` repo) — the non-code work.
- Lane 6 step 1 robot re-point (fleet-gateway host runbook); Lane 3 residency
  ADR (unblocked, awaits Rich's want).
- Known small debts staying put: per-turn text-following (design-deferred),
  citation anchors + golden-quote eval harness (Lane 2 step 3), the
  MCP-superseded question. One UNLEDGERED observation from the ADR-027 build:
  `stream_with_audio_refs` synthesizes inline, so token forwarding stalls
  ~per-piece during TTS — an overlap/queue would smooth text delivery further;
  ledger it if you touch that file.

## Session-end ritual

Hermetic green → deploy → live receipts named → fold known-issues (delete the
ruled tail once promoted) + the plan's rows → push. The Mac picks up from
origin.
