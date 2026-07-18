# EVIDENCE — Batch B (R03 re-point · R09 re-clone · SMK-R live smoke) · 2026-07-18

Operator: Fable driving, Rich attending (voice + phone legs). MacBook session ran the
phone leg. All times BST. Companion: ../voice-r01-r02-batchA-2026-07-17/EVIDENCE.md.

## R09 — clean re-clone — PASS (morning)
Old clone cd612e9 (2026-05-20, pre-R-track). mv -> fleet-gateway.bak-2026-07-18;
fresh clone @ e5a98ea, later fast-forwarded per-file to 3194278 (alias fixes).
NATS hand-edit transplanted Pi-side from .bak (creds never left the Pi). .pth intact.
httpx 0.28.1 into apps_venv. ask_tutor file-path load gate PASS (schema [message,subject]
then +question,+query aliases). AC-R09-1..3 PASS; AC-R09-4 = the replay runbook
(RUNBOOK-second-reachy-standup.md, committed alongside this evidence).

## R03 — re-point + config — PASS (morning)
sitecustomize §A written (local mode, ws://promaxgb10-41b1:8765/v1/realtime, tutor URL,
REAL bearer from the live container env, MODEL_VOICE=Ryan legacy). NATS line preserved.
LANDMINE FOUND+FIXED: /home/pollen/.env was a Mac-authored template with /Users/... paths
for BOTH external dirs and OVERRIDES all env when cwd-upward-search finds it (bit only
sometimes — cwd-dependent). External-dir lines removed (backup .env.bak-2026-07-18).
PROFILES_DIRECTORY fence (AC-R03-1): removed from /etc/environment AND .env; verified
unset in fresh session; scholar resolves from Personality Studio (user_personalities/).
R08 reconciled profile refreshed into PS (ask_tutor present, emotion absent).
VOICE PIN TRUTH (supersedes W0-R finding 1 and the R01 caveat): in app 0.6.1 the ONLY
effective voice pin is startup_settings.json ("voice": "Ryan") — beats MODEL_VOICE env,
profile voice.txt, and the server --qwen3_tts_speaker flag. Session shows voice='Ryan'. 

## SMK-R — live smoke — ALL FOUR ACs PASS (11:00-12:50)
- AC-R1 open-mic local, no HF-cloud: conversations all day over ESTAB Pi->GB10:8765;
  connection sampling: only tailscale infra + HF-CDN (dashboard catalogue fetch) on 443;
  no hf.space realtime. App log: session initialized profile=user_personalities/scholar.
- AC-R2 ask_tutor round-trip: PROVEN repeatedly. Best-form: <code>-taught call parsed
  with exact args {"message":"What is a metaphor?"}; POST /api/sessions/start (Auth
  lilymay) + /turn 200; spoken Socratic answer in Ryan's voice ending with a question.
- AC-R3 query_student_model: canonicalizer-recovered call; GET /api/student-model 200;
  robot narrated the REAL record ("level 2, 280 XP, 180 towards next, Scholar
  achievement at level 6" / later "20 XP away from Level 3") — quick and clean.
- AC-R4 / D8 cross-device pickup: Phone (galaxy, via Mac session) started session
  acb3394c-a9a4-42ba-bdec-29dbd30bcfc9 (lilymay, english, 2 turns). Robot ask_tutor
  then logged: "session acb3394c-... (resumed=True, subject=english)" and POSTed
  /turn on THAT id; tutor continued the phone's metaphor thread aloud. PROVEN both
  directions (id match server-side + on-device transcript + audible continuation).
- No raw audio at rest: Pi zero audio files today; GB10 only package assets +
  rt_probe fixture (removed). :8100 voice routes unmounted (flag off; Mac-verified 404).

## The s2s tool-call saga (the day's engineering story — 12 dialects)
gemma4-tutor (fine-tuned partly on Claude transcripts) NEVER received tool-format
teaching in the responses-api pipeline (build_tool_system_prompt only existed in the
local-model handler family — the root cause, found late). It improvised 12 formats:
<call:f(x)/>, <tool_call:f>{json}</tool_call>, <tool_call>f(x)</tool_call>,
<function_call>f(x), <call:f k="v"/>, bare f(x), <call:f>, <call:f(x)>,
<function_calls><call name=.../>, <tool_call|>+call:f{}, <|tool_call>, <|channel>thought.
Fixes (ALL LOCAL PATCHES to ~/s2s/.venv, recorded at ~/s2s/patches/
0001-local-toolcall-fixes.patch, pristine .orig copies alongside; NOT upstreamed):
1. base_openai_compatible: RAW-stream interception state machine (enter markers ->
   buffer -> end markers -> parse) BEFORE remove_unspeechable; <think> blocks discarded;
   orphan-tag + JSON-blob speech guards; wrapper-agnostic CANONICALIZER (registered
   tool name + quoted k/v pairs anywhere -> constructed call); parsed calls emitted
   via _record_tool_call (native path).
2. tool_prompt/language_model: widened block regexes (also benefits local-model path).
3. responses_api: tools + tool_choice NEVER forwarded (llama.cpp parser-gen 400s on
   this template); _serialize TEXTIFIES function items — function_call -> assistant
   text, function_call_output -> USER-role text (system-mid-conversation 400s: proven
   empirically T1-T6 against :9000); tool teaching injected into instructions
   (_apply_config) — after which the model used <code> correctly at least once.
Residual defects (recorded, not blocking):
- Reasoning-channel leak dialect #12 (<|channel>thought) can still reach TTS.
- Qwen3-TTS-0.6B intermittently misses EOS and babbles to the 360-frame cap (28.72s
  signature, 3 occurrences); ASSUM-003 pre-approves trying the 1.7B checkpoint.
- Tool CHOICE is erratic (progress tool for "carry on with my session"); needs
  explicit "ask the tutor..." phrasing; persona-tuning follow-up.
- Latency: tutor turns 26-80s on the spark topology; robot copes (filler + generous
  timeout) but the APP's 15s turnBudget is under water (Mac finding; bites KC-G3).

## Mac-session findings (phone leg) — for the weekend log
1. app turnBudget 15s < real 26-34s turns on spark topology -> every phone turn shows
   "Connection problem" despite succeeding; retries DUPLICATE turns. Must address
   before KC-G3 (raise deadline or fix latency).
2. Android APK build broken on main: flutter_appauth 8.0.3 hardcodes compileSdk 31 vs
   AGP 9 (A3 gates were analyze+test only — never built an APK). Minimal workaround
   UNCOMMITTED on the MacBook (app/android/build.gradle.kts: raise lib modules to 36).
   MUST be committed/fixed before the KC-G3 phone build.
3. Voice routes unmounted on :8100 (STUDY_TUTOR_VOICE_ENABLED unset) — by design; add
   flag + STT/TTS env when app-voice testing is wanted.

## Ops notes
- "Back to connection" in the Reachy app = daemon backend STOP. Recovery:
  POST /api/daemon/start?wake_up=true (then app restart). Volume resets are common
  after reboot: POST /api/volume/set {"volume": 88-95}.
- s2s left RUNNING with tutor set resident post-smoke (robot usable); coordinate with
  dcl before reclaiming the GPU.
