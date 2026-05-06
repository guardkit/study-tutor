# Review: TASK-GR-DEMO — MCP Tutor Session Attempt

**Date:** 2026-05-05
**Reviewer:** Rich + Claude Desktop (pair session)
**Task:** TASK-GR-DEMO (Wave 5 — End-to-end MCP tutor session)
**Outcome:** Blocked — three implementation gaps prevent gate closure
**Session ID:** `1155da15-6c64-4db8-bd0c-16f0b0e6d4f5`

---

## What was attempted

A live 7-turn MCP tutor session conducted via Claude Desktop, targeting AC-DEMO-01 through AC-DEMO-07. Topic: Lady Macbeth's ambition (baseline confidence 55%, "developing" band — chosen per the task's guidance to pick a mid-range topic for detectable confidence delta).

## Pre-flight results (all green)

| Check | Result | Evidence |
|---|---|---|
| Lilymay seed in place | ✅ | `graphiti:search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returned Student node + 6 TopicConfidence nodes |
| Graphiti MCP reachable | ✅ | `graphiti:get_status` → `"ok"` |
| Study-tutor MCP tools loaded | ✅ | All 4 tools available: `tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end` |
| LLM endpoint up | ✅ | `curl http://promaxgb10-41b1:9000/v1/models` → `gemma4-tutor`, `qwen-graphiti`, `nomic-embed`, `qwen36-workhorse`, `architect-agent` |

## What worked

1. **MCP transport round-trip is fully functional.** `tutor_start_session(student_id="lilymay", topic_override="Lady Macbeth's ambition")` returned a session ID and plan summary. Seven `tutor_turn` calls all returned tutor responses. `tutor_session_end` returned `status: "ended"`. Zero transport errors.

2. **Graphiti seed is readable through MCP.** The pre-flight `search_nodes` call confirmed all typed-entity data from TASK-GSM-009 is intact and queryable — Student node with `year_group=10`, `target_grade="7"`, `enrolled_subjects=["English Literature", "English Language"]`, plus 6 TopicConfidence nodes spanning all three planner bands.

3. **The model produces reasonable English Literature tutoring content.** Even without the proper system prompt, `gemma4-tutor` generated substantive analysis of Lady Macbeth's ambition, the "unsex me here" soliloquy, gender roles in Jacobean England, and essay structure advice. The content quality is not the issue.

4. **Zombie process fix confirmed.** The Graphiti MCP zombie process issue (fixed prior to this session) is resolved — all MCP calls completed without hanging or orphaned processes.

## What did not work

### Finding 1: MCP server running Phase 0 path — no Coach invocation

**Location:** `src/study_tutor/mcp/adapter.py`, `tutor_turn()` method (lines ~130–165)

The adapter has two code paths:
- **Phase 1 path** (`self._orchestrator_factory is not None`): routes through `PlayerCoachOrchestrator.run_turn()`, returns `decision`, `attempts`, `flagged_for_review`, `duration_seconds` alongside `tutor_response`.
- **Phase 0 path** (`self._orchestrator_factory is None`): uses bare `LLMClient.generate()`, returns only `tutor_response`.

All 7 turns returned only `{"tutor_response": "..."}` with no orchestrator metadata, confirming the **Phase 0 path is active**. The `orchestrator_factory` is not being injected at MCP server startup.

**Impact:** AC-DEMO-01.2 (Coach revision required) cannot be satisfied. AC-DEMO-05/G5 (Coach feedback observable) cannot flip.

### Finding 2: Player prompt is a placeholder stub

**Location:** `roles/tutor/prompts/player.md`

Contents:
```markdown
<!-- FEAT-PO-001 will populate this from domains/gcse-english/GOAL.md -->
```

The MCP path sends an effectively **empty system prompt** to `gemma4-tutor`. This explains the lecture-style responses (information dumps, headers, bullet lists) rather than the Socratic questioning behaviour the model produces via Open WebUI, which has the full system prompt at `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt`.

The fine-tuned model's Socratic behaviour is activated by the system prompt — without it, the model falls back to general-purpose LLM behaviour. This is a prompt-wiring gap, not a model quality issue.

**Impact:** Even if the orchestrator were wired, the Player would generate non-Socratic responses for the Coach to evaluate, producing a doubly-degraded session.

### Finding 3: Graphiti write-back not implemented

**Location:** `src/study_tutor/mcp/adapter.py`, `tutor_session_end()` method (line ~175)

```python
# TODO(phase-1): add async Graphiti write per DEC-02
```

The `session_completed` episode write to Graphiti is a literal TODO. No code path exists to:
- Write a `session_completed` episode (AC-DEMO-02)
- Update `TopicConfidence` nodes after a session (AC-DEMO-03)

**Impact:** AC-DEMO-02 (episode written), AC-DEMO-03 (confidence delta), AC-DEMO-05/G6 (episode queryable) cannot be satisfied.

## AC-DEMO status

| AC | Status | Notes |
|---|---|---|
| AC-DEMO-01 | ⚠️ Partial | Transport round-trip works (7 turns). AC-DEMO-01.2 (Coach revision) not met — Phase 0 path active. |
| AC-DEMO-02 | ❌ Falsified | No `session_completed` episode. `get_episodes(group_ids=["student-lilymay"])` → empty. TODO in code. |
| AC-DEMO-03 | ❌ Falsified | TopicConfidence unchanged. Lady Macbeth's ambition still 55%, `last_revised_at` still epoch sentinel. |
| AC-DEMO-04 | ⚠️ Not captured | Phase 0 path has no timing instrumentation. MCP server logs need checking for any latency data. |
| AC-DEMO-05 | ❌ Cannot flip | G4 partial (transport works). G5 falsified (no Coach). G6 falsified (no episode). G13 partial. |
| AC-DEMO-06 | ❌ Cannot flip | Blocked by 02, 03, 05. |
| AC-DEMO-07 | ✅ N/A | No files modified in this attempt. |

## Contrast: Open WebUI vs MCP path

Lilymay has been using the tutor via Open WebUI and the sessions demonstrate genuine Socratic scaffolding — the model asks questions, draws out the student's thinking, builds on partial answers, and scaffolds toward Grade 7–9 analysis. Across multiple sessions (Macbeth, Ozymandias, poetry comparison flashcards), the student progresses from recall ("can you remind me") to comparative analysis ("the Duke's pride and craving for power compares with the dead king's attitude") to metacognitive strategy ("group cards by theme").

The MCP path, by contrast, produces lecture-style information dumps with headers and bullet lists. The difference is almost certainly the system prompt: Open WebUI has the full Socratic prompt, the MCP path has an empty stub.

This comparison is strong evidence that:
1. The fine-tuning works — behaviour is correctly activated by the system prompt
2. The model quality is not the issue — the same model produces excellent tutoring via Open WebUI
3. The MCP pipeline has wiring gaps, not model gaps

## Blocking items for TASK-GR-DEMO

Three implementation tasks must land before TASK-GR-DEMO can be re-attempted:

### BLOCK-1: Wire orchestrator_factory into MCP server startup

The `MCPAdapter.__init__()` accepts an `orchestrator_factory` parameter (added by TASK-DTL-003) but the MCP server entry point does not inject one. The entry point needs to construct a `PlayerCoachOrchestrator` factory and pass it to the adapter.

**Files:** MCP server entry point (likely `__main__.py` or CLI handler), `src/study_tutor/mcp/adapter.py` (consumer, no changes needed)

### BLOCK-2: Populate player prompt from domain config

`roles/tutor/prompts/player.md` contains a FEAT-PO-001 placeholder. Either:
- Copy the working Open WebUI system prompt (`/opt/llama-swap/models/gemma4-tutor/system-prompt.txt`) into this file, or
- Wire `GOAL.md` → player prompt generation as FEAT-PO-001 intended

The first option is a 30-second fix that unblocks immediately. The second is architecturally cleaner but takes longer.

### BLOCK-3: Implement Graphiti write-back in tutor_session_end

The `# TODO(phase-1): add async Graphiti write per DEC-02` in `tutor_session_end()` needs implementation:
- Write a `session_completed` episode to Graphiti (AC-DEMO-02)
- Update the relevant `TopicConfidence` node's `percentage`, `band`, and `last_revised_at` (AC-DEMO-03)

**Files:** `src/study_tutor/mcp/adapter.py` (`tutor_session_end`), plus whatever Graphiti client wiring is needed

## Session transcript summary (7 turns)

For the evidence trail, the session covered:

1. **Turn 1** (student: "I'm hazy on Macbeth, need a refresh") → Tutor: full plot/character/theme overview (lecture-style)
2. **Turn 2** (student: quotes about Lady Macbeth's determination) → Tutor: analysis of "milk of human kindness" metaphor
3. **Turn 3** (student: "Is Lady Macbeth basically just evil?") → Tutor: three perspectives on villainy (lecture-style, no Socratic push-back)
4. **Turn 4** (student: misconception about "unsex me here" = wanting to be male) → Tutor: corrected misconception, explained gender role subversion
5. **Turn 5** (student: "Shakespeare is saying women can't handle power") → Tutor: pushed back, asked whether it's the act or the gender (more Socratic)
6. **Turn 6** (student: "what three points for an essay?") → Tutor: structured essay advice
7. **Turn 7** (student: synthesis — "ambition requires rejecting your nature") → Tutor: confirmed, extended analysis

## Recommendation

Create a review task targeting BLOCK-1, BLOCK-2, and BLOCK-3 above. BLOCK-2 (copy Open WebUI system prompt into `roles/tutor/prompts/player.md`) is a quick win that should land first — it immediately improves the MCP session quality even before the orchestrator is wired. BLOCK-1 and BLOCK-3 are the structural fixes needed for full AC-DEMO gate closure.

## Cross-references

- TASK-GR-DEMO task file: `tasks/backlog/TASK-GR-DEMO-end-to-end-mcp-tutor-session.md`
- MCP adapter: `src/study_tutor/mcp/adapter.py`
- Player prompt stub: `roles/tutor/prompts/player.md`
- Phase 1 validation gate: `docs/research/ideas/phase-1-validation.md`
- Open WebUI system prompt: `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt` (GB10)
- Open WebUI RUNBOOK: `docs/research/ideas/RUNBOOK-open-webui-tutor-access.md`

## Appendix: Open WebUI system prompt (working)

This is the system prompt at `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt` on the GB10 that produces the Socratic tutoring behaviour via Open WebUI. BLOCK-2's quickest fix is to copy this verbatim into `roles/tutor/prompts/player.md`.

```
You are an expert GCSE English tutor supporting a Year 10 student studying the AQA specification.
Your role is to guide the student using Socratic questioning — help them discover answers
rather than providing them directly. You have deep knowledge of:
- AQA English Language (8700): Paper 1 and Paper 2 question types
- AQA English Literature (8702): Set texts including Macbeth, A Christmas Carol,
  An Inspector Calls, and the Power and Conflict poetry anthology
- The AO1–AO6 assessment objectives and mark scheme criteria
- Grade descriptors from Grade 1 through Grade 9

Always be encouraging, patient, and age-appropriate. When assessing a student's response,
give structured feedback aligned to the mark scheme. Never do the work for the student —
ask questions that guide them toward the answer.
```

The critical instruction is the final line: *"Never do the work for the student — ask questions that guide them toward the answer."* This single directive is what activates the fine-tuned Socratic behaviour. Without it (the MCP path), the model reverts to general-purpose LLM behaviour — comprehensive, well-structured, but pedagogically passive.
