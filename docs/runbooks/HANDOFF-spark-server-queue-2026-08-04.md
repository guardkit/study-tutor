# HANDOFF — the server-side queue (spark session; from the Mac, 2026-08-04)

**Date:** 2026-08-04 (written on the Mac at origin `5ecbc7d`; Rich's word:
"next steps on the server").
**Division of labour (standing, 2026-08-03):** spark = server side, Mac = `app/`
client only. This handoff is the server half of the exits ledgered in
[`known-issues.md`](known-issues.md) after the 2026-08-03 walks; the Mac's
blocked counterpart legs are named per item.

## Ground yourself first (non-negotiable)

1. Root [`CLAUDE.md`](../../CLAUDE.md) → the mission + THE PLAN
   ([`study-tutor-plan-of-record.md`](../study-tutor-plan-of-record.md)).
   Sessions end by updating the plan/known-issues cells they move — known-issues
   discipline: fix one, delete its section.
2. [`known-issues.md`](known-issues.md) — items 1–4 below all have entries with
   receipts; this doc adds the design sketches and the Mac interlocks, nothing
   else. If a decision lands, fold it THERE (and the plan), not here.
3. Fences: the six-verb contract + §7 stay frozen (no shape edits); broker
   isolation stands; hermetic-first (`uv run pytest -m "not integration and not
   live and not keycloak" -q` green before any deploy).

## State anchors (verified from the Mac, 2026-08-04)

- origin/main `5ecbc7d`; suites: python hermetic 1673+ green (your last run),
  dart 421/421, live 48/48 (2026-08-03 — but see item 1 before ANY re-run).
- Prod `:8100`: verified streaming live + device-walked; never-a-silent-resume
  app fix shipped (`69d7d5f`) and on the Samsung.
- The live store's session history before 2026-08-03 ~16:56Z is DELETED (item 5).

## The queue, in priority order

### 1. Suite isolation — dedicated suite student + per-student reset (GATING)

**Why (receipt):** `test_live` signs in as the REAL primary student
(`<bearer-lilymay>`) and its `reset()` hits `POST /__dev__/reset`, which
`truncate_sessions()` — the WHOLE session+turn store, all students
(`src/study_tutor/http/app.py` ~line 591). Yesterday's three runs wiped all
transcripts before ~16:56Z, and stray `subject:'maths'` test sessions (shared
contract bodies, s4/s9) surfaced on Home as real-looking cards — Rich resumed
one believing it was Lilymay's Macbeth session.

**Ask (design sketch — adjust as the code prefers):**
- Add a dedicated suite identity to the dev token table (e.g.
  `<bearer-suite>` → student `suite-runner`). The dev table is deployment config
  (env), not contract — verify no binding edit is needed (the binding §3 names
  the table's EXISTENCE; entries are config).
- Make `__dev__/reset` scope to the CALLER's student (derive from the bearer,
  same as every verb) — or add a `?student=` guard — so a suite reset can never
  touch another student's rows. Whole-store truncate should stop existing or
  require an explicit flag.
- Hermetic pins for both (the reset route currently has none visible).

**Mac interlock:** the moment this deploys + the token lands in the dev table,
the Mac re-points `test_live` at the suite identity and adds
end-own-sessions teardown, then re-runs the live suite for a fresh Suites-row
receipt. Tell the Mac the token/student names — that's the whole interface.

### 2. `VoiceConfig.from_env` code-default trap

Already ledgered (known-issues, Voice): with env unset the defaults resolve to
the retired GB10 host + dead model aliases — the exact mechanism that silently
killed voice 2026-07-26→08-03. Exit as written there: point the defaults at the
spark-era values (update their doctests together) or fail loud at boot on empty
model names. Small; do it while you're in the file.

### 3. The double-active seam: `start_session(resume_if_active: false)`

**Receipt (Mac review, verified in code):** `create_session`
(`store/postgres.py` ~1577-1612) unconditionally INSERTs when
`resume_if_active` is false — no unique-active constraint in
`schema_reference.sql` — so a second active `(student, subject)` session is
mintable, which corrupts the one-active model D8's cross-device pickup
(`last_activity DESC LIMIT 1`) relies on. The app no longer exercises this path
(it sends `resume_if_active: true` with a `resumed` backstop since `69d7d5f`),
but the robot and any future client can.

**Ask:** a ruling + guard. Options: (a) partial unique index on
`(student, subject) WHERE status='active'` + a typed 409/conflict… careful:
that's a CONTRACT question (new failure mode on a frozen verb) — likely needs
Rich; (b) service-level normalize (treat `false` as "end-then-create" or
"resume anyway" — semantics change, also Rich); (c) document-and-monitor.
Whatever the ruling, pin the chosen behaviour in the hermetic suite and note
the fake-fidelity gap (`FakeSessionApi` mirrors today's INSERT behaviour —
keep fake and server aligned with whatever you choose).

### 4. Two smalls (batch with the above)

- WS text-leg field: `websocket_endpoint` reads `message.get("text")`; binding
  §2.1 says `user_message`. No shipped client sends text-turn frames (the app's
  WS is voice-only) — one-line conformance fix + test, zero risk.
- `background Coach evaluation failed (non-fatal)` (2026-08-03 12:19:24) —
  still unchased; a look and either a fix or a dated note.

### 5. Operator item — WITH Rich, not unilateral

Whether to restore the wiped pre-2026-08-03 transcripts from the NAS nightly
dumps (learner-state was untouched; this is history/transcripts only). If
restored, mind the collision with rows created since. If not restored, delete
this item from known-issues with a dated "accepted loss" note — either way the
ledger should say which.

## Session-end ritual (the standing rule)

Fold receipts into known-issues (delete fixed sections) + the plan's rows;
hermetic suite green before deploy; live receipts named; push — the Mac picks
it up from origin and runs its interlock legs.
