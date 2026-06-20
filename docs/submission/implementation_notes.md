# Study-Tutor — Implementation Findings for Submission

Status snapshot of what's verified, what's partial, and what should
not be claimed in the Kaggle Gemma 4 Good Hackathon submission. Three
load-bearing findings, each with evidence and a recommended next step.

This is a working document — capture, not a press release. Treat the
"Suggested wording" blocks as drop-in copy for the technical write-up
and the "Recommended follow-ups" as the prioritised fix list.

---

## TL;DR

| Surface | Verified? | Honest claim | Caveat |
|---|---|---|---|
| **Graphiti student model** | ✅ live | Persistent per-topic confidence; topic selection adapts across sessions | Memory does **not** reach the Player's prompt — see Finding 1 |
| **RAG corpus** | ✅ ingested | Selective retrieval over Macbeth + Inspector Calls + Power & Conflict (581 chunks) | 0% citation-anchor coverage — see Finding 2 |
| **Player–Coach loop** | ✅ live | Four-session demo on 2026-05-07; Coach revise loop fired (`attempts=2`) | — |
| **Technical write-up** | ❌ stub | n/a | All §1–§13 are placeholder stubs — see Finding 3 |

---

## Finding 1 — Graphiti memory: topic-adaptive, not content-adaptive

**Verdict:** real adaptive loop, but operates at the **planning layer**,
not at the layer where the fine-tuned model generates the tutoring text.

### What's verified live

Live demo on 2026-05-07 via Claude Desktop → MCP → FalkorDB
([TASK-GR-DEMO](../../tasks/completed/TASK-GR-DEMO/TASK-GR-DEMO.md);
gate flips in [phase-1-validation.md](../research/ideas/phase-1-validation.md#L236)):

- 4 full tutoring sessions ran end-to-end.
- Persistent student model (year_group=10, target_grade=7, subjects,
  6 topic confidences) read at `tutor_start_session`, written at
  `tutor_session_end`.
- Topic confidence for "Lady Macbeth's ambition" demonstrably moved
  **55% → 56% → 57% → 58%** across the four sessions — the round-trip
  proving itself.
- Coach revise loop fired in session 4 turns 1 + 5 (`attempts=2`,
  `decision=accept`).
- Phase-1 validation gates G3/G4/G5/G6/G13 flipped from **Falsified →
  Held** with cited evidence.

### What Graphiti memory *does* drive

[src/study_tutor/planner/pipeline.py:375](../../src/study_tutor/planner/pipeline.py#L375)
calls `get_student_state` and feeds it into the deterministic planner:

1. **Topic selection** — `pick_lowest_confidence_topic` picks the
   learner's weakest topic outside a 48 h cooldown
   ([rules.py:114](../../src/study_tutor/planner/rules.py#L114)).
2. **Focus AOs** — pulled from the topic's AO mapping.
3. Plan also computes `related_misconceptions`, `opening_prompt`, and
   `rationale`.

The whole plan is returned in the MCP `tutor_start_session` response
as `plan_summary`
([adapter.py:105-123](../../src/study_tutor/mcp/adapter.py#L105-L123)) —
so an MCP client (e.g. Claude Desktop) sees the topic, opening
prompt, and misconceptions and *can* steer with them.

### What Graphiti memory does **not** do — load-bearing gap

The fine-tuned Gemma Player receives **none** of the planner output
in its prompt. Two pieces of evidence:

1. **`SessionState` doesn't transport it.** Only carries
   `session_id / student_id / text_name / topic / focus_aos / mode`
   ([session_state.py:39-44](../../src/study_tutor/tutoring/adapters/session_state.py#L39-L44)).
   Misconceptions and confidence are computed by the planner but
   never enter the boundary object handed to the orchestrator.
2. **The Player adapter explicitly ignores `SessionState` in its
   prompt.** From the docstring of
   [llm_player_adapter.py:147-164](../../src/study_tutor/tutoring/adapters/llm_player_adapter.py#L147-L164):

   > "`session_state` is accepted for Protocol parity but its fields
   > are not yet woven into the prompt — Phase-1 wiring keeps the
   > prompt scope narrow (player system prompt + raw learner message)."

   The code does `_ = session_state.session_id` (a no-op touch),
   then `client.generate(learner_message, self._player_prompt)` —
   a **static** system prompt plus the raw learner message. Topic,
   focus AOs, confidence, and misconceptions never reach the model.

### Why sessions still felt personalised

When run via Claude Desktop, the calling Claude receives the rich
`plan_summary` from `tutor_start_session` and can steer the
conversation around it. So the personalisation experienced in the
GR-DEMO sessions is a **client-side** effect — Claude Desktop's
Claude using the plan summary — not the Gemma fine-tune being
conditioned on memory.

### Suggested wording for the submission

> *"A Graphiti knowledge graph persists per-topic confidence for the
> learner. A deterministic planner reads it to select each session's
> focus — the weakest topic outside a cooldown window — and session
> outcomes write back, so topic selection adapts measurably across
> sessions (verified 55→58% progression across four live sessions on
> 2026-05-07)."*

**Don't claim:** that the tutor *tailors its teaching* to the
student's specific misconceptions. That signal is computed by the
planner but never reaches the Player's prompt.

### Honest caveats to keep on hand

- The `session_completed` episode write is verified by direct
  `GRAPH.QUERY` against FalkorDB, not via `mcp__graphiti__get_episodes`
  — that MCP tool has an upstream bug (queries the wrong graph). The
  write path is fine; the read-back convenience tool isn't.
- The Phase-1 seed writes intra-group edges only; cross-group
  relationships are denormalised (ADR-ARCH-021 §G2). Say "persistent
  student model with topic-confidence tracking", not "full
  multi-entity knowledge graph".

### Recommended follow-up (high impact)

**Weave memory into the Player prompt.** Contained change:

1. Add `misconceptions: tuple[str, ...]` and
   `confidence_percentage: float | None` to `SessionState`
   ([session_state.py](../../src/study_tutor/tutoring/adapters/session_state.py)).
2. Populate them in
   [adapter.py:310](../../src/study_tutor/mcp/adapter.py#L310) from
   the cached `SessionPlan`.
3. Inject `topic` + `focus_aos` + `misconceptions` into the prompt
   assembled by `LLMPlayerAdapter.respond` /
   `_assemble_revise_prompt`
   ([llm_player_adapter.py](../../src/study_tutor/tutoring/adapters/llm_player_adapter.py)).

Honour the ASSUM-LCA-006 prose-injection invariant: pass
misconceptions as **structured fields** (named slots in the system
prompt), not concatenated into the user-message string.

This turns "memory selects the topic" into "memory shapes the
lesson" — a strictly stronger hackathon story.

---

## Finding 2 — RAG corpus: all three texts ingested, but 0% citation-anchor coverage

**Verdict:** retrieval and verification work across the full demo
set; the *annotated-citation* enrichment doesn't.

### What's verified

`data/chroma/` (ingested 2026-05-10) holds **581 PRIMARY_TEXT
embedded chunks**, sidecar at `data/chroma/.primary_text_index`
registers all three primary texts:

| `text_name` | Chunks | Source | Type |
|---|---:|---|---|
| `macbeth` | 253 | docling `.md` | play |
| `an_inspector_calls` | 274 | docling `.md` | play |
| `power_and_conflict_poems` | 54 | docling `.md` | poetry anthology |

Per the runbook ([RUNBOOK-rag-ingest-and-smoke.md](../runbooks/RUNBOOK-rag-ingest-and-smoke.md)
— "last verified 2026-05-08") the wiring smoke runs green against
the GB10 llama-swap embedder. Selective retrieval, BGE reranker,
source-typed quote verifier, AO3 bypass, and graceful degradation
are all implemented and live-tested.

**Consequence:** a session on any of the three texts gets
`reason=retrieve:primary_present` (not the analysis-mode skip).
The fine-tune-plus-RAG selective-retrieval thesis is genuinely
active across the whole demo set.

### The gap — citation anchors

Direct query of the chunk_json column in
`data/chroma/chroma.sqlite3`:

```sql
SELECT tn.string_value AS text,
       SUM(cj.string_value LIKE '%"citation_anchor":{%') AS with_anchor,
       COUNT(*) AS total
  FROM embedding_metadata tn
  JOIN embedding_metadata cj ON tn.id = cj.id
 WHERE tn.key='text_name' AND cj.key='chunk_json'
 GROUP BY tn.string_value;
```

Result — **every chunk has `citation_anchor: null`:**

| text | with_anchor | total |
|---|---:|---:|
| `an_inspector_calls` | 0 | 274 |
| `macbeth` | 0 | 253 |
| `power_and_conflict_poems` | 0 | 54 |

### Concrete impact

- **Retrieval works** — passages come back and ground the Player. ✅
- **Quote verification works** — the verifier still confirms verbatim
  primary-text matches and strips/corrects fabricated quotations. ✅
- **What's missing** — verified quotes are **not annotated with
  structured Act/Scene/Line citations**. The "annotated citation
  anchor" enrichment produces nothing on this corpus.

### Why

- **Power & Conflict poems (54 chunks)** — *expected*. No
  `PoetryCitationAnchor` exists in the schema yet
  ([TASK-PRV-009](../../tasks/backlog/TASK-PRV-009-poetry-citation-anchor.md),
  backlog). Poems were always going to land anchor-less.
- **Macbeth + An Inspector Calls (both plays)** — *should* have
  `PlayCitationAnchor`s. Likely cause: the anchor inferrer was
  designed against the Standard Ebooks `.txt` layout, and docling's
  `.md` output flattens the Act/Scene structure (sample chunk 0
  of Macbeth is a run-on `"Contents ACT I .......3SCENE I. A desert
  place..."` blob — no clean headings for the inferrer to anchor on).

This is the exact gap
[TASK-RAG-003](../../tasks/backlog/TASK-RAG-003-end-to-end-rag-smoke-session.md)
(still in backlog) was designed to catch — its AC says "expect
≥90% anchor coverage for plays post-PRV-008." Currently at 0%.

### Suggested wording for the submission

> *"Selective RAG over a licensed corpus of three GCSE set texts —
> Macbeth, An Inspector Calls, and the AQA Power & Conflict
> anthology (581 embedded chunks, ingested via docling and embedded
> on a GB10 llama-swap endpoint). A per-turn decision retrieves
> primary-text passages to ground the tutor's answer, and a
> post-hoc verifier checks every quotation against the source text,
> correcting or stripping anything not verbatim."*

**Don't claim:** that quotes are annotated with precise
Act/Scene/Line citations. That enrichment isn't producing output
on the current docling-ingested corpus.

### Recommended follow-up (medium impact)

1. **Investigate the anchor inferrer against docling output.**
   Locate the inferrer (likely in
   [src/study_tutor/knowledge/corpus.py](../../src/study_tutor/knowledge/corpus.py)
   or `corpus_models.py`); diff a docling chunk against a Standard
   Ebooks chunk; identify the heading-shape mismatch.
2. Either patch the inferrer to recognise the docling heading
   shape, or re-process the source PDFs with a docling option that
   preserves Act/Scene structure, then re-run
   `scripts/ingest_corpus.py --reset`.
3. Add `PoetryCitationAnchor` as a separate follow-up
   ([TASK-PRV-009](../../tasks/backlog/TASK-PRV-009-poetry-citation-anchor.md)).

---

## Finding 3 — Technical write-up still all stubs

[docs/submission/technical-writeup.md](./technical-writeup.md) — every
section (§1 Problem Statement through §13 Acknowledgements) is a
placeholder one-liner. This is the unticked **G8** validation gate
from `phase-1-validation.md`. Whatever the submission deadline
becomes, this is the largest pure-writing gap remaining.

### Recommended approach

Draft §5 (Architecture) and §11 (Evaluation) first using the
findings above — they're the sections where the precise wording
matters most and where overclaiming is easiest. The remaining
sections (problem statement, fine-tuning specifics, on-device
deployment, copyright, roadmap) are largely
write-from-source-material exercises that can ride on the existing
`docs/architecture/`, `docs/research/`, and `docs/gamification/`
content.

---

## Prioritised follow-up backlog

Ranked by impact-per-hour for the hackathon submission:

| # | Action | Impact | Effort |
|---|---|---|---|
| 1 | Weave `topic` + `focus_aos` + `misconceptions` into Player prompt (Finding 1) | **High** — turns "topic-adaptive" into "content-adaptive" | ~2–4 h |
| 2 | Draft technical-writeup.md §5 and §11 (Finding 3) | **High** — submission gate G8 | ~2 h |
| 3 | Fix docling anchor inference for plays (Finding 2) | Medium — strengthens RAG claim from "verifies" to "verifies and cites" | ~2–4 h (depends on docling output shape) |
| 4 | Land [TASK-RAG-003](../../tasks/backlog/TASK-RAG-003-end-to-end-rag-smoke-session.md) two-path live smoke | Medium — closes G7, provides a CI-replayable artefact | ~3 h |
| 5 | `PoetryCitationAnchor` for P&C poems (TASK-PRV-009) | Low — known scope-deferred | ~1–2 h |

---

## Evidence index

Files and queries used to support the findings — for fast re-verification later.

### Graphiti memory path
- Read at session start: [pipeline.py:375](../../src/study_tutor/planner/pipeline.py#L375)
  (`get_student_state` call inside `plan_session`).
- Topic selection rule: [rules.py:114](../../src/study_tutor/planner/rules.py#L114)
  (`pick_lowest_confidence_topic`).
- Plan returned to MCP client: [adapter.py:105-123](../../src/study_tutor/mcp/adapter.py#L105-L123)
  (`_plan_summary`).
- `SessionState` field list: [session_state.py:39-44](../../src/study_tutor/tutoring/adapters/session_state.py#L39-L44).
- `SessionState` built in `tutor_turn`: [adapter.py:310-317](../../src/study_tutor/mcp/adapter.py#L310-L317)
  (no misconceptions / confidence passed in).
- Player ignores session_state in prompt: [llm_player_adapter.py:147-164](../../src/study_tutor/tutoring/adapters/llm_player_adapter.py#L147-L164).
- Live demo evidence: [phase-1-validation.md §"Phase 2 Wave 5 — Operator handoff"](../research/ideas/phase-1-validation.md#L236).
- Demo task: [TASK-GR-DEMO](../../tasks/completed/TASK-GR-DEMO/TASK-GR-DEMO.md).

---

## Player–Coach harness — how it actually runs

> **Where to look:** [src/study_tutor/tutoring/orchestrator.py](../../src/study_tutor/tutoring/orchestrator.py), the two adapters in [src/study_tutor/tutoring/adapters/](../../src/study_tutor/tutoring/adapters/), and the prompts under [roles/tutor/prompts/](../../roles/tutor/prompts/). Diagram: [diagrams/player-coach-loop.svg](diagrams/player-coach-loop.svg).

### The two roles

- **Player** — the tutor that actually talks to the learner. Production wiring is [LLMPlayerAdapter](../../src/study_tutor/tutoring/adapters/llm_player_adapter.py), backed by the fine-tuned Gemma 4 26B MoE model via `LLMClient`. System prompt: [roles/tutor/prompts/player.md](../../roles/tutor/prompts/player.md).
- **Coach** — an evaluator the learner *never sees*. Scores the Player's draft against a 6-criterion rubric. Production wiring is [LLMCoachAdapter](../../src/study_tutor/tutoring/adapters/llm_coach_adapter.py), backed by a separate Coach model resolved via `AGENT_MODELS__COACH_MODEL`. Prompt: [roles/tutor/prompts/coach.md](../../roles/tutor/prompts/coach.md). Rubric: [roles/tutor/criteria/definitions.yaml](../../roles/tutor/criteria/definitions.yaml).

Both adapters are defined as structural `Protocol`s (`PlayerLike`, `CoachLike` in `orchestrator.py`) so production wiring and the test suite plug in the same way.

### The per-turn loop

[`PlayerCoachOrchestrator.run_turn`](../../src/study_tutor/tutoring/orchestrator.py) executes one learner turn end-to-end:

1. **Quote-verifier** runs first (FEAT-PH1-004 RAG check against the primary text).
2. **Player.respond** → draft tutoring reply.
3. **Coach-handover** (TASK-PRV-006): the quote-verifier rewrites any unverified quotations in the Player draft before it reaches the Coach. Verifier metadata (`verifier_exception`, retrieval skip reasons) rides alongside.
4. **Coach.evaluate** → returns a `CoachVerdict` with `decision = accept | revise`, a `weighted_total` score, and structured `RubricFeedback` (one entry per criterion).
5. If **`decision == "accept"`** → return immediately. This is the **stable-turn guarantee**: once a draft is accepted, no further revision can replace it.
6. If **`decision == "revise"`** → call **`Player.revise`** with the verdict's `RubricFeedback`, re-run handover + Coach, repeat.
7. Hard cap: **`MAX_REVISION_ATTEMPTS = 3`**. On exhaustion, the orchestrator releases the **lowest-scoring** attempt seen, not the latest — that preserves the diagnostic signal "the system genuinely tried and these were the outputs" rather than masking a regression where revisions get progressively worse.
8. **Fallbacks:**
   - Coach unreachable → return the Player's unevaluated reply with the turn flagged for session-end review; no revision attempts made.
   - Player unavailable mid-revision → release the last successful attempt with a provider-unavailable flag.
   - Player unavailable on the first attempt → return an empty `TurnResult` with `decision=fallback, attempts=0` so the MCP boundary can render a graceful retry.

### The load-bearing security invariant

The Coach can and does produce free-text reasoning, but **none of it ever reaches the learner or even the Player on revision**. The only thing the Player sees on revision is a list of structured pointers:

```
- criterion_id: ao1_evidence; target_score: 0.70
- criterion_id: socratic_quality; target_score: 0.80
```

That assembly is `_assemble_revise_prompt` in [llm_player_adapter.py](../../src/study_tutor/tutoring/adapters/llm_player_adapter.py). `RubricFeedback.suggested_focus` deliberately exists in the schema but is *not* fed into the prompt — adding it would re-open the prose-injection channel that TASK-DTL-001 specifically closed.

`validate_loop_configuration` enforces the invariant at session start: if anything would route Coach prose into the learner path, or if the revision input channel is anything other than `rubric_feedback`, the session **refuses to start**. That refusal is a deployment error, not a runtime fallback — it propagates as `OrchestratorConfigurationError`.

### Concurrency model

The orchestrator is **constructed fresh per turn** and holds **no session-scoped mutable state**. Two concurrent sessions get two independent `PlayerCoachOrchestrator` instances on the shared event loop; there is no class-level container into which one session's Coach observations could leak into another's. The adapters follow the same rule — system prompts are cached at construction, but `LLMClient` is built per-call so an env-var rotation between turns is observed without restarting the server.

### Observability — what every turn emits

Each turn returns a frozen `TurnResult` carrying:

- `response` — the learner-facing reply (never includes Coach text)
- `decision` — `accept` | `exhausted` | `fallback`
- `verdict` — the Coach verdict for the released response (or `None` on Coach-unreachable fallback)
- `attempts` — how many Player invocations were made (1–3)
- `flagged_for_review` + `flag_reason` — set on exhaustion, fallback, or over-budget latency
- `duration_seconds` — wall-clock latency; turns over `LATENCY_BUDGET_SECONDS = 30.0` are flagged but still returned
- `verifier_metadata` — the quote-verifier signal for the released response (introduced TASK-PRV-006)

An optional `on_flag` callback fires whenever a turn is flagged so the session-end summary ([tutoring/session_end.py](../../src/study_tutor/tutoring/session_end.py)) can roll up review markers.

### One-sentence pitch for the video

> "There are two LLMs behind every reply: a Player that drafts the tutor's response, and a Coach that silently grades it against a six-criterion rubric. If the Coach isn't satisfied, the Player gets up to three structured revision attempts — but the Coach's own words never reach the learner, only its scores."


