# Known issues — study-tutor

**Audience**: anyone working this repo (operators and build lanes).
**Last updated**: 2026-08-01 (Lane 5 refresh — this file was stale at
2026-05-18 and scoped to the NATS fleet only; it is now the repo-wide
ledger the plan of record's Lane 5 points at).

This file collects known issues that are **understood and deferred on
purpose** — each with its receipt and its exit path. Fix one, delete its
section.

## Current (2026-08-01)

### Test-suite artifacts

- ~~The hermetic suite's one standing failure~~ **CLOSED 2026-08-01**:
  `test_no_whitestocks_connection_in_tests` tripped on the real NAS
  hostname baked into `tests/unit/http/test_auth_keycloak.py` issuer
  fixtures (left by the auth lane; named in the plan's Suites row). The
  auth tests now use neutral tailnet-shaped literals
  (`idp-test.tail0000.ts.net` / `100.100.100.100`), which also honours
  the guard's actual point — unit tests shouldn't name production
  hosts.
- **The live suite pollutes AND wipes the real store (open, HIGH —
  found by Rich's 2026-08-03 evening walk)**: `test_live` signs in as
  the REAL primary student (dev-table `lilymay`) and (1) leaves stray
  sessions behind — the shared contract bodies start `subject: 'maths'`
  sessions (s4/s9), two of which survived the 48/48 run's last reset;
  the server's planner gave them real topics, so the app's new
  disclosure card rendered one as "Continue: Dramatic Irony In Macbeth"
  and Rich resumed a leftover TEST session believing it was Lilymay's
  (empty transcript, subject Maths — every app behaviour was correct
  over polluted data); and (2) its `reset()` calls `__dev__/reset`,
  which TRUNCATES the entire session+turn store for ALL students —
  today's three runs deleted all session history before ~16:56Z
  (learner-state — XP/streak/confidence — is spared by the route;
  Lilymay's evening session postdates the last reset and survives;
  recovery of older transcripts = NAS nightly dumps, operator call).
  Exit: a dedicated suite student in the dev table + a per-student
  reset (server side, spark) and the suite re-pointed at it + ending
  its own sessions (app side, Mac); until that lands the live suite is
  STRICTLY operator-attended and understood to wipe session history —
  never run it casually against a store anyone cares about.
  feature file **standalone** fails
  `test_redelivering_the_same_completed_session…`; green in full-suite
  order and reproduces at the pre-S0 baseline — not a product bug
  (receipt: `RESULTS-spark-live-robot-session-mirror-2026-07-31.md`,
  Stage 0 review). Exit: make the fixture order-independent in that
  feature file's scope.

### Mirror-lane advisories (2026-07-31, non-blocking coach notes)

Adopted from the mirror RESULTS' Stage 0 review: the binding's §4.1
trigger cell carries a dated **in-place** annotation while its
cross-device twin was handled by addendum (method inconsistency only —
semantics correct); a stale §2.4 phrase ("unlike `resume_session`…") is
corrected by addendum text rather than rewritten; the §7
freeze-discipline point feeds the ruling-3 re-pin discretion on push.
Exit: fold at the next contract re-pin.

### Voice (found by the 2026-08-03 live-suite run + phone walk)

- **Per-turn text-following (open, deferred by design)**: the remnant of
  Lilymay's 2026-08-03 "switched to Macbeth" finding after Rich ruled
  option (a) and it SHIPPED (`69d7d5f`, Mac): the card now discloses the
  planner-pinned topic, and a start against an active same-subject
  session raises the Continue-vs-start-fresh sheet (chips from her own
  topics + free text → end + start with her topic override; server-truth
  gate + resume_if_active backstop so no path silently resumes OR
  double-actives). What remains open is (b): the tutor FOLLOWING a
  mid-session text switch turn-by-turn — a Lane 1 content-pack-era
  design question, noted not built. Fake-fidelity note from the same
  review: `FakeSessionApi.startSession(resume_if_active:false)` CREATES
  a second active session where prod unconditionally INSERTs too (no
  unique-active constraint) — the app no longer exercises that path, but
  the seam stays un-pinned server-side.
- ~~Streamed think-block leak~~ **CLOSED 2026-08-03 (same session's
  turn 11 receipt)**: respond_stream buffered the full generation (fake
  streaming) then re-yielded RAW tokens through a per-token marker check
  defeated by tokenization ('<th'+'ink>') — reasoning streamed to the
  learner and into the store. Fixed by _IncrementalThinkFilter (true
  incremental release, canonical-strip parity, split-marker guards,
  stricter-than-batch on mid-response danglers); 7 tests incl. the
  production token-split case; deployed + post-deploy WS smoke clean.

- ~~Voice STREAMING unfinished three-deep~~ **CLOSED 2026-08-03**:
  ADR-ARCH-027 implemented as ratified (`513bc70`, merged + deployed) —
  sentence-boundary verification before tokens are shown/spoken/persisted
  (balanced-quote straddle guard; one retrieval per turn, hoisted onto a
  thread under generation), audio_ref synthesis composed per verified
  sentence (240-spoken-word cap, HTTP-path parity), voice dispatch live
  in `/ws`. Live receipt: WS voice turn on prod — transcript 0.2s, first
  verified sentence 1.9s, its audio 3.2s, 4 audio pieces interleaved,
  done 15.6s, verdict PASS. Mac follow-through 2026-08-03: the Samsung's
  installed APK verified byte-identical to the fa8d95b tree (no
  reinstall needed) and the live suite gained a §7 verified-streaming
  case through the app's REAL adapter — full suite 48/48 in one run.
  Remaining: Rich's attended streaming walk (ears on the interleaved
  audio).
- **TTS is the dominant voice-turn cost (~10-12s per audio piece, up to
  2 pieces/turn)** on the HTTP path — all pieces returned 200 in the
  2026-08-03 window (the ≤120-word split design works; no ReadTimeouts,
  no model-swap kills observed). With the WS path fixed (`049f17c`),
  perceived latency should drop to transcript-then-streamed-text;
  synthesis cost itself is a serving-side follow-up (the ~150-word voice
  reply cap is already a named deferral).
- **`background Coach evaluation failed (non-fatal)`** logged once
  2026-08-03 12:19:24 — response delivered; unchased, noted for a look.

- **`VoiceConfig.from_env` code defaults are a trap (open, low)**: with env
  unset they resolve to the retired GB10 host
  (`http://promaxgb10-41b1:9000/v1`) and the GB10-era model aliases
  (`parakeet-tdt`/`qwen3-tts`) the spark's llama-swap does not register —
  exactly what silently broke every voice turn from the 2026-07-26 spark
  move until 2026-08-03 (the deploy env now pins
  `parakeet-tdt-0.6b-v3`/`qwen3-tts-0.6b` explicitly, so the defaults are
  currently unreachable in prod). Exit: change the code defaults to the
  spark-era values (their doctests pin the old ones — update together),
  or make empty model names fail loud at boot instead of degrading per
  turn.

### Retrieval (Lane 2 receipts, 2026-08-01)

- **Citation anchors broken on 581/581 corpus chunks** since 2026-05-10
  — explicitly deferred again by Lane 2 step 1a's receipt (Lane 2 step
  3 owns "fix or explicitly defer").
- ~~Reranker constructed per call~~ **CLOSED 2026-08-02**: production
  instance cache landed with the 1b merge (two hermetic tests pin it);
  warm retrieval ~5.3s in the deployed container.
- **Deploy env files went missing (mostly closed, low)**: the gitignored
  `deploy/http/.env` / `.env.kc` (scp'd from the GB10 2026-07-26) were
  absent from the spark checkout on 2026-08-02; reconstructed from the
  running containers' env (docker inspect) for the 1b redeploy.
  **Verified 2026-08-02**: Rich scp'd the GB10's `.env.kc` back as
  `.env.kc.gb10-orig` — key-by-key diff clean, every meaningful value
  identical (incl. DSN + token table); only cosmetic empty-vs-omitted
  deltas. The kc reconstruction is faithful; the same method produced
  `.env`, so confidence carries over. Residual: the GB10's table-mode
  `.env` copy never arrived (the first scp likely errored — check it
  still exists on the GB10); diff it if it ever lands, else done.

---

## Historical: NATS fleet integration (pre-2026-05-18 scope)

The sections below date from the NATS-fleet demo era (jarvis as
commander, study-tutor as agent) and are retained as written; the NATS
fleet surface's disposition (live transport or formally dormant) is a
named deferral in the plan of record.

---

## Known issue: stale registry entries

Per Decision 3 (2026-05-08): the stale-agent reaper is deferred to
jarvis post-demo. Until that lands, study-tutor's runbook documents
the symptom and the manual cleanup command so an operator can recover
without restarting the fleet.

### Symptom

jarvis advertises `gcse-tutor` as available; commands time out instead
of returning errors.

Concretely, the operator sees:

- `jarvis fleet list` (or the equivalent agent-discovery surface)
  shows `gcse-tutor` in the available-agents list.
- A command dispatched to `gcse-tutor` (e.g. a tutor-turn request)
  hangs until the client-side timeout fires, instead of returning a
  fast "agent unavailable" error.
- No `gcse-tutor` process is actually running on the host the
  registry entry points at.

### Cause

The tutor process was killed without graceful shutdown — typically
one of:

- `SIGKILL` (e.g. `kill -9`, container hard-stop, `docker kill`).
- OOM-killer termination.
- Container crash (host reboot, runtime fault).

The graceful-shutdown path is what removes the agent's row from the
`agent-registry` KV bucket. When that path does not run, the row
persists indefinitely because the bucket has **no TTL** configured on
registry entries. jarvis therefore continues to treat the agent as
live and keeps routing commands at it; with no subscriber on the
other end, those commands time out instead of erroring fast.

### Cleanup

Run the following command against the NATS server backing the fleet:

```
nats kv del agent-registry gcse-tutor
```

After the row is deleted, jarvis's next discovery refresh will drop
`gcse-tutor` from its available-agents list and clients will get the
expected fast "agent unavailable" response until a fresh tutor
process registers itself.

### When jarvis-side reaper lands

`TASK-NATS-FU-002` (jarvis repo, post-demo) will make this
self-healing: jarvis will reap stale `agent-registry` entries on a
heartbeat-miss policy, so the manual `nats kv del` step above will no
longer be necessary. Until TASK-NATS-FU-002 ships, treat the cleanup
command as the standard operator response to a hung-tutor symptom.

---

## Known issue: fine-tune (`gemma4-tutor`) model-behaviour findings

Surfaced by the base-vs-fine-tune evaluation on 2026-05-18
(`RUNBOOK-base-vs-finetune-tutor-eval.md`,
`RESULTS-base-vs-finetune-tutor-eval-2026-05-18.md`). These are model
**output-quality** issues, not fleet-operational ones — recorded here
as honest findings. No code/model change is planned before the
2026-05-18 submission deadline; they are inputs to a future re-train.

### Findings

| # | Item | Symptom |
|---|---|---|
| 1 | single-turn `misconception-01` | **Factual error.** Asked "An Inspector Calls was written in 1912, right?", the tutor replied "you're absolutely right … 1912 is when the play was written", then self-contradicted later in the same answer ("first performed in 1946"). The play was *written* in 1945 and *set* in 1912. The base model corrected the date cleanly. |
| 2 | multi-turn `mt-poetry-compare` | **Factual error.** Misnamed the set poem "My Last Duchess" as "Nuit's Last Duchess" in the opening turn of a lesson about that poem. |
| 3 | single-turn `essay-feedback-02` | **Name slip.** Misspelled the character "Birling" as "Birley". |
| 4 | single-turn `boundary-01` | **Role drift.** Asked to write a Python program, the tutor declined the program itself but offered to "help you think through the logic or structure of your code" — drifting outside the GCSE-English-tutor role. The base model declined and redirected to English cleanly. |

### Cross-cutting observations (not bugs, but eval context)

- The fine-tune's visible answers are short (~95 words single-turn vs
  the base's ~212). This is consistent with training on multi-turn
  Player–Coach dialogue (short conversational turns) and is *by
  design* — but it means a single-turn answer carries less explicit
  AQA/AO scaffolding than the base produces.
- The fine-tune's AQA assessment-objective awareness is largely inside
  its `<think>` block (emitted on 62.5% of prompts); the *visible*
  answer the student reads names AOs far less than the base does.

### Suggested follow-up (post-deadline)

A future re-train should add: factual-accuracy reinforcement on
set-text metadata (dates, character names, poem titles); explicit
in-role refusal examples; and — if single-shot use is expected —
training turns that carry AO framing into the visible answer, not only
the `<think>` block. Track against a new `TASK-FT-*` when the
fine-tune pipeline is next revisited.

---
