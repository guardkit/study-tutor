# HANDOFF — the Scholar robot app build (fleet-gateway's next lane)

**Date:** 2026-08-13 · **From:** the spark master session · **For:** the fleet-gateway
Claude session (the one that ran the re-point — it has warm context on the Pi and repo).
**Lane:** study-tutor plan-of-record **Lane 6, the packaging build** — the gate is CLOSED
(all seven questions ruled by Rich, 2026-08-13; recorded in
`docs/design/robot-app-distribution-design-pass-2026-08-07.md` §E and inlined below, so
this brief is self-contained).
**How to consume this:** this file lives in the study-tutor repo
(`docs/runbooks/HANDOFF-fleet-gateway-scholar-app-build.md`); fetch it raw from GitHub if
no checkout is at hand. Everything the build needs is IN this brief — the design doc and
contract are referenced for depth, not required reading to start.

## The one-paragraph why

The Scholar today is a hand-deployed lattice (a `.pth` file + `sitecustomize.py` +
Personality Studio copies + a version-pinned `startup_settings.json`) riding inside
Pollen's stock conversation app — and its spoken path is DEAD: the local speech-to-speech
unit it depended on (`ws://promaxgb10-41b1:8765`) no longer exists anywhere (GB10 swept
2026-08-13: no container, no service). Rich has ruled the GB10 factory-only, so the
robot speaks again by BUILDING THE RIGHT THING: a real, installable Reachy Mini app that
uses **study-tutor's own server-side verified streaming voice on the spark** — one
backend, one box, the same ADR-027 voice pipeline the phone uses, with quote
verification built in.

## The rulings this build executes (Rich, 2026-08-13 — binding, do not relitigate)

1. **E1 = (c): standalone app, spark server-side voice.** The app owns its audio loop
   (record on the robot, ship audio to the spark, play the returned speech). No local
   STT/TTS models, no speech-to-speech unit, no dependency on Pollen's conversation app
   internals.
2. **E2: public Hugging Face Space** — the store tile Lilymay/Dulcie can reinstall
   themselves. Zero secrets in the repo; the Space page states plainly: *usable only on
   the household network (the backend is tailnet-only)*.
3. **E3: the static bearer is entered per-robot via the app's settings web UI** and
   persisted on-robot. FEAT-AUTH-004 (per-device pairing) is sequenced AFTER, untouched.
4. **E4: `ask_jarvis` is DROPPED.** The app ships tutoring tools only. No NATS anywhere
   in the app (no `nats://`, no `:4222`, no client libs) — this also satisfies the
   standing broker-isolation rule by construction.
5. **E5: startup app** — antenna-touch → tutor (`--startup-app`), other apps still
   switchable from the dashboard.
6. **E6: the packaging build formally RETIRES the hand-deploy path** (the standup
   runbook's `.pth`/`sitecustomize`/Personality-Studio steps) once the app is proven.
7. **E7: the package lives in the fleet-gateway repo; the Space under the RichWoollcott
   HF account.**
8. **Success criterion added 2026-08-13 (Rich): ZERO study-tutor dependency on the
   GB10.** Grep-provable: no `promaxgb10`, no `:8765`, no `HF_REALTIME_*` requirement
   in the app or its config surface.

## What the app talks to (the spark surface — frozen contract, CONSUME ONLY)

Base URL (per-robot setting, default for the household): 
`http://spark-fcf6.tailebf801.ts.net:8100` — table-auth mode, `Authorization: Bearer
<token>` on every call, identity derived server-side. The re-point receipts prove the
robot's existing bearer works against it. Client-side turn deadline: **90 s** (ratified
2026-08-13). The six session verbs are FROZEN — additive consumption only; any wire need
this build discovers comes back as a question, never an edit.

- `POST /api/sessions/start` `{subject: "english", resume_if_active: true}` — **the
  robot ALWAYS sends `resume_if_active: true`** (the blessed 2026-08-04 semantics: a
  robot start JOINS the learner's active session, never ends it; D8 cross-device pickup
  is structural). Response carries `session_id`, `resumed`.
- `POST /api/sessions/{id}/voice-turn` — **`multipart/form-data`**, file field `audio`
  (send filename + full content-type incl. codec params). Response:
  `{transcript, tutor_response, audio: [{seq, chunk_id, url}]}` — the spark does STT,
  the Socratic turn, quote verification, AND TTS server-side.
- `GET /api/sessions/{id}/voice-audio/{chunk_id}` → `audio/wav` bytes. Play in `seq`
  order.
- Streaming upgrade (stage 3): `GET /api/sessions/{id}/ws` (WebSocket, bearer on the
  upgrade) — contract §7 Rev 1 frame vocabulary; verified streaming = sentence-by-
  sentence text with interleaved `audio_ref`s (transcript ~0.2 s, first spoken sentence
  ~3 s on the phone today).
- `GET /api/student-model?subject=english` — the existing `query_student_model` read
  (`data_available` gating as today).
- `POST /api/sessions/{id}/end` — on clean app stop (SIGINT → `stop_event`), do NOT end
  the session by default: the session may be Lilymay's, shared with her phone (the
  join-never-end principle extends to shutdown; just stop talking).

Existing tool code to LIFT, not rewrite: `common/tutor_client.py` (the offline behaviour
is contract-shaped — any failure yields exactly "The tutor isn't reachable right now.",
never a raise) and `common/subject.py` (the SUBJECT_DEFAULT seam).

## The platform shape (verified against Pollen's docs, 2026-08-07 design pass)

- An app = a Python class extending `ReachyMiniApp` implementing
  `run(reachy_mini, stop_event)`; entry point group `reachy_mini_apps` in
  `pyproject.toml`. Scaffold with `reachy-mini-app-assistant create` (never hand-rolled);
  `check` validates; `publish` creates the Space (choose PUBLIC per E2). README
  frontmatter tag `reachy_mini_python_app` = store discovery.
- **Settings UI:** set `custom_app_url` on the class → the SDK serves the package's
  `static/` via FastAPI with routes on `self.settings_app`; the dashboard shows a gear
  icon. Settings to carry: backend base URL, bearer token, subject (default `english`).
  Persist to an on-robot config file. **Secrets never in the Space repo.**
- **Lifecycle:** the daemon runs ONE app at a time as a subprocess; stop = SIGINT →
  `stop_event`. Install: dashboard/store tile, `POST /api/apps/install {url}`, or the
  documented side-load (`scp` + `/venvs/apps_venv/bin/pip install`) as the dev loop.
- **Audio:** SDK APIs (`start_recording`, `play_sound`, …). The talk trigger is the
  builder's design decision within one constraint: **MVP = deliberate push/touch-to-talk
  (antenna touch or equivalent), not open-mic wake-word** — simplest, and a 14-year-old's
  bedroom robot should visibly listen only when asked. Propose; don't gold-plate.

## Fences (verbatim, standing)

- **Law 2 (data):** the child's audio goes to the spark and NOWHERE else — no HF-hosted
  realtime, no cloud STT/TTS, no third-party endpoints. `HF_REALTIME_CONNECTION_MODE`
  and its whole config family must not survive into this app.
- **Laws 1/7 (tone):** the app never bypasses the tutor's Socratic behaviour (no local
  prompt injection, no answer shortcuts); nothing that can make a session end sad.
- **Frozen contract:** consume only; a needed change is a REPORTED question.
- **No NATS** (E4 + standing broker isolation).
- **Secrets:** bearer only via settings UI → on-robot file (0600); never committed,
  never logged, never in the Space.
- **The Pi's existing lattice stays untouched until stage 4** — it's the rollback path.

## Build order (coach-gated stages; local commits; Rich's word before the Space publish)

1. **Scaffold + settings + text parity.** Assistant-scaffolded app in the fleet-gateway
   repo; settings UI (URL/bearer/subject → on-robot config); lift `tutor_client` +
   `subject`; a `run()` loop that can take a typed/test prompt through
   `start → turn → reply` against a FAKE spark in tests (hermetic; the repo's 160-test
   suite stays green) and the real spark in a dev-mode install.
   *Gate: hermetic tests green + a dev-mode install on the Pi answers one text prompt
   via the spark.*
2. **The spoken loop (HTTP).** Touch-to-talk → `start_recording` → `voice-turn`
   multipart → fetch `voice-audio` chunks in `seq` order → `play_sound`. Honest waits
   (TTS costs ~10–12 s/piece on the HTTP path today — an interim "thinking" gesture
   beats silence). *Gate: a spoken round trip on the robot against the spark, attended.*
3. **Streaming upgrade.** Move the turn to the WS verified-streaming path — sentence-by-
   sentence speech, the phone-parity experience. Keep HTTP as fallback. *Gate: spoken
   streaming turn attended + the phone mirror shows the robot's turns (same session —
   the D8 cross-check).*
4. **Publish + retire.** `publish` to the public Space (RichWoollcott); install from the
   dashboard tile on the robot; `--startup-app` wired (E5); THEN remove the Pi lattice
   (`.pth`, `sitecustomize.py`, Personality Studio copies — keep the timestamped
   backups) and mark the standup runbook's hand-deploy path SUPERSEDED in its header.
   *Gate: Rich's attended walk — antenna-touch → spoken Socratic exchange → mirror
   check → GB10-dependency grep = zero. His merge word closes the lane.*

Stage 2 is the moment the robot speaks again; stages 3–4 make it right and make it
distributable. If any stage discovers a genuine contract need or a fourth act for Rich,
PARK with a note and come back — never improvise on the frozen surface.

## Reporting

Per the mission's rule: the lane ends by updating study-tutor's plan (Lane 6 cell + the
Robot row) with receipts — the spark session folds it if you push a RESULTS note; state
the S0 effect (this lane is S0's robot leg: a robot session by a real student is the
number that matters).
