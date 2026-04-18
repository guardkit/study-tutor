# Reachy Mini Integration — Conversation Starter

**Purpose:** Scope and bootstrap a dedicated Claude Desktop or Claude Code session to integrate Reachy Mini ("Scholar") with the Study Tutor for the 18 May 2026 hackathon demo.

**Trigger for spinning up the dedicated thread:** Scholar arrives on the home network (expected ~25 April based on 90-day delivery from late January order), OR 4 May 2026 (hackathon go/no-go gate), whichever comes first.

**Decision reference:** `decisions-log-2026-04-17.md` DEC-06 — stretch phase, hard sequencing rule (cannot block Phases 0–2), clear fallback to pre-recorded future-vision segment if the go/no-go fails.

**Status when read:** If this document is being read for the first time in a new Claude session, assume the main Study Tutor build is ongoing or complete and the reader is bootstrapping Reachy work as a parallel stretch thread.

---

## The goal in one paragraph

A 30-second segment of the hackathon demo video where Scholar (Reachy Mini Wireless) verbally reports Lilymay's study progress — streak count, current level and title, near-unlockable achievements, a targeted session suggestion — using natural speech, with some head movement and antenna animation for personality. The content is real data pulled from her Graphiti student model. Lilymay can optionally interact with Scholar in a follow-up clip to show the companion working live, but the primary demo target is a scripted scenario where Rich asks "How's Lilymay's revision going?" and Scholar replies in character.

This is the killer differentiator for the submission. Very few (probably no) other Gemma 4 Good Hackathon entries will have an embodied robot companion. The architectural story — AI tutor, Graphiti student model, gamification engine, all surfaced through a physical robot that can see and speak — is unique enough to matter.

---

## Context the new thread needs

### What Study Tutor looks like when Reachy work starts

- The fine-tuned Gemma 4 31B tutor is deployed (Phase 0 done) and Lilymay is using it via Open WebUI
- The DeepAgents tutoring harness with Player-Coach quality monitor is running (FEAT-PO-006, Phase 1)
- Graphiti student model is populated with real session history, topic confidence scores, XP, streak, achievements (FEAT-PO-004, Phase 1)
- Gamification state engine is producing deterministic event transitions (FEAT-PO-007, Phase 2)
- AWS Bedrock Custom Model Import is validated as a backup inference path (Phase 1, per DEC-07)

### Hardware state

- Reachy Mini "Scholar" ordered ~25 January 2026 (Wireless version, $449-class)
- Reachy Mini "Bridge" ordered ~1 February 2026 (second unit, likely post-hackathon)
- Expected delivery: 90 days from order = ~25 April 2026. Pollen Robotics has a track record of running slightly late; assume anywhere ~25 April to ~10 May is plausible.
- Target machine for development: MacBook Pro M2 Max (the same one running the Study Tutor MCP + Open WebUI during demos)

### Network topology

- MacBook on home WiFi, Tailscale-connected to: GB10 (Ollama/training), Synology NAS (FalkorDB), Google Gemini (Graphiti LLM)
- Reachy Mini Wireless needs to join the home network; MacBook reaches it on-LAN (Tailscale likely not needed inside the house)
- Proven reliable: the TASK-REV-B8E4 walkthrough shows Tailscale direct-connect at 1ms RTT, no DERP relay, no drops

### What's already been done (data points from the existing docs)

- `GCSE_Gamification_Research.md` has explicit Reachy interaction scenarios documented — "How's Eleanor's revision going?" → Reachy reports streak, level, recent XP, and upcoming achievements; "What achievements am I close to?" → Reachy identifies 2-3 nearest unlockable achievements and suggests a targeted session
- `gemma4-hackathon-submission-plan.md` §5.3 documents Reachy as the "gamification companion" solution to the single-user isolation problem
- Both docs describe Scholar as "verbally reports progress, reacts to achievements, and provides encouragement" — the demo moment is already narratively scoped

---

## What Pollen Robotics ships that we can reuse

**Primary SDK:** https://github.com/pollen-robotics/reachy_mini (branch: `develop`)

Key properties:
- Python SDK, `pip install reachy_mini` pattern
- Auto-detects Wireless vs Lite, auto-switches between localhost and network
- Client-server architecture: the Daemon runs on Scholar's onboard Raspberry Pi 4, your Python app connects over the network
- **Critical architectural note:** *"You can run your AI code on a powerful server while the Daemon runs on a Raspberry Pi connected to the robot."* This means our Graphiti-querying, Gemini-calling, TTS-producing code runs on the MacBook (or Bedrock), not on the Pi — it sends movement and speech commands to the Daemon.
- Core primitives: `goto_target()` for head/antenna/body movement with interpolation methods (linear, minjerk, ease, cartoon); media backend for camera frames and audio

**AI-agent-specific guide:** https://github.com/pollen-robotics/reachy_mini/blob/develop/AGENTS.md

Pollen explicitly wrote a Claude Code / Codex / Copilot onboarding doc. The recommended prompt for a fresh AI-agent thread is literally "I'd like to create a Reachy Mini app. Start by reading https://github.com/pollen-robotics/reachy_mini/blob/develop/AGENTS.md." That's the first action in the dedicated thread.

**Reference conversation app:** https://github.com/pollen-robotics/reachy_mini_conversation_app

This is the pivotal reuse target. Pollen ships a full conversational interaction app with:
- **Dual realtime LLM backends** — OpenAI Realtime or Gemini Live, auto-selected by `MODEL_NAME`. As of April 2026 the upstream default is Gemini Live. All features (tools, profiles, head tracking) work with both backends.
- **Custom profiles system** — `profiles/<n>/` containing `instructions.txt` (system prompt), `tools.txt` (enabled tools list), and optional Python files defining custom tools that subclass `core_tools.Tool`. A `LOCKED_PROFILE` constant in `config.py` creates distribution clones with a fixed personality.
- Head tracking (MediaPipe or YOLO face detection — `uv sync --extra mediapipe_vision` or `--extra yolo_vision`)
- Audio pipeline (fastrtc low-latency streaming) with console or Gradio UI modes
- Vision pipeline (realtime-model default, optional on-device SmolVLM2 via `--local-vision`)
- Daemon connection, layered motion queue (dances, emotions, goto poses, breathing with speech-reactive wobble blending), and error handling

**We do not fork.** The custom-profile abstraction is the integration point. There are two ways to add a Scholar profile, and the **external_content/ pattern is strongly preferred** for this project:

**Option A (preferred): External content directory.** Scholar lives in its own repo (`study-tutor-scholar/` or as a subdirectory of `study-tutor/`), pointed at by env vars. No upstream code is touched:

```
study-tutor-scholar/
└── external_content/
    ├── external_profiles/
    │   └── scholar/
    │       ├── instructions.txt     # system prompt (Scholar persona + response rules)
    │       ├── tools.txt            # enabled tools including query_student_model
    │       └── voice.txt            # Gemini voice pin, e.g. "Kore" or "Aoede"
    └── external_tools/
        └── query_student_model.py   # Graphiti reader, subclass of core_tools.Tool
```

`.env`:
```
REACHY_MINI_CUSTOM_PROFILE=scholar
REACHY_MINI_EXTERNAL_PROFILES_DIRECTORY=./external_content/external_profiles
REACHY_MINI_EXTERNAL_TOOLS_DIRECTORY=./external_content/external_tools
GEMINI_API_KEY=...
MODEL_NAME=gemini-3.1-flash-live-preview   # current upstream default, explicit for clarity
```

This gives clean separation: the Scholar repo is independently versioned, diffable, and could be open-sourced later without dragging in upstream history.

**Option B (acceptable): `profiles/scholar/` inside conversation_app.** Simpler initial setup (no env vars), but mixes our code with upstream. Acceptable for a quick spike; switch to Option A before the hackathon demo.

**Custom tool shape** (from `profiles/example/sweep_look.py`):

```python
# external_content/external_tools/query_student_model.py
from reachy_mini_conversation_app.tools.core_tools import Tool

class QueryStudentModelTool(Tool):
    name = "query_student_model"
    description = (
        "Look up Lilymay's current study progress: streak, level, recent XP, "
        "topic confidence, nearest unlockable achievements. Call this whenever "
        "the user asks how her revision is going or what she's close to."
    )

    async def run(self, args, deps):
        # deps provides daemon connection + other injected resources;
        # the tool body reads from the shared Graphiti student model
        progress = await fetch_graphiti_student_model("lilymay")
        return {
            "streak_days": progress.streak_days,
            "level": progress.level_name,
            "recent_xp": progress.xp_last_session,
            "near_achievements": progress.near_unlockable[:3],
        }
```

The tool returns a plain dict; Gemini Live narrates the values back in character per the `instructions.txt` persona. The conversation loop, motion system, and audio pipeline are completely untouched.

**For distribution-like behaviour during the demo** (one command, fixed personality, no profile switching in the Gradio UI), either clone the repo and set `LOCKED_PROFILE = "scholar"` in `src/reachy_mini_conversation_app/config.py`, or simply don't expose the Personality accordion during the video shoot — `REACHY_MINI_CUSTOM_PROFILE=scholar` plus muscle memory is sufficient.

**Closest built-in profile to study as a tone reference:** `chess_coach` ("a patient chess mentor"). The Scholar persona should lean toward patient-mentor-encouraging rather than pirate-captain-excitable. The 15 built-in profiles (`default`, `mars_rover`, `noir_detective`, `victorian_butler`, `mad_scientist_assistant`, `bored_teenager`, `cosmic_kitchen`, `hype_bot`, `captain_circuit`, `chess_coach`, `nature_documentarian`, `sorry_bro`, `tedai`, `time_traveler`, `example`) are all worth skimming for prompt-structure patterns, but `chess_coach` is the closest tonal match.

**Prompt fragment composition** is a feature: lines like `[identities/witty_identity]` in `instructions.txt` pull from `src/reachy_mini_conversation_app/prompts/`. Scholar can use this to reference shared fragments, or ignore it and just write monolithic instructions. For the hackathon, monolithic is fine.

**Precedent worth studying before coding:** `ravediamond/baby-reachy-mini-companion` (164 likes on HF Spaces) — *"a fully local Reachy Mini AI Companion for babies and kids"*. Closest community app to Scholar's shape (child-facing, personality-driven, voice-first, single-user). Read its source before designing Scholar's prompt and tool surface — it has already solved the "keep a child engaged in a calm, non-agitating way" problem that Scholar faces. Other useful precedents: `tierralibre/ReachyGotchi` (local voice), `yozkut/judgy_reachy_no_phone` (behaviour-reactive — relevant to Scenario 3 gamification reactions), `luisomoreau/hey_reachy_wake_word_detection` (wake-word primitive for Scenario 1's voice trigger).

**App store + Hugging Face Spaces:** One-click app installs directly from the robot's dashboard. This is the post-hackathon distribution path if we want to share Scholar-as-tutor-companion publicly.

**Out-of-scope but architecturally relevant: NVIDIA Spark & Reachy Photo Booth** (https://build.nvidia.com/spark/spark-reachy-photo-booth). Uses Redpanda (Kafka-compatible) message bus, NeMo Agent Toolkit with ReAct loop, `gpt-oss-20b` on TensorRT-LLM, Parakeet ASR, Kokoro TTS, FLUX.1-Kontext image gen, Detectron2+ByteTrack person tracking, MinIO. Six services in Docker Compose. This is almost exactly the `distributed_agent_orchestration_architecture.md` pattern with Redpanda in place of NATS — worth bookmarking as the reference build for **Bridge** (second Reachy, post-hackathon, Ship's Computer role), not for Scholar.

---

## The integration architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         MacBook (dev + demo)                 │
│                                                              │
│   ┌──────────────────────┐       ┌──────────────────────┐   │
│   │  Study Tutor MCP     │       │  Scholar Companion   │   │
│   │  (Phase 0/1 work)    │       │  (this thread)       │   │
│   │                      │       │                      │   │
│   │  - Tutor agent       │       │  reachy_mini_        │   │
│   │  - Session lifecycle │       │  conversation_app    │   │
│   │  - Graphiti write    │       │  w/ profiles/scholar │   │
│   └──────────┬───────────┘       │  - Gemini Live LLM   │   │
│              │                   │  - Custom tool:      │   │
│              │ shared             │    query_student_    │
│              │ Graphiti           │    model (Graphiti)  │   │
│              │ + gamification     └──────────┬──────────┘   │
│              │ state              over LAN   │              │
│              ▼                               ▼              │
└──────────────┼───────────────────────────────┼──────────────┘
               │                               │
               │  Tailscale                    │ Home WiFi
               │                               │
               ▼                               ▼
       ┌───────────────┐               ┌──────────────┐
       │ Synology NAS  │               │   Scholar    │
       │ FalkorDB      │               │  (Reachy     │
       │               │               │   Mini Wl)   │
       └───────────────┘               │              │
                                        │  Daemon on  │
                                        │  onboard Pi │
                                        └──────────────┘
```

**Key points:**
- Scholar is a *second* consumer of the same Graphiti student model, not a separate product
- The tutor (Study Tutor MCP) writes state on session events; Scholar reads state on voice trigger or schedule
- Scholar does not need to call Gemini — Graphiti reads + a local text-to-speech pipeline is enough for the demo moment
- If we want Scholar to answer free-form questions (post-hackathon), we add an LLM call into the companion app; for the demo, scripted scenarios are fine

---

## Four demo scenarios worth scoping

Ranked by return-on-integration-effort. Build the first one first; add the others if time permits.

### Scenario 1 — "How's her revision going?" (voice query → verbal report)

Rich asks the question out loud. Scholar's MediaPipe face-tracking already has him in frame. STT picks up the question, the companion app routes it as a "progress summary" intent, reads Graphiti for streak + level + recent XP + active quest, composes a natural-language response, speaks it with light head-tilt and antenna animation. ~8 seconds. Closest to the scenario already documented in `GCSE_Gamification_Research.md`. **Demo-critical.**

### Scenario 2 — "What am I close to?" (voice query → targeted suggestion)

Lilymay asks Scholar what achievements she's close to. Companion app reads gamification state, finds the 2-3 nearest unlockable achievements (by XP delta or topic-confidence threshold), speaks the top one with a session suggestion. ~10 seconds. Adds student-facing interaction to the demo. **Strong stretch.**

### Scenario 3 — Session milestone acknowledgement (event-triggered)

During a recorded tutoring session (via Open WebUI), when Lilymay completes a session or unlocks an achievement, Scholar reacts verbally and with animation ("Nice one — that's your 12-day streak!"). Event-triggered rather than voice-triggered. Requires the tutoring harness to emit events Scholar can subscribe to (NATS-style pub/sub or direct invocation). **Nice-to-have if the Phase 1 session lifecycle already emits events.**

### Scenario 4 — Lilymay interacts freely (full conversation mode)

Full use of Pollen's conversation_app shape: Lilymay asks arbitrary questions, Scholar holds a conversation with context from her student model via a custom `query_student_model` tool. With Gemini Live now the upstream conversation-app default and custom profiles a first-class extension point, the engineering cost of Scenario 4 has collapsed compared to January: it's mostly a matter of writing a good `instructions.txt` and exposing the student-model tool. **Plausible if Scenarios 1–3 land by ~7 May.** Still the riskiest scenario for demo reliability (free-form conversation has unbounded failure modes where Scenarios 1–3 are scripted), so build and test last.

---

## Go/no-go gate (4 May 2026)

Three criteria — all must be green to proceed with integration. If any red, fall back to pre-recorded future-vision segment (script already drafted in `gemma4-hackathon-submission-plan.md §6.4`).

| Criterion | Evidence required |
|---|---|
| **Platform operational (hardware OR simulator)** | EITHER Scholar unboxed, on home WiFi, Daemon running, dashboard reachable from MacBook browser; OR MuJoCo simulator path validated — `python -m reachy_mini.daemon.app.main --sim --no-localhost-only` running, Gradio UI connects, antenna-wiggle executes cleanly |
| **SDK exercised end-to-end** | `with ReachyMini() as mini: mini.goto_target(antennas=[0.5, -0.5], duration=0.5)` runs without error; simple speech playback working (hardware) or motion animation rendering (simulator) |
| **LAN/local path confirmed** | Hardware: latency from MacBook to Scholar Daemon measured (<50ms expected on LAN); no firewall blocking; `reachy_mini_conversation_app` dependency install succeeds. Simulator: same conversation-app install, `--gradio` mode launches at http://127.0.0.1:7860 |

**Background on allowing the simulator path:** Pollen's ship-date history suggests Scholar may not arrive in time (customers who ordered July 2025 were still waiting in December; clem at HF indicated many Jan/Feb 2026 orders wouldn't ship until Feb 2026+). Rather than binary-fail Reachy work if hardware is late, the simulator path produces real working code with a MuJoCo-rendered robot visual — better for the demo than a pure pre-recorded future-vision mock, and the work ports to hardware immediately once Scholar arrives (even post-submission for the v1.1 version).

If all three green on 4 May: proceed with Scenario 1 as the Reachy Phase deliverable, targeting completion by 10 May for inclusion in the demo video shoot (11–13 May). Hardware path is preferred; simulator path is the acceptable fallback, not a second-class substitute.

If any red on 4 May: stop Reachy work immediately, fall back to pure pre-recorded future-vision segment. No sunk-cost continuation.

---

## Recommended first prompt for the dedicated thread

Paste this to a fresh Claude Desktop or Claude Code session when Scholar arrives or 4 May, whichever comes first:

```
I'm integrating Reachy Mini ("Scholar") with the Study Tutor
(GCSE English AI tutor) for the Gemma 4 Good Hackathon submission,
deadline 18 May 2026. The integration is a stretch phase, go/no-go
gate already passed, hard deadline 10 May.

Start by reading these in order:
1. https://github.com/pollen-robotics/reachy_mini/blob/develop/AGENTS.md
   (Pollen's AI-agent onboarding guide — follow its methodology:
   check for agents.local.md first, write plan.md before coding,
   use `reachy-mini-app-assistant create --template conversation`
   to scaffold — NEVER create app folders manually)
2. /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/reachy-integration-conversation-starter.md
   (this conversation starter — full scope, demo scenarios, integration architecture)
3. /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/decisions-log-2026-04-17.md
   DEC-06 (the decision that authorised this work)
4. https://github.com/pollen-robotics/reachy_mini_conversation_app
   README — pay particular attention to the `profiles/` system,
   `instructions.txt`/`tools.txt` pattern, custom tools subclassing
   `core_tools.Tool`, and the `LOCKED_PROFILE` config constant. This
   is our integration point — we are NOT forking this repo.
5. Skim https://huggingface.co/spaces/ravediamond/baby-reachy-mini-companion
   source tree — the closest community precedent to Scholar's shape
   (fully local, child-facing, voice-first). Extract whatever is
   useful for the Scholar instructions.txt and tool surface.

Target: implement Demo Scenario 1 — "How's her revision going?" —
as a `profiles/scholar/` directory inside reachy_mini_conversation_app,
with a custom `query_student_model` Python tool that reads from the
existing Graphiti student model. Scope docs for Study Tutor Phase 1
are at /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/
and describe the student model schema we read from.

Before writing any code, write plan.md per the AGENTS.md methodology
(understanding of goal, technical approach, clarifying questions with
answer fields). Wait for answers before coding.

First concrete task: confirm the platform is operational. If Scholar
has arrived, run the quickstart antenna wiggle on hardware. If not,
stand up the MuJoCo simulator path (per go/no-go criterion 1) and run
the wiggle there. Either outcome counts; document which in
agents.local.md. Then propose a build plan for Scenario 1.
```

---

## What this thread should NOT do

- **Do not modify the Study Tutor core.** Scholar is a second consumer of the student model, not a contributor to it. If Scholar needs data the tutor doesn't write, that's a tutor-side feature request, not a Scholar-side workaround.
- **Do not use Pollen's Hugging Face app-store distribution path before the hackathon.** Distribution is post-submission work. For the demo, we run the app locally from our fork.
- **Do not add new LLM dependencies.** Gemini is already in the architecture for Graphiti. If Scenario 4 (free conversation) is built, it uses Gemini via the existing path; it does not introduce Claude, GPT, or any other provider.
- **Do not attempt Scenario 4 before Scenarios 1–3 work.** Full conversation mode is the stretchiest stretch.

---

## Related documents

- `decisions-log-2026-04-17.md` DEC-06 — the decision authorising this work
- `state-of-the-project-and-phase-recommendation.md` §7 Decision 6 — the original reasoning
- `GCSE_Gamification_Research.md` §3 — documented Reachy scenarios ("How's Eleanor's revision going?")
- `gemma4-hackathon-submission-plan.md` §5.3 — Reachy as gamification companion
- https://github.com/pollen-robotics/reachy_mini — SDK
- https://github.com/pollen-robotics/reachy_mini/blob/develop/AGENTS.md — AI-agent onboarding
- https://github.com/pollen-robotics/reachy_mini_conversation_app — reference conversation app to fork
