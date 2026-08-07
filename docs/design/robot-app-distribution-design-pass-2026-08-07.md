# Robot app distribution — design pass (Lane 6 step 2)

**Status:** Design pass for Rich's gate (Lane 6 step 2; ruling-queue item 6) — 2026-08-07.
**What this is:** the investigation Rich asked for before any build — how Pollen's Reachy
Mini app distribution actually works, what the study tutor's robot integration would have
to become to be a switchable, installable app, and the open questions only Rich can rule
on. **This document does not design the build**; per the plan's gate, it comes back to
Rich first. Sources: this repo's runbooks/contracts (every claim receipted below) plus
2026 web research on the Reachy Mini platform (citations in §B). Facts about the
`fleet-gateway` repo come from THIS repo's runbooks and contract docs only — that repo
was not read for this pass (see §D).

**Bottom line, one paragraph.** The platform mechanism fits Rich's ask exactly: Reachy
Mini apps are pip-installable Python packages published as Hugging Face Spaces, the
robot's own daemon (its built-in app manager) runs exactly one app at a time and handles
install/start/stop/uninstall/switching natively, and Pollen's documented per-app
settings-web-UI pattern carries precisely the configuration our integration currently
smuggles in by hand (backend URL, bearer token, speech-service URL, voice pins). The
real decisions are the three forks in §E — app architecture, distribution channel, and
secrets posture — plus four smaller calls. All build work lands in the `fleet-gateway`
repo (and a new Hugging Face Space); study-tutor's frozen contracts are untouched —
they already serve any authenticated client.

Codenames, cashed out once: **the spark** = the household DGX Spark inference box (runs
the tutor backend on `:8100`); **the GB10** = the other household inference box (runs
the local speech-to-speech service on `:8765`); **Reachy Mini** = Pollen Robotics' small
desk robot (Lilymay's; a second lands for Dulcie in September); **the Scholar** = the
tutor personality the robot speaks as; **fleet-gateway** = the separate GitHub repo
(guardkit org) holding the robot-side integration code, deployed on the robot's own
Raspberry Pi; **the daemon** = the robot's built-in app-manager service (REST API on the
Pi's port `:8000`); **a Hugging Face Space** = a hosted git repository on Hugging Face
that doubles as an app's publish/distribution home.

---

## A. What the robot integration is today: a hand-deployed lattice

**The Scholar is not an "app" at all today — it is an overlay riding inside Pollen's
stock conversation app.** The receipt is
[`RUNBOOK-second-reachy-standup.md`](../runbooks/RUNBOOK-second-reachy-standup.md)
(the proven 2026-07-18 standup sequence), which shows the full deployed shape on the
robot's Pi:

- The fleet-gateway repo is `git clone`d to `/home/pollen/fleet-gateway` and injected
  into the robot's shared app virtualenv via a **`.pth` file** dropped into
  `/venvs/apps_venv/lib/python3.12/site-packages/`, plus a hand `pip install httpx`
  (runbook §C).
- The Scholar's tools (`ask_tutor`, `query_student_model`, `ask_jarvis`) are loaded by
  pointing the env var `REACHY_MINI_EXTERNAL_TOOLS_DIRECTORY` at the clone's
  `reachy/external_content/external_tools/` directory.
- Configuration is smuggled in through a **`sitecustomize.py`** file in site-packages —
  the runbook's own words: "the daemon passes no env; this is the channel" (§D3). It
  carries: `STUDY_TUTOR_HTTP_URL`, `STUDY_TUTOR_TOKEN` (the static bearer),
  `HF_REALTIME_WS_URL` (the GB10 speech service on `:8765`), `NATS_URL` plus credentials
  (for `ask_jarvis`), and `HF_REALTIME_CONNECTION_MODE=local`.
- The Scholar personality files (`instructions.txt`, `tools.txt`) are hand-copied into
  Pollen's Personality Studio directory inside `reachy_talk_data` (§D4), and **the
  voice/profile pin lives in `reachy_mini_conversation_app/startup_settings.json`** — a
  version-specific (0.6.1) landmine the runbook marks ⚠ as the pin that "beats every
  other channel" (§D5).
- Bring-up is the daemon's own REST API:
  `POST http://localhost:8000/api/apps/start-app/reachy_mini_conversation_app` (§E).

This is exactly the problem Rich's Lane 6 ask names: a hand-deployed lattice of
site-packages hacks, hand-edits (the repoint runbook warns "the Pi may carry a
hand-edited clone" — recon delta D7), and version-pinned config files inside *someone
else's* app. It is fragile under every conversation-app update, invisible to the robot's
dashboard, and not installable, switchable, or uninstallable as a unit.

**What the robot actually consumes from study-tutor — and why study-tutor's surface does
not need to change.** Per the frozen contract
[`API-session-http-binding.md`](contracts/API-session-http-binding.md):

- `ask_tutor` calls the frozen six-verb HTTP session surface on `:8100` with the
  **static bearer** (table-token mode): `start_session` with
  `resume_if_active: true, subject: 'english'`, then `turn`. (Receipt: R07 in
  [`HANDOFF-weekend-auth-voice-fable-window.md`](../runbooks/HANDOFF-weekend-auth-voice-fable-window.md);
  confirmed in
  [`HANDOFF-spark-live-robot-session-mirror.md`](../runbooks/HANDOFF-spark-live-robot-session-mirror.md).)
  Offline behaviour is contract-shaped: any failure — network error, non-2xx, rejected
  bearer — yields exactly the spoken string "The tutor isn't reachable right now.",
  never a raised exception.
- `query_student_model` uses the additive `GET /api/student-model` read (binding §2.2),
  pinned in fleet-gateway at `common.tutor_client.STUDENT_MODEL_PATH`; any non-2xx maps
  to a graceful "unavailable"; consumers gate on the `data_available` field.
- Authentication is `Authorization: Bearer <token>` only, with identity derived
  server-side, never client-asserted (binding §3). **The contracts already serve any
  authenticated client** — an installable app changes *how the Scholar code and its
  config arrive on the robot*, not one byte of study-tutor's wire surface. The only
  surface-adjacent item on the horizon is per-device identity (FEAT-AUTH-004 device
  pairing) — out of scope and already ledgered; today "every robot shares the student
  token → shares sessions" (standup runbook §F).

**The session semantics are already robot-safe (blessed).** Commit `19a0211`
(2026-08-04, blessed by Rich): a robot start **resumes** the learner's active
`(student, subject)` session — it joins, never ends, the conversation Lilymay may have
open on her phone. The ruling is recorded in place in
`src/study_tutor/mcp/adapter.py` (~lines 218–237), and the HTTP
`resume_if_active: false` path is end-then-create with a partial-unique-index backstop
(the binding table's dated 2026-08-04 annotation). The robot's HTTP path already sends
`resume_if_active: true`, so both doors agree: cross-device pickup (D8) is structural.
Nothing an installable app does can mint a second active session.

**The mirror closes the loop phone-side.**
[`RESULTS-spark-live-robot-session-mirror-2026-07-31.md`](../runbooks/RESULTS-spark-live-robot-session-mirror-2026-07-31.md):
the phone watches the robot's turns via the additive `turns?since=` delta read plus the
optional SSE stream ("one verb per job" — `resume` stays active-only after the `96baad2`
revert). An installable app inherits this for free, because it is the same session.

**The precondition that is NOT this step: Lane 6 step 1.** The GB10-to-spark re-point
([`RUNBOOK-reachy-repoint-spark.md`](../runbooks/RUNBOOK-reachy-repoint-spark.md) —
written 2026-08-01, ready, **NOT YET RUN**). The robot's tutor path is presumed DOWN
until fleet-gateway's base URL flips from the retired GB10 `:8100` to
`http://spark-fcf6.tailebf801.ts.net:8100` (same bearer). Any app packaging bakes in the
*spark* URL story, so **step 1's completion — or at minimum its URL decision — precedes
or rides with any build**. Note the standup runbook's `sitecustomize.py` also still
carries GB10 hostnames for the speech-service WebSocket URL; that speech service stays
on the GB10 `:8765` (fenced) even after the tutor re-point.

---

## B. How Reachy Mini app distribution actually works (web research, 2026)

**B1. The mechanism, plainly.** Every Reachy Mini app is a **Python package published
as a Hugging Face Space**. The Space repo is the distribution artifact: the robot
installs an app by `pip`-installing the repo into the robot's shared virtualenv.
Discovery is by Hugging Face tag: the app's README frontmatter must carry
`reachy_mini_python_app` to appear in the store. The store front-ends are (a) the
**robot's own dashboard** (the daemon's web UI on `:8000`) and (b) **Reachy Mini
Control**, the official desktop app (production-ready on macOS; Windows and Linux are
work-in-progress per its own README), whose Applications tab fetches
tagged Spaces, installs via job-based polling, and handles start/stop/uninstall.
Hugging Face launched the official app store 2026-05-06 with 200+ community apps and
roughly 10,000 robots in the field; all apps are open-source repos, forkable and
one-click installable; a curated official list also exists as the
`pollen-robotics/reachy-mini-official-app-store` dataset. There is also a phone app —
already used in the household (standup runbook §F).

**B2. The app SDK contract (Python).** An app is a class extending `ReachyMiniApp`
implementing `run(reachy_mini, stop_event)`, discovered through a standard Python entry
point in `pyproject.toml`, group `reachy_mini_apps`
(`my_app = "my_app.main:MyApp"`). The scaffold is generated by
`reachy-mini-app-assistant create <name> <path> [--publish]` — never hand-rolled; the
assistant handles tags, entry points, and structure. `reachy-mini-app-assistant check`
validates; `publish` creates the Hugging Face Space (and **asks for a privacy setting,
private or public**). There are two templates: default, and **`--template
conversation`** — "LLM integration, speech, making the robot talk. Includes audio
pipeline, LLM tools, movement fusion and all the plumbing." An `AGENTS.md` plus a
`skills/` directory in the SDK repo exist specifically so AI coding agents can build
apps correctly.

**B3. Lifecycle: how apps run, stop, and switch.** The **daemon owns the whole
lifecycle**: a start request (dashboard or REST) launches the app as a subprocess
(`python -u -m your_app.main`); stop sends SIGINT, which trips the app's `stop_event`;
after exit the daemon returns the robot to its default position. **Only one app runs at
a time** — which is precisely Rich's "switch between the study tutor and other robot
apps": switching is stop-current + start-other, native to the platform. The REST surface
is exactly what the standup runbook already uses:

- `POST /api/apps/install {"url": "https://huggingface.co/spaces/<user>/<app>"}`
- `POST /api/apps/start-app/<name>`
- `POST /api/apps/stop-current-app`
- `GET /api/apps/list`

A `--startup-app <name>` daemon option makes one installed app the default
wake-up/antenna-touch experience (and auto-installs it from the catalog if missing).

**B4. Per-app configuration.** The app subprocess **inherits the daemon's environment —
there is no env-injection mechanism** (this is the fact the current `sitecustomize.py`
hack exploits). Pollen's *recommended* pattern for runtime config (API keys, **server
URLs**) is the app's own **settings web UI**: set `custom_app_url` on the app class and
the SDK auto-starts a FastAPI server serving the package's `static/` directory, with
routes added on `self.settings_app`; the dashboard shows a gear icon opening it
(`http://reachy-mini.local:<port>` on the Wireless model). Alternatives named in the
docs: a config file at a known path (the conversation app's `.env.example` is the worked
example) or hardcoded defaults. So **a backend URL, bearer token, and voice pins can
ride with the app** as a settings page persisting to an on-robot config file — with no
secrets in the published Space.

**B5. Private listing and side-loading.** Publishing private Spaces is supported by the
assistant. The store listings surface *tagged public* Spaces, and none of the official
docs state whether the dashboard can install a private Space (it would need a Hugging
Face token on the robot) — an open question carried to §E2. What **is** documented and
proven: **manual side-load** — `scp` the app to the robot and
`/venvs/apps_venv/bin/pip install /tmp/my_app` (the documented offline/conference path),
plus install-by-URL over the REST API from the LAN. The local dev loop is
`pip install -e` plus a daemon restart. Uninstall is handled by the dashboard/desktop
app lifecycle.

**B6. Constraints.**

- **Compute:** the Wireless robot's onboard computer is Raspberry Pi-class (announced
  with a Pi 5; 2026 store/press listings say Raspberry Pi CM4 — 4 mics, wide-angle
  camera, 5W speaker, WiFi, battery). Either way: no on-robot LLM, speech-to-text, or
  text-to-speech inference — all heavy lifting must stay off-board (the spark
  `:8100`/`:9000`, the GB10 speech service `:8765`), which is already this project's
  topology.
- **Connectivity:** apps assume the robot can reach whatever backends they call. The
  spark is tailnet-only, so the app's install story silently assumes the robot stays on
  the LAN/tailnet (already true — the standup prereq). A store-published app would be
  *installable* by anyone but *usable* only inside the household network — worth stating
  honestly on the Space page if public.
- **Shared virtualenv:** apps install into one shared venv on the Wireless model
  (`/venvs/apps_venv/`) — dependency hygiene matters; the current `.pth` + hand-pip
  approach is exactly what proper packaging would replace.
- **Audio:** SDK audio APIs (`start_recording`, `play_sound`, etc.) are available to
  apps directly; the conversation template carries a full audio pipeline. One app at a
  time also means the tutor app and, say, a dance app can never contend for the
  microphone.

**Citations (web, current as of 2026):**

- Building & Publishing Apps (SDK docs — lifecycle, REST API, config, side-load, tags):
  https://huggingface.co/docs/reachy_mini/SDK/apps
- Make and Publish Your Reachy Mini Apps (publish walkthrough, private/public setting):
  https://huggingface.co/blog/pollen-robotics/make-and-publish-your-reachy-mini-apps
- App store announcement (Clem Delangue, 2026-05-06):
  https://huggingface.co/blog/clem/reachymini-appstore
- VentureBeat on the store launch:
  https://venturebeat.com/technology/the-app-store-for-robots-has-arrived-hugging-face-launches-open-source-reachy-mini-app-store-with-200-apps
- Reachy Mini SDK repo (AGENTS.md, skills/):
  https://github.com/pollen-robotics/reachy_mini · docs hub:
  https://huggingface.co/docs/reachy_mini/SDK/readme
- Reachy Mini Control desktop app (install/start/stop/uninstall subsystem):
  https://github.com/pollen-robotics/reachy-mini-desktop-app · usage doc:
  https://github.com/pollen-robotics/reachy_mini/blob/main/docs/source/platforms/reachy_mini/usage.md
- Official store curation dataset:
  https://huggingface.co/datasets/pollen-robotics/reachy-mini-official-app-store
- Template app with settings UI:
  https://huggingface.co/spaces/pollen-robotics/reachy_mini_template_app (the Space
  returned 401 at verification on 2026-08-07 — apparently made private; the settings-UI
  pattern it demonstrates is described in the SDK apps doc above) · conversation
  app (`.env.example` config precedent):
  https://github.com/pollen-robotics/reachy_mini_conversation_app
- Wireless hardware (CM4 listing):
  https://store.pollen-robotics.com/products/reachy-mini-wireless-version · SDK on PyPI:
  https://pypi.org/project/reachy-mini/

---

## C. What a switchable, installable study-tutor app needs (findings, not design)

1. **A real `ReachyMiniApp` package** — assistant-generated, entry-point discovered, a
   Hugging Face Space repo — replacing the `.pth` + `sitecustomize` + Personality-Studio
   + `startup_settings.json` lattice of §A. The conversation template appears to cover
   most of what the Scholar overlay currently borrows from
   `reachy_mini_conversation_app`.
2. **Config carried with the app, secrets entered per-robot:** a settings UI (the
   documented `custom_app_url` pattern, §B4) for the backend URL (the spark), the static
   bearer, the speech-service WebSocket URL, and the voice/profile pins — persisted
   on-robot, never committed to the Space. This dissolves the "daemon passes no env"
   problem legitimately.
3. **Clean install/uninstall/switching for free** from the daemon plus
   dashboard/desktop app once it is a real app: install by store tile or URL,
   one-app-at-a-time switching, SIGINT-clean shutdown (the `stop_event` loop), and
   optionally `--startup-app` to make the tutor the robot's default wake-up persona.
4. **No study-tutor changes:** the app speaks the frozen contracts as any authenticated
   client (§A); robot starts resume the active session (the blessed `19a0211` ruling);
   the phone mirror keeps working. The only adjacent lane is FEAT-AUTH-004 per-device
   pairing, already ledgered and out of scope.

## D. Where the work lands

- **fleet-gateway repo (guardkit org) + the robot host:** essentially all of it —
  restructuring the Scholar integration (`reachy/external_content/*`,
  `common/tutor_client.py`, `common/subject.py`) into the app package, the Hugging Face
  Space publish, and retiring the standup runbook's hand-deploy steps. **Honest note:
  that repo is not checked out here — everything this document says about fleet-gateway
  comes from THIS repo's runbooks and contract docs only** (the standup and repoint
  runbooks, the binding's consumer-pin notes, and the R07/R08 handoff rows), not from
  reading fleet-gateway itself.
- **A Hugging Face Space** (new artifact; org/account choice open — §E7) as the
  distribution repo.
- **study-tutor repo:** nothing but documentation — the plan's Lane 6 cells and, at
  most, additive contract addenda if a future decision ever needs one (none identified).
- **The GB10:** the speech-to-speech service on `:8765` stays a fenced household service
  that the app points at via config (unless §E1 option (c) removes the dependency).

---

## E. THE GATE — open questions for Rich (ruling-queue item 6)

The investigation's seven open questions FOR Rich, verbatim from its brief, each with a
one-line recommendation where the findings support one. Reminder riding with every answer: **the
step-1 precondition stands** — the GB10-to-spark re-point (or at least its URL decision)
precedes or rides with any build.

**E1.** *App architecture fork: package the Scholar as (a) a thin overlay that still
configures/launches Pollen's `reachy_mini_conversation_app` (closest to today, but stays
hostage to its internals — the 0.6.1 `startup_settings.json` landmine class), or (b) a
standalone app from the **conversation template** owning its own audio/LLM/tool loop
against the s2s unit, or (c) a standalone app that drops the local s2s dependency and
uses study-tutor's own server-side voice (`voice_turn`/WS streaming verbs) — the biggest
simplification (one backend, verified streaming voice, no GB10 dependency) and the
biggest build.*
> **Recommendation: lean (c)** — one backend, contract-verified streaming voice, no GB10
> dependency — while being honest that it is also the biggest build; (a) is the smallest
> step but keeps the whole landmine class that motivated this lane, and (b) is the
> middle path that owns the app but keeps two backends (spark + GB10) in every robot's
> config.

**E2.** *Distribution channel: public Space (open-sources the Scholar shim;
usable-only-on-the-household-tailnet must be stated; zero secrets in-repo), private
Space (does the dashboard/robot install private Spaces, and with what HF token on the
robot? — unverified), or documented side-load (`scp` + pip, known-good, no store UX).
This also decides whether the tutor appears as a store tile Lilymay/Dulcie can reinstall
themselves.*
> The honest tradeoff: **public** gives the store tile the children can reinstall
> themselves at the price of open-sourcing the shim (secrets already stay out via the
> settings UI, and "usable only on the household tailnet" must be stated on the Space
> page); **private** may not be installable from the dashboard at all — unverified in
> the official docs and needing a Hugging Face token on the robot; **side-load** is
> known-good but keeps deployment an operator ritual, which is the problem being solved.

**E3.** *Secrets posture: is the static bearer entered per-robot via the settings UI
acceptable for now, and does FEAT-AUTH-004 (device pairing, per-child robots/tokens —
Dulcie's robot lands September) ride with this lane or stay sequenced after it?*
> **Recommendation: yes for now, sequenced after** — the settings-UI bearer is the
> documented platform pattern and strictly better than today's `sitecustomize.py`;
> FEAT-AUTH-004 is already ledgered out of scope, and nothing in the packaging blocks
> it landing later (September, with Dulcie's robot, is the natural forcing date).

**E4.** *The `ask_jarvis`/NATS tool: does the packaged tutor app ship it (NATS creds
would then need the same settings-UI treatment), or is it dropped from the tutor app and
left to some other app/profile? (Broker isolation is a build-lane rule; the robot
runtime does use NATS today.)*
> No recommendation from the findings — this is a genuine scoping call. The one fact to
> weigh: shipping it widens the app's secret surface (NATS credentials alongside the
> bearer), while dropping it makes the tutor app single-purpose and leaves `ask_jarvis`
> to a separate app the platform can now cleanly switch to.

**E5.** *Startup posture: should the study tutor be the robot's `--startup-app`
(antenna-touch → tutor) or one tile among several started from the dashboard?*
> **Recommendation: startup-app for the household** — antenna-touch → tutor makes the
> tutor the robot's default persona for Lilymay (and Dulcie's robot in September), and
> the daemon's switching still allows any other app to be started from the dashboard.

**E6.** *Sequencing: confirm Lane 6 step 1 (the spark re-point + live `ask_tutor` smoke)
executes before or as part of the app build, and whether the packaging work formally
retires `RUNBOOK-second-reachy-standup.md`'s hand-deploy path.*
> **Recommendation: confirm both** — step 1 is independent, runbook-ready, and unblocks
> the only currently-broken thing (the robot's tutor path); and a packaging build that
> does not retire the hand-deploy path would leave two deployment truths on the Pi.

**E7.** *Venue/naming: does the app package live inside the fleet-gateway repo with the
Space as a publish target, or as its own repo? Which HF account/org owns the Space?*
> No recommendation from the findings — repo layout and Hugging Face org/account
> ownership are Rich's call; the only constraint found is that the Space itself is the
> distribution artifact either way.

---

**Key repo receipts (all verified against this worktree, 2026-08-07):**
`docs/study-tutor-plan-of-record.md` (Lane 6; ruling-queue item 6) ·
`docs/runbooks/RUNBOOK-second-reachy-standup.md` (the current hand-deploy shape) ·
`docs/runbooks/RUNBOOK-reachy-repoint-spark.md` (step 1, NOT YET RUN) ·
`docs/runbooks/RESULTS-spark-live-robot-session-mirror-2026-07-31.md` (the mirror;
`96baad2` "one verb per job") ·
`docs/design/contracts/API-session-http-binding.md` (§2.2, §3, the 2026-08-04
`start_session` annotation) ·
`src/study_tutor/mcp/adapter.py` (~218–237, the blessed resume ruling in place) ·
`docs/runbooks/HANDOFF-weekend-auth-voice-fable-window.md` (R07 — the `ask_tutor`
contract-shaped offline string) ·
`docs/runbooks/HANDOFF-spark-live-robot-session-mirror.md` (same-session confirmation).
