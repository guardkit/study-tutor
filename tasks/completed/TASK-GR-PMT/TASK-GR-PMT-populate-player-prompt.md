---
id: TASK-GR-PMT
title: "Wave 5 — BLOCK-2: populate player.md with verbatim Open WebUI system prompt"
task_type: feature
parent_review: TASK-REV-GRD5
parent_task: TASK-GR-DEMO
feature_id: FEAT-FD32
wave: 5
implementation_mode: task-work
complexity: 1
estimated_minutes: 10
dependencies: []
soft_dependency_of: TASK-GR-WIRE
status: completed
priority: critical
created: 2026-05-05T22:30:00+00:00
updated: 2026-05-06T00:00:00+00:00
completed: 2026-05-06T00:00:00+00:00
completed_location: tasks/completed/TASK-GR-PMT/
operator_verification:
  ac_pmt_04: pending
  reason: |
    AC-PMT-04 (live MCP tutor_turn → Socratic response) is operational
    acceptance, captured at PR-review or post-merge demo retest. The
    running MCP servers in the operator's environment have the empty
    placeholder cached at MCPAdapter.__init__ time and need a fresh
    spawn to load the new prompt. Operator will re-run the demo task
    test (TASK-GR-DEMO) after merging, which exercises this path end-
    to-end and produces the Socratic-mode transcript evidence.
  recipe: See "AC-PMT-04 — operator follow-up" section below.
tags:
  - graphiti
  - mcp
  - phase-1-gate-closure
  - prompt-fix
  - wave-5
related:
  - TASK-GR-DEMO
  - TASK-REV-GRD5
  - TASK-GR-WIRE
  - TASK-GR-CONF
  - FEAT-PO-001
conductor_workspace: wave5-mcp-blockers-wave1-1
test_results:
  status: passed_with_pre_existing_unrelated_failure
  coverage: null
  last_run: 2026-05-05T23:30:00+00:00
  notes: |
    169 passed, 3 skipped, 1 failed. The single failure is
    tests/unit/knowledge/test_graphiti_client_wiring.py::test_cross_encoder_sentinel_raises_on_arbitrary_method_name
    — confirmed pre-existing on pristine HEAD (markdown-only change cannot
    affect graphiti_client tests). Out of scope for TASK-GR-PMT.
---

# Wave 5 — BLOCK-2: populate player.md with verbatim Open WebUI system prompt

## Why this exists

The 2026-05-05 MCP tutor session attempt (TASK-GR-DEMO) found that
`roles/tutor/prompts/player.md` is a placeholder stub:

```
<!-- FEAT-PO-001 will populate this from domains/gcse-english/GOAL.md -->
```

`MCPAdapter.__init__` reads this file at construction time
([adapter.py:124](../../../src/study_tutor/mcp/adapter.py#L124)) and passes it as the system prompt to
`gemma4-tutor`. With an empty prompt, the model falls back to general-purpose LLM behaviour
(lecture-style information dumps) instead of the Socratic questioning behaviour the same model produces
via Open WebUI on GB10. The fine-tuning works; the prompt-wiring is missing.

The full Open WebUI system prompt that activates Socratic behaviour lives at
`/opt/llama-swap/models/gemma4-tutor/system-prompt.txt` on GB10 (`promaxgb10-41b1`). This task copies
that prompt verbatim into the repo file. FEAT-PO-001's eventual GOAL.md → prompt-generation pipeline
replaces this file later (Phase 2); this is an explicit Phase-1 expedient.

See [TASK-REV-GRD5 review report §AC-REV-03](../../../.claude/reviews/TASK-REV-GRD5-review-report.md)
for the design rationale (option (b1) — verbatim copy — chosen over (b2) generator-based wiring).

## Acceptance Criteria

- [ ] **AC-PMT-01** — `roles/tutor/prompts/player.md` contains the full text from
  `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt` on GB10 as of the date of this task. The
  load-bearing final directive — *"Never do the work for the student — ask questions that guide them
  toward the answer"* — must be present.

- [ ] **AC-PMT-02** — A one-line provenance comment is present at the top of the file:

  ```markdown
  <!-- Verbatim copy of /opt/llama-swap/models/gemma4-tutor/system-prompt.txt on GB10 (promaxgb10-41b1), <YYYY-MM-DD>. FEAT-PO-001 will replace this with GOAL.md-derived generation. -->
  ```

  The date must be the actual capture date.

- [ ] **AC-PMT-03** — The body of the prompt (everything below the provenance comment) is plain text
  with no embedded markdown comments. The HTML-comment provenance line is the only `<!-- -->` block in
  the file. Rationale: `role_config.load_player_prompt()` reads the file as-is and passes the entire
  contents to the model; markdown comment markers are not parsed and become literal context.

- [ ] **AC-PMT-04** — A single live MCP `tutor_turn` call (Phase-0 path is fine; this task does NOT
  depend on TASK-GR-WIRE) demonstrates a Socratic-style response — model produces a question or guided
  prompt rather than a lecture. Paste the transcript excerpt into the PR description as evidence.

- [ ] **AC-PMT-05** — Lint/format pass on the modified file (markdown). No Python changes; existing
  unit tests are unaffected and continue to pass.

## Test Requirements

This is primarily a static-asset change. Verification:

1. **File contents** — `git diff` shows the new prompt body and the provenance comment.
2. **Manual smoke** — start the MCP server (`study-tutor serve`); invoke `tutor_start_session` then one
   `tutor_turn` from Claude Desktop or via the smoke harness; confirm the response is question-led. AC-PMT-04
   requires the transcript paste; this is the operational acceptance.
3. **No regression** — existing unit + integration tests (`pytest`) all pass.

## Implementation Notes

### Capturing the prompt from GB10

```bash
# From the MacBook with Tailscale up:
ssh promaxgb10-41b1 cat /opt/llama-swap/models/gemma4-tutor/system-prompt.txt > /tmp/openwebui-prompt.txt

# Or, via the open-webui RUNBOOK:
# docs/research/ideas/RUNBOOK-open-webui-tutor-access.md
```

If the file content has changed since the source review (2026-05-05), use the *current* GB10 contents
and adjust the provenance date accordingly. The point is to mirror what's running in production on the
working surface, not to pin an arbitrary historical revision.

### Why no markdown body

`MCPAdapter.__init__` at [adapter.py:124](../../../src/study_tutor/mcp/adapter.py#L124) calls
`role_config.load_player_prompt()` which (per the loader convention in `roles/loader.py`) reads the
prompt file as raw text. The text is then passed verbatim to `LLMClient.generate(user_message, system_prompt)`.
There is no markdown-rendering or comment-stripping step — anything in the file becomes part of the
model's system prompt context.

The provenance comment at the top is acceptable because LLMs tolerate irrelevant header text well; the
benefit of greppable provenance outweighs the negligible context-window cost. Additional comments in the
body would be both pointless (they don't render) and noisy in the model's context.

### What this task does NOT do

- Does NOT modify `domains/gcse-english/GOAL.md`. That's FEAT-PO-001 territory.
- Does NOT introduce a generator from GOAL.md to the prompt. Also FEAT-PO-001.
- Does NOT add a hashing / drift-detection mechanism between GB10 and the repo. If drift becomes a real
  problem post-Phase-1, that's a separate task.

### Coupling with TASK-GR-WIRE

TASK-GR-WIRE *should* land after TASK-GR-PMT for cleanest demo evidence (Coach-revision evidence under
AC-DEMO-01.2 needs to come from a Player using the real Socratic prompt, not the lecture stub). However
there is no hard build dependency — TASK-GR-WIRE compiles and tests independently of this file's
contents. The recommendation is documented as `soft_dependency_of: TASK-GR-WIRE` in the frontmatter; if
the operator opts to parallelise via Conductor, the only cost is "Coach revision evidence captured on
TASK-GR-WIRE looks confounded by lecture-mode prompt" — fixable by re-running the demo session after
TASK-GR-PMT lands.

## Implementation Evidence (2026-05-05)

**Capture path used**: `ssh promaxgb10-41b1 cat /opt/llama-swap/models/gemma4-tutor/system-prompt.txt > /tmp/openwebui-prompt.txt`. File came back at 12 lines, 1063 bytes.

**Verbatim match**: `diff /tmp/openwebui-prompt.txt <(tail -n +2 roles/tutor/prompts/player.md)` returned no differences.

**AC status**:

| AC | Status | Evidence |
|---|---|---|
| AC-PMT-01 (verbatim copy + load-bearing directive) | ✅ HELD | `diff` shows exact match; `grep -c "Never do the work for the student" roles/tutor/prompts/player.md` = 1 |
| AC-PMT-02 (single-line provenance comment with date) | ✅ HELD | Line 1 of `roles/tutor/prompts/player.md`, dated 2026-05-05 |
| AC-PMT-03 (plain-text body, only one `<!-- -->` block) | ✅ HELD | `grep -c "<!--" roles/tutor/prompts/player.md` = 1 |
| AC-PMT-04 (live MCP `tutor_turn` shows Socratic response) | ⏳ DEFERRED — operator verification required | See below |
| AC-PMT-05 (lint/format pass; no Python regressions) | ✅ HELD with caveat | Markdown-only change; pytest = 169 passed / 3 skipped / 1 unrelated failure pre-existing on pristine HEAD |

### AC-PMT-04 — operator follow-up

A live `tutor_turn` was attempted from this `/task-work` session. The MCP server processes that this Claude Code session is wired to were spawned at session start (before the prompt edit), and `MCPAdapter.__init__` at [adapter.py:124](../../../src/study_tutor/mcp/adapter.py#L124) reads `roles/tutor/prompts/player.md` once at construction — so the running adapter has the empty placeholder cached. The single live call returned a **lecture-mode response** ("In Act 1 Scene 7, Shakespeare presents Macbeth's ambition not as a simple desire for power, but as a destructive force..." with structured headers and bullet points and no questioning), which is itself evidence of the Phase-0 gap this task fixes. The fix is on disk; verifying it requires a fresh server spawn.

**Operator verification recipe** (run after PR pull, before merge):

```bash
# 1. Restart the MCP server (e.g. in Claude Desktop: Settings → MCP → reload, or:)
pkill -f "study-tutor serve --role tutor" && sleep 1   # only kill if you own all the processes
# 2. New session in Claude Desktop or task-work session in Claude Code; then:
#    tutor_start_session(student_id="ac-pmt-04")
#    tutor_turn(session_id=..., user_message="I need help analysing how Shakespeare presents Macbeth's ambition in Act 1 Scene 7 — please could you explain it to me?")
# 3. Expect a question-led response (e.g. "Before I show you the analysis, let's start with what you already notice — what stands out to you in the soliloquy?"), not a lecture. Paste excerpt into PR description.
```

The lecture-mode transcript captured in this task-work session is preserved in the conversation log as the **before** evidence for the PR description; the operator's restart-and-retry produces the **after** evidence.

### Pre-existing unrelated test failure

`tests/unit/knowledge/test_graphiti_client_wiring.py::test_cross_encoder_sentinel_raises_on_arbitrary_method_name` fails on pristine `main` (`dfd4fdb`) without any TASK-GR-PMT changes applied. Markdown-only edit to `roles/tutor/prompts/player.md` cannot affect a Python unit test in `study_tutor.knowledge.graphiti_client`. Out of scope for this task; should be tracked separately.

## Cross-references

- [TASK-REV-GRD5 review report §AC-REV-03](../../../.claude/reviews/TASK-REV-GRD5-review-report.md) — design rationale (verbatim copy chosen over generator wiring)
- [docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md §"Finding 2"](../../../docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md) — original BLOCK-2 finding with quoted GB10 prompt
- [src/study_tutor/mcp/adapter.py:124](../../../src/study_tutor/mcp/adapter.py#L124) — load site
- [docs/research/ideas/RUNBOOK-open-webui-tutor-access.md](../../../docs/research/ideas/RUNBOOK-open-webui-tutor-access.md) — Open WebUI access reference
- [TASK-GR-DEMO](../TASK-GR-DEMO-end-to-end-mcp-tutor-session.md) — parent task being unblocked
