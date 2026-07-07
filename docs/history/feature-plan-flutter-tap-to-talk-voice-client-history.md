# /feature-plan — flutter-tap-to-talk-voice-client — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-plan flutter-tap-to-talk-voice-client — 2026-07-07T09:08:25Z

### Prompt

```
/feature-plan "Flutter tap-to-talk voice client" \
  --context features/flutter-voice-client/flutter-voice-client_summary.md
```

### Assistant response

I'll orchestrate the feature planning workflow. Let me start by reading the context file to understand the feature.

Let me explore the feature directory and related design docs.

Let me examine the app structure and find the voice design doc for the referenced sections.

Let me read the Flutter client design section (§6) which is the authoritative source for this feature.

I now have a thorough understanding of the feature: a well-specified Flutter client (FEAT-VOICE-003) with a design doc (§6), a 22-scenario `.feature` file, and an assumptions manifest. The app already uses a ports & adapters pattern I can extend.

Before I run the review analysis, let me clarify the review scope (Context A).

Recorded: **focus = all aspects**, **trade-off = quality/reliability**.

**Step 2.5 — Graphiti pre-planning context:** skipped. Graphiti is retired for study-tutor (per project memory); GuardKit commands run markdown-only. Continuing without knowledge-graph enrichment.

Now creating the review task.

Review task created: **TASK-REV-V3C1**. Now executing the decision-mode review.

Context A recorded (focus=all, tradeoff=quality). Graphiti unavailable — reviewing from codebase + design analysis. Producing the decision-mode review report now.

Here is the decision-mode review.

---

## 🔍 FEATURE PLANNING: Flutter tap-to-talk voice client (FEAT-VOICE-003)

**Review:** TASK-REV-V3C1 · mode=decision · depth=standard · focus=all · trade-off=**quality/reliability**

### Key finding

The architecture is **already pre-decided** by `docs/design/voice-tutor-and-reachy-design.md §6`: a new sibling `VoiceApi` port (frozen `SessionApi` untouched), `HttpVoiceApi` reusing the `HttpSessionApi` seams, `Fake`/`FlakyVoiceApi` for hermetic tests, mic/playback UX on `SessionScreen`. So the real decision is **sequencing/slicing** — and the dominant quality risk is the **"green-but-broken" fidelity seam** (a recording that uploads OK but reaches the tutor mis-authed / wrong session / re-encoded), which only the hermetic MockClient direction-pins catch.

### Option evaluation

| Option | Quality fit | Risk | Verdict |
|--------|-------------|------|---------|
| **1. Port + fidelity-pins first → MVP HTTP → streaming** | **Highest** | Low | ✅ **Recommended** |
| 2. Streaming-first | Medium | Medium (hardest surface as first foothold) | No |
| 3. Big-bang single task | Low | High (collapses the fidelity defence into UX churn) | No |

**Why Option 1:** front-loads the port + direction-pins before any UX, so every later slice sits on a proven-correct upload seam. MVP HTTP (`voiceTurn`) ships a transcript-first loop early; streaming (`voiceTurnStream` + `seq`-ordered playback) layers on without reworking the port. Encoder choice stays **gated** (ASSUM-006, Phase-0 m4a-against-live-STT) rather than hard-coded.

### Recommended breakdown — 7 tasks

1. **TASK-VC-001** — deps + Android/iOS manifests (scaffolding, cx 3)
2. **TASK-VC-002** — `VoiceApi` port + DTOs + 6 sealed error types (declarative, cx 3)
3. **TASK-VC-003** — `HttpVoiceApi` + **fidelity direction-pins** (feature, cx 6)
4. **TASK-VC-004** — Fakes + recorder (60 s / 10 MB stop, gated encoder) (feature, cx 5)
5. **TASK-VC-005** — SessionScreen tap-to-talk UX + degradation (feature, cx 6)
6. **TASK-VC-006** — Streaming `voiceTurnStream` + ordered playback (feature, cx 7)
7. **TASK-VC-007** — Dual-backend + live voice tests (testing, cx 5)

Full analysis saved to [TASK-REV-V3C1-review-report.md](.claude/reviews/TASK-REV-V3C1-review-report.md).

---

### 📋 DECISION CHECKPOINT

**[I]mplement** selected. Collecting implementation preferences (Context B).

**Context B recorded:** Approach = Option 1 (port+fidelity first), Execution = auto-detect waves, Testing = Standard (quality gates).

Generating the feature structure. Creating the 7 task files first.

Now the IMPLEMENTATION-GUIDE.md with the mandatory Mermaid diagrams.

Now generating the structured YAML feature file (Step 10). Let me verify the generator script exists first.

Feature YAML generated: **FEAT-VOICE-003** (5 waves, AC-quality clean). Running pre-flight validation (Step 8.5).

Validation passed. Now **Step 11 — BDD scenario linking** (wire up R2 by tagging scenarios with `@task:`). Preparing the matching request.

Status `ready` — 22 scenarios, 7 tasks. Now invoking the `bdd-linker` subagent to map scenarios to tasks.

Invoking the `bdd-linker` subagent to produce scenario→task mappings.

Mappings produced (all ≥ 0.6). Writing the response and applying the tags (Step 11.3).

All 22 scenarios tagged — R2 task-level BDD oracle is now active. Cleaning up temp files.

Let me update the review task status to reflect completion.
