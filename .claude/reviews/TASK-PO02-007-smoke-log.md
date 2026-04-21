# TASK-PO02-007 — Live Smoke Log

**Date:** 2026-04-21
**Operator:** Richard Woollcott
**Host:** MacBook Pro (Ollama running locally)
**Model:** `gcse-tutor-gemma4-moe:latest` (25.2B, Q4_K_M)
**Base URL:** `http://localhost:11434`

> The task doc guessed the model name was `gcse-tutor-gemma4-31b:Q4_K_M`. Actual
> tag served locally is `gcse-tutor-gemma4-moe:latest`. The `.env` and the
> smoke run use the actual tag.

---

## Pre-checks

- [x] **Ollama reachable.** `curl http://localhost:11434/api/tags` → 200, lists
      `gcse-tutor-gemma4-moe:latest` among 12 installed models.
- [x] **Config backup.** `claude_desktop_config.json` → `claude_desktop_config.json.bak-PH0-2026-04-20`.
- [x] **Config entry added.** `mcpServers.study-tutor.command` =
      `/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/mcp-wrapper.sh`.
      JSON validated; 5 servers now registered (graphiti, youtube-insights-mcp,
      architect-agent, product-owner-agent, study-tutor).
- [x] **.env hydrated.** `AGENT_MODELS__REASONING_MODEL=local`,
      `OLLAMA_BASE_URL=http://localhost:11434`,
      `OLLAMA_MODEL=gcse-tutor-gemma4-moe:latest`.

## Pre-flight stdio dry-run (before Claude Desktop restart)

Full four-call sequence ran end-to-end against the wrapper over stdio to
de-risk the manual test. Results:

| Call | Observed | Threshold | Status |
|---|---|---|---|
| `initialize` + `tools/list` | 4 tools advertised: `tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end` | must be exactly 4 | ✅ |
| `tutor_start_session` (subject=English Literature, topic=Macbeth) | `session_id` returned ~instant | <1s | ✅ |
| First turn *fired 4ms after session start* | 35.4s | n/a — not a realistic user pacing | ⚠️ |
| First turn *after 20s warm-up wait* | **12.17s** | <20s (warm-up must work) | ✅ |
| Second turn (back to back, history appended) | 24.88s | <30s acceptance bound | ✅ |
| `tutor_session_status` after end | `status: "ended"` | must be "ended" | ✅ |

**Warm-up interpretation.** The 35.4s cold-no-wait vs 12.17s cold-with-20s-wait
gap confirms the background warm-up (TASK-PO02-005) is doing real work. In
Claude Desktop UX, user pacing between tool calls (typing the next prompt,
reading the response) easily covers that 20s window.

**Content check (turn 1, post-warmup).** Excerpt:
> *"In Act 1 Scene 1, the witches serve several crucial dramatic and thematic
> purposes: Establishing Atmosphere: They immediately create a sense of chaos
> and disorder. The storm, thunder, and strange…"*

Covers atmosphere, chaos/disorder, thematic foreshadowing — matches the
"any tutor-appropriate response" acceptance bar.

**Content check (turn 2).** Follow-up about Macbeth's first line (Act 1 Sc 2):
model correctly quoted the *"So foul and fair a day…"* line and connected it
to the witches' *"Fair is foul, and foul is fair"* — i.e. the model **retained
session context from turn 1** and built on it. That satisfies the "session
state retained" acceptance criterion.

---

## Live Claude Desktop invocations

_Executed after Claude Desktop restart on 2026-04-21._

### Tool surface

MCP server `study-tutor` appears in the tool list with **exactly 4 tools**,
schemas resolve cleanly via tool_search:

| # | Tool | Required | Optional |
|---|---|---|---|
| 1 | `tutor_start_session` | `subject` | `topic`, `player_model` |
| 2 | `tutor_turn` | `session_id`, `user_message` | `player_model` |
| 3 | `tutor_session_status` | `session_id` | — |
| 4 | `tutor_session_end` | `session_id` | — |

### Session 1 — An Inspector Calls (J.B. Priestley)

- **session_id:** `4d302e56-2cf0-4976-a55d-5588778038d0`
- **Started:** 2026-04-21T12:08:04.829849+00:00
- **Subject / topic:** GCSE English Literature / An Inspector Calls
- **Lifecycle:** start → status (active, 0 turns) → turn → end (status: `ended`) — all transitions clean ✅
- **Turn 1 latency:** ~11s (under 15s tool-description budget)

**Prompt:**
> "Hi, can you help me understand how Priestley uses Inspector Goole as a
> dramatic device in An Inspector Calls? I'm specifically interested in the
> way his presence shifts the power dynamics on stage."

**Response shape:** thesis → 4 numbered sections (Disruption of Established
Order / Language and Rhetoric / Visual Power Shift / Exposing Hypocrisy) →
Key Takeaways → essay guidance. Consistent with GCSE essay scaffolding.

**Representative excerpt — structural analysis (lighting):**
> "The stage directions describe the lighting changing from 'pink and intimate'
> to 'harder' when the Inspector arrives. This symbolizes the exposure of
> the truth and the stripping away of the family's facade."

**Representative excerpt — closing guidance:**
> "When writing your essay, focus on specific examples from the text that
> show how the Inspector's presence changes the power balance in each scene.
> Connect these observations to Priestley's overall message about social
> responsibility and collective responsibility."

**Defect observed:** First-token generation artefact in sentence 2 —
`"He'to manipulate…"` (dropped subject/verb, orphaned apostrophe). Cosmetic,
isolated to opening stanza, rest of response clean.

### Session 2 — Macbeth (William Shakespeare)

- **session_id:** `a5bf98b7-62e2-4b9e-81ec-e05740fc3dc2`
- **Subject / topic:** GCSE English Literature / Macbeth
- **Lifecycle:** start → turn → end — all transitions clean ✅
- **Turn 1 latency:** ~13s (within budget)

**Prompt:**
> "Can you explain how Shakespeare presents Lady Macbeth's ambition in Act 1
> Scene 5? I'd like some specific quotes I could use in an essay."

**Response shape:** thesis → 4 numbered sections with quote+analysis pairs →
essay structure summary. Same scaffold as Session 1.

**Representative excerpt — opening:**
> "In Act 1 Scene 5, Shakespeare presents Lady Macbeth's ambition as both
> overwhelming and deeply transgressive. She is introduced not as a passive
> observer, but as a proactive force who immediately recognizes the
> opportunity for power and begins to strategize how to seize it."

**Representative excerpt — clean quote analysis (serpent imagery):**
> "The 'innocent flower' represents the mask of virtue and loyalty that she
> knows must be maintained to deceive Duncan and the court. The 'serpent'
> imagery is a clear biblical allusion to the serpent in the Garden of Eden,
> suggesting that her ambition is inherently sinful and treacherous."

**Defects observed:**

1. **Quote fidelity (HIGH severity for a tutor).** Fabricated or corrupted
   quotations:
   - Model produced: `"Come, you spirits / That tend on mortal coats…
     unmaculate me from the deed"`
   - Shakespeare: `"Come, you spirits / That tend on mortal thoughts,
     unsex me here…"`
   - The raven quote was similarly garbled vs. the real
     `"The raven himself is hoarse / That croaks the fatal entrance of
     Duncan"`.
   - **Clean quote:** `"Look like the innocent flower / But be the serpent
     under 't"` was rendered correctly.
2. **Truncation.** Response cut off mid-sentence:
   `"Body Paragraph 2: Analyse the deception and manipulation involved in
   her ambition (the "`. Suggests a `num_predict` / max-tokens ceiling hit
   rather than a model defect — worth checking the Ollama `generate`
   payload in `src/study_tutor/llm/client.py`.

### Session continuity note

The live test exercised two independent sessions rather than two turns in
one session, so in-session context-retention was not directly re-verified
in Claude Desktop. **It was verified during the pre-flight stdio dry-run
above** (turn 2 quoted Macbeth's *"So foul and fair a day…"* and explicitly
linked it back to the witches' *"Fair is foul, and foul is fair"* introduced
in turn 1). Session state storage is exercised by the unit suite as well.
A belt-and-braces live in-session follow-up is recommended but not a gate
blocker.

---

## Summary

| Check | Result |
|---|---|
| MCP server registered | ✅ |
| Exactly 4 tools exposed | ✅ |
| Session lifecycle (start / status / turn / end) | ✅ |
| Turn latency within 15s budget | ✅ (~11–13s) |
| Topic grounding | ✅ |
| GCSE-appropriate pedagogy shape | ✅ |
| Quote fidelity | ⚠️ Inspector Calls clean; Macbeth fabricated quotes |
| Output completeness | ⚠️ Macbeth response truncated mid-sentence |
| Token generation cleanliness | ⚠️ One first-token artefact in Session 1 |

## Gate declaration

**End-of-Saturday gate: GREEN** — FEAT-PO-002 is submittable as-is.

**Rationale.** Every hard acceptance criterion in TASK-PO02-007 is met:
Ollama reachable, config backed up, `study-tutor` registered with exactly
the 4 expected tools, session lifecycle clean, latencies well inside
budget, `tutor_turn` returning real tutor-appropriate responses with
correct topic grounding, `tutor_session_status` reporting `"ended"` after
`tutor_session_end`. The build-plan.md gate condition
("`tutor_turn` returns a real response") is satisfied — responses are
coherent, on-topic, and pedagogically well-structured.

The three ⚠️ items are **content-quality defects, not integration
defects**, and the task explicitly notes "exact content does not" matter
for the gate. They are logged as follow-ups below rather than as
gate-blockers.

## Follow-ups (do not block Phase 0 submission)

1. **Quote fidelity — HIGH priority for production.** Fabricated Shakespeare
   quotes are the most visible failure mode for a GCSE tutor. This is the
   correct problem to solve in the RAG layer (text grounding) rather than
   by prompt-patching the base model. Should be sequenced before multi-
   subject expansion.
2. **Response truncation.** Investigate Ollama `num_predict` default (or
   whatever max-tokens our client sends — `src/study_tutor/llm/client.py`
   currently sends no explicit cap). May be hitting Ollama's default
   `num_predict=128` or similar; verify in payload and bump to a tutor-
   appropriate ceiling.
3. **First-token artefact in Session 1.** Single occurrence, not reproduced
   in Session 2 or in stdio dry-run. Park as "watch list" — raise priority
   only if it recurs.
4. **Default model name in `src/study_tutor/llm/client.py:19`** still says
   `gcse-tutor-gemma4-31b:Q4_K_M` while the real tag is
   `gcse-tutor-gemma4-moe:latest`. `.env` overrides correctly, so runtime
   is fine, but the fallback default is wrong.
