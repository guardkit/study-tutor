---
id: TASK-VOX-R08
title: "Author the reconciled Scholar profile (tools + persona)"
task_type: declarative
parent_review: TASK-REV-RCH4
feature_id: FEAT-VOICE-004
wave: 3
implementation_mode: task-work
complexity: 3
dependencies: [TASK-VOX-R07, TASK-VOX-R03]
repo: fleet-gateway
---

# Author the reconciled Scholar profile (recon D4)

Update the Scholar profile to add `ask_tutor` and reconcile the known repo-vs-Pi drift
**to the Pi where the Pi is right** (the Pi's installed-app reality is authoritative — the
truth was captured live in R03).

## Acceptance criteria

- **AC-R08-1**: `tools.txt` adds `ask_tutor`; the known-broken `emotion` tool stays
  **absent** (it is broken in the installed app version); `task_cancel` / `task_status`
  are **present** (the Pi already runs them).
- **AC-R08-2**: `instructions.txt` no longer chains the broken `emotion` tool; it includes
  the tutoring tool-selection guidance, the slow-turn filler (ASSUM-008), and the
  tutor-unavailable handling (ASSUM-007) — using the drafted copy below verbatim (or lightly
  adapted to the final persona voice, keeping the never-invent-an-answer rule).
- **AC-R08-3**: The persona's subject aligns with the shared constant from R06 (ASSUM-001) —
  no residual English/maths mismatch.
- **AC-R08-4**: All modified files pass project-configured lint/format checks with zero
  errors.

## Coach validation

- Diff the profile against the R03-captured Pi state; assert `emotion` absent,
  `task_cancel`/`task_status` present, `ask_tutor` added, subject reconciled; lint clean.

## Persona copy — drafted 2026-07-07 (closes ASSUM-007 / ASSUM-008)

Add to `instructions.txt`, in Scholar's voice (warm, British, older-sibling, 2–4 sentences,
spoken aloud). Mirrors the existing never-invent-progress rule.

**ASSUM-008 — slow-turn filler.** A tutoring turn via `ask_tutor` takes ~5 s+, so speak a
"thinking" line **immediately before** calling the tool, then deliver the answer in your own
voice. Rotate naturally so it isn't the same phrase every time:

> - "Ooh, good question — let me have a proper think about that one."
> - "Right, let me work that through with you — give me a sec."
> - "That's a good one. Let me think it through so I get it right for you."
> - "Let me have a proper look at that — one moment."

**ASSUM-007 — tutor unavailable.** If `ask_tutor` returns `"The tutor isn't reachable right
now."`, **do not invent an answer**. Say so warmly and keep the open-mic conversation going;
never mention tokens, servers, or errors:

> "I can't get through to the tutor just this second — no drama, let's have another go at
> that in a minute. We can still natter in the meantime."

(Same handling whether the tutor is down or credentials are refused — the tool returns the
identical string, so there is nothing technical to leak. This parallels the existing
`query_student_model` `data_available=False` honesty rule.)

## Notes

- `voice.txt` (`Kore`) is OpenAI-only and ignored by the backend — not copied; the Ryan
  voice is set server-side (R01).
