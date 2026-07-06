# Reachy Local-Backend Migration — fleet-gateway Recon Deltas

**Status:** Recon complete 2026-07-06 (read of `fleet-gateway/reachy/` — README, deploy runbook,
SDK_SETUP, scripts, external_content — diffed against
[voice design §7](../../design/voice-tutor-and-reachy-design.md) and the
[W0-R runbook](../../runbooks/RUNBOOK-voice-w0r-reachy-feasibility.md)).
**Purpose:** surface repo-reality facts the R-track plan doesn't carry, **before** the W0-R
operator run. Advisory (drift-report style) — the runbook/plan owners decide what to fold in.
**Bottom line:** the plan's architecture is right; two deltas (D1, D3) can produce a *false
failure* of W0-R gate R-G3, and one (D2) is a data-plane rot problem the plan doesn't cover.

---

## 1. Current state (verified facts)

- **Two deployment modes.** (A) MacBook dev: unpinned clone of
  `pollen-robotics/reachy_mini_conversation_app`, `.env` from `reachy/.env.example` with
  `BACKEND_PROVIDER=huggingface`, `REACHY_MINI_CUSTOM_PROFILE=scholar`, external profile/tool dirs,
  `NATS_URL`; launched via `scripts/launch_scholar.sh` (exports `PYTHONPATH=<fleet-gateway-root>`).
  (B) On-robot Pi (production, verified 2026-05-20, first robot "Scholar"): app pre-installed in
  `/venvs/apps_venv`; the daemon passes **no** env, so env is injected via `sitecustomize.py`
  `os.environ.setdefault(…)` setting **only** `REACHY_MINI_EXTERNAL_TOOLS_DIRECTORY` and
  `NATS_URL`; profile lives in Personality Studio
  (`…/reachy_talk_data/profiles/user_personalities/scholar/`); NATS creds also hardcoded in
  `ask_jarvis.py` `_DEFAULT_NATS_URL`.
- **Cloud connection is implicit.** Mac sets `BACKEND_PROVIDER=huggingface`; the Pi sets *no*
  backend variable at all (HF cloud is the app default). `grep -rn "HF_REALTIME"` across
  fleet-gateway → **zero hits**: the `HF_REALTIME_CONNECTION_MODE`/`HF_REALTIME_WS_URL` re-point
  keys the plan relies on exist only upstream, never in this repo or (verified-as-of-May) on the Pi.
- **Voice:** nothing deployed sets `MODEL_VOICE` (comment-only in `.env.example`; supported list
  includes `Ryan`); per-profile `voice.txt` (`Kore`) is OpenAI-only and ignored by the HF backend.
- **Tools:** `ask_jarvis` is the only externally **proven** tool (13/20 May demos) and the only
  one conforming to the Pollen ABC (`parameters_schema` + `async def __call__`).
  `query_student_model`, `celebrate_achievement`, `agent_status` still use the **rejected** shape
  (`parameters` + `async def run()`; celebrate returns `str` not `dict`) — per the README's own
  13-May gotchas these would not load/fire, and no demo evidence shows them firing.

**What the plan already gets right:** plane split, sitecustomize env-injection quirk,
never-set `REACHY_MINI_EXTERNAL_PROFILES_DIRECTORY` on the Pi, ask_jarvis plumbing, Ryan in the
voice list, profile-drift existence, gated tool-forwarding.

## 2. Deltas (numbered; each with impact + suggested action)

**D1 — R-G3's proof tool is broken for reasons unrelated to s2s.** R-G3 ("tool calls round-trip
through local s2s — the highest-risk unknown") uses `query_student_model` as its proof, but the
repo tool is interface-non-conformant (rejected shape, §1). A failure would be **misattributed to
the s2s server**. → Before the operator run: either port `query_student_model` to the conformant
ABC shape, or make `ask_jarvis` (proven) the R-G3 proof tool and demote `query_student_model` to
a secondary check.

**D2 — the tool's data plane is rotting.** `query_student_model` reads Graphiti
(group `student-lilymay`), whose data is **frozen** since the Postgres migration (W1–W3 merged);
FEAT-SMP-004 tears the graph write path down next. The plan says the tool plane is "untouched",
which is true of transport but not of data. → FEAT-VOICE-004 (or a sibling task) needs a
Postgres-backed replacement — most naturally re-pointing the robot's student-model reads at the
HTTP adapter on `:8100`, same as `ask_tutor`. Not currently planned anywhere.

**D3 — app version unverified for the re-point keys.** `HF_REALTIME_CONNECTION_MODE`/
`HF_REALTIME_WS_URL` support was verified against **upstream** docs, not the version installed on
the Pi (~2026-05-20), and no upgrade step exists in any runbook. → Add a W0-R/R2 pre-gate: read
the installed app version on the Pi, confirm the env keys exist in that version, else plan an app
upgrade step (with the Personality-Studio profile-survival check).

**D4 — profile drift, enumerated.** Pi `tools.txt` drops `emotion` (broken in the installed app
version) and adds `task_cancel`/`task_status`; repo still lists `emotion` and lacks the task_*
entries; repo `instructions.txt` + `celebrate_achievement` scaffold still chain the broken
`emotion` tool; `voice.txt` never copied (and is ignored anyway). → This list is the concrete
content of the plan's "reconcile repo-vs-Pi drift" step (design §7.4) — reconcile *to the Pi*
where the Pi is right.

**D5 — the two-robot fact (R-G6) has no repo backing.** Scholar-only runbook; no Bridge
deployment record; and Pi deployments don't set `REACHY_MINI_CUSTOM_PROFILE`, so a second robot's
`ask_jarvis` would identify as `reachy-scholar` (adapter id derives from that var). → If R-G6 is
run with two robots, set the profile var per-robot via each Pi's `sitecustomize.py` first.

**D6 — subject-pin tension (D8 pickup).** The plan pins `ask_tutor`'s subject to the app's
constant (`maths`, `app/lib/…/home_screen.dart:12` confirmed), while the deployed Scholar persona
and `query_student_model` default are `english`. `resume_if_active` matches on
`(student, subject)`, so a phone session in `maths` resumes on the robot only if `ask_tutor`
sends `maths` — but the Scholar persona is an English tutor. → Decide deliberately: one shared
subject constant sourced from one place (and update persona or app accordingly), else D8 pickup
silently never matches.

**D7 — the Pi clone is hand-edited.** Hardcoded NATS creds in `ask_jarvis.py` (Phase 7
belt-and-braces) mean `git pull` on the Pi will conflict when shipping `ask_tutor`. → Ship via a
clean re-clone + re-apply of the sitecustomize/creds step (runbook it), not an in-place pull.

## 3. Suggested plan surgery (before the W0-R operator run)

1. W0-R runbook: add the D3 version pre-gate; swap R-G3's proof tool per D1; note D5 for R-G6.
2. FEAT-VOICE-004 spec inputs: carry D2 (Postgres-backed student-model read), D6 (subject
   constant decision), D7 (deployment mechanics), D4 (reconcile list).
3. fleet-gateway: fix the three non-conformant tools' interface shape regardless — cheap, and it
   un-blocks `celebrate_achievement` for the gamification track too.

---

*Generated 2026-07-06 from a repo recon pass diffing `fleet-gateway/reachy/` against the voice
design §7 and W0-R runbook. Advisory drift report; plan owners ratify.*
