---
task_id: TASK-REV-C7D1
review_mode: architectural
review_depth: standard
source_document: docs/reviews/architecture/claude-desktop-review-system-arch-output.md
date: 2026-04-19
reviewer: architectural-reviewer (meta-triage of Claude Desktop feedback)
phase: Phase 0 → /system-design gate
---

# Review Report: TASK-REV-C7D1 — Analyze Claude Desktop architecture review feedback

## Executive Summary

Claude Desktop reviewed the `/system-arch` output and recommended proceeding to `/system-design`
after fixing items 1–4. This report triages every finding (F1–F5, O1–O5) against the actual
artefacts in the repo, records **accept / defer / reject** with rationale, and spawns
concrete follow-up actions.

**Bottom line:** Reviewer's recommendation holds. **Go** to `/system-design` on Sunday
morning after F1–F4 are applied. F5 is correctly deferred *into* `/system-design`. Of
the smaller observations, O1, O2, and O5 are accepted for small ADR/plan edits; O3 and
O4 are watch-list items, not blockers.

**Score:**

| Dimension | Score | Notes |
|---|---|---|
| Review quality (is the feedback right?) | 95/100 | All nine code-level claims verified against actual files. One claim (O3 framing) reframed, not rejected. |
| Blocker count | 1 | F1 — embedding dimension mismatch will fail Phase 1 seeding. |
| Pre-`/system-design` edit count | 4 | F1, F2, F3, F4 (four edits across ADR-007, ADR-008, ADR-015 + `.guardkit/graphiti.yaml`). |
| Deferred-to-`/system-design` | 1 | F5 — Subject enum value shape. |
| No-action / watch-list | 2 | O3 (Phase 1 revisit), O4 (pre-submission polish). |

## Context Used

No Graphiti knowledge graph context loaded for this review — the scope is tightly
defined (10 pre-enumerated findings, all verifiable against files in-repo). All findings
were cross-checked directly against:

- `docs/architecture/decisions/ADR-ARCH-{003,006,007,008,012,013,014,015}.md`
- `docs/architecture/domain-model.md` (§8 shared kernel)
- `docs/architecture/container.md` (session container declaration)
- `docs/architecture/assumptions.yaml` (ASSUM-003, ASSUM-007, ASSUM-013)
- `.guardkit/graphiti.yaml` (live config)
- `docs/research/ideas/phase-0-build-plan.md` (FEAT-PO-004 gate context)

## Findings Triage

### F1 — Embedding dimension mismatch (hard bug)

**Review claim:** `.guardkit/graphiti.yaml` and ADR-ARCH-007 both declare
`embedding_dimensions: 1024`, but `nomic-embed-text-v1.5` returns 768. No Matryoshka
truncation is mentioned anywhere.

**Verified:** Yes.
- `.guardkit/graphiti.yaml:14` — `embedding_dimensions: 1024`
- `docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md:52` — `embedding_dimensions: 1024`
- `nomic-embed-text-v1.5` native output dimension is 768 (widely documented; matches
  the existing agentic-dataset-factory ChromaDB wiring the reviewer cites).
- No mention of Matryoshka Representation Learning truncation anywhere in the ADR set.

**Triage: ACCEPT — hard bug, spawn implementation task.**

**Rationale:** If FalkorDB indexes at 1024 and the embedder returns 768, Phase 1 seeding
fails at the first write. This is not a nit; it is a boot-time error. Acceptance
criterion of this task explicitly requires F1 to be an implementation task (not a note),
so it will be spawned.

**Action:** Implementation task (see "Spawned Subtasks" below) that edits both files to
`embedding_dimensions: 768` and adds a short ADR note confirming the model's native
dimension.

---

### F2 — Phase 0 `tutor_start_session` "long-running" rationale

**Review claim:** Scope (SR-07) classifies `tutor_start_session` as long-running because
it "includes Graphiti read of student model," but Phase 0 has no Graphiti. The
architecture's behavioural claim (`≤1s` return) is correct; the *reason* is different —
it is architected as long-running for Phase-1 forward compatibility.

**Verified:** Yes. ADR-ARCH-008 line 37 classifies the tool as long-running without
naming the forward-compatibility rationale explicitly. The scope document frames it
around a current Graphiti read that does not exist yet.

**Triage: ACCEPT — low-effort ADR-008 rationale edit.**

**Rationale:** If `/feature-spec FEAT-PO-002` inherits the scope's framing, the resulting
Gherkin may assert behaviour ("completes within N seconds *because* it reads Graphiti")
that doesn't match the Phase 0 implementation. Making the rationale explicit at the
ADR level prevents that drift.

**Action:** Bundle with F3 (same ADR). Single edit to ADR-ARCH-008 adding a rationale
note.

---

### F3 — stdio child-process session scope

**Review claim:** Phase 0 session state is an in-memory dict inside a single MCP stdio
child process. Claude Desktop launches a fresh child per conversation, so
`tutor_session_status(session_id=...)` across conversations fails. Acceptable for
Phase 0 (ASSUM-003) but must be captured as an explicit behavioural note so the 16 May
demo doesn't trip over it.

**Verified:** Yes.
- `docs/architecture/container.md:31` — `Container(session, "Tutor Session Manager", "Python / in-memory dict", ...)`.
- `docs/architecture/assumptions.yaml:45-53` — ASSUM-003 says "sessions surviving MCP
  server restarts is not a Phase 0 requirement," which is the generic version of this
  limitation but does not call out the stdio-child-per-conversation specifics.
- ADR-ARCH-008 describes MCP stdio as the transport/trust boundary but does not
  document the session-scope consequence.

**Triage: ACCEPT — ADR-008 behavioural note + demo-script constraint.**

**Rationale:** This is a real bear-trap for a recorded demo. The fix is cheap (one
paragraph in ADR-008) and the downside of missing it is a live demo failure on 16 May.

**Action:** Bundle with F2. Add a "Phase 0 session scope" behavioural note to
ADR-ARCH-008 that calls out:
1. A fresh stdio connection = a fresh process = a fresh (empty) session dict.
2. Demo script constraint: do not close and re-open the stdio transport mid-session.

---

### F4 — ADR-015 AWS region framing

**Review claim:** ADR-015 says Bedrock "runs in a UK-adjacent region," but ADR-006 and
the Phase 0 build plan name us-east-1 / us-west-2. Those are Virginia / Oregon — not
UK-adjacent in a GDPR sense. Either confirm eu-west-2 supports Custom Model Import for
Gemma 4 31B, or rewrite the framing honestly.

**Verified:** Yes.
- `docs/architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md:62` —
  "runs in a UK-adjacent region."
- `docs/architecture/assumptions.yaml:99-116` — ASSUM-007 explicitly names "us-east-1
  or us-west-2" as the selected region, confidence medium.
- `docs/architecture/decisions/ADR-ARCH-006-dual-inference-path-ollama-bedrock.md`
  (line 94 "Phase 0 build-plan §Prerequisites") references build-plan prerequisites
  that consistently name us-east-1 / us-west-2.

**Triage: ACCEPT — ADR-015 edit + verification step on 22 Apr during FEAT-PO-004.**

**Rationale:** A residency claim that doesn't match the actual region posture is the
kind of thing a hackathon judge *will* spot. Two-step fix: (a) factual verification of
eu-west-2 availability for Gemma 4 31B Custom Model Import; (b) rewrite ADR-015 to
match whichever region actually runs the import.

**Action:** Implementation task spawned (see below). Verification step folds into
FEAT-PO-004 prerequisites (Monday/Tuesday 21–22 April). Whichever way the
verification lands, ADR-015 gets updated before `/system-design` copies its residency
claim into the design doc.

---

### F5 — Shared Kernel A `Subject` enum value shape

**Review claim:** `domain-model.md §8.1` declares `Subject.ENGLISH_LANGUAGE = "English Language"`.
Human-readable StrEnum values are hostile to Graphiti group IDs (`subject:gcse-english`
per ADR-014) and to JSON stability. Decide slug values or a `.slug` property during
`/system-design`.

**Verified:** Yes.
- `docs/architecture/domain-model.md:366-368` — StrEnum with display values.
- `docs/architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md:38` —
  `subject:gcse-english` group-ID convention.
- `docs/architecture/domain-model.md:175-176` — explicit link to the slug form.

**Triage: DEFER to `/system-design`, with explicit carry-forward note.**

**Rationale:** This is a contract-shape decision, not an architecture decision. It
belongs in `/system-design` where Pydantic model shapes and enum conventions get
nailed down. The important thing is that `/system-design` *inherits* this constraint
rather than re-discovering it.

**Action:** Record in the **Carry-Forward to `/system-design`** section below so the
`/system-design` prompt picks it up.

---

### O1 — ADR-013 middleware integration seam

**Review claim:** ADR-013 (Proposed) is correctly deferred to P2, but the
CompositeBackend route-based permissions pattern in ADR-012 already provides the
middleware insertion point. Worth making the seam explicit so FEAT-PO-007 inherits the
awareness.

**Verified:** Yes. ADR-013 lines 25-41 describe `GamificationMiddleware` as a possible
shape but do not link back to ADR-012's CompositeBackend route-scoped permissions
(which are the actual insertion point the middleware would attach to).

**Triage: ACCEPT — one-sentence ADR-013 edit, not a blocker.**

**Rationale:** Cheap to do now, cheaper than rediscovering in June.

**Action:** Edit ADR-013 "Consequences" section to add one line linking to ADR-012's
CompositeBackend middleware seam.

---

### O2 — ASSUM-007 Bedrock contingency

**Review claim:** ASSUM-007 (Bedrock supports Gemma 4 31B) is medium confidence and
on the Phase 0 critical path. The current revisit_trigger says "Ollama-primary posture
stays and demo-week scheduling becomes tighter" but does not name which of the three
DEC-07 GB10 workloads (dataset expansion / re-fine-tune / architect-agent training)
gets squeezed if Bedrock is out. Easier to decide now than at 3am on 11 May.

**Verified:** Yes.
- `docs/architecture/assumptions.yaml:99-116` — ASSUM-007 acknowledges tighter
  scheduling but names no contingency priorities.
- `docs/research/ideas/phase-0-build-plan.md` — FEAT-PO-004 validation on Tuesday
  22 April is the gate but has no fallback decision tree.

**Triage: ACCEPT — decision needed from user, spawn capture task.**

**Rationale:** This is a genuine forward-look decision, not a doc fix. The right
output is a written priority ordering of the three DEC-07 workloads under the "Bedrock
out" branch. Owner is the user (product/training-schedule decision); the spawned task
captures the decision once made.

**Action:** Task spawned (owner: user) to (a) pick the squeeze ordering and (b) record
it under ASSUM-007's revisit_trigger or in `docs/research/ideas/phase-0-build-plan.md`.

---

### O3 — ADR-003 turn-level Coach feedback loss framing

**Review claim:** ADR-003's loss acknowledgment ("if the tutor crashes between
session-end and Graphiti flush, the session-level state is lost") frames the loss as a
single event, but in practice every active-turn observation is at risk during the whole
session. Worth revisiting during Phase 1 testing if real MCP disconnects are observed.

**Verified:** Yes — ADR-003 lines 74-76 do frame this as a single-moment loss. The
reviewer's reframing (the entire active-session window is exposed) is accurate.

**Triage: DEFER — Phase 1 watch-list item, no ADR edit now.**

**Rationale:** The reviewer explicitly says "worth revisiting during Phase 1 testing if
real MCP disconnects are observed." Editing ADR-003 now to pre-document a worry that
may not materialise is premature; adding a Phase 1 revisit trigger is enough. If Phase
1 testing surfaces real disconnects, spawn a dedicated mitigation task (e.g. per-turn
append to an on-disk WAL, or shorter-horizon Coach flush).

**Action:** No immediate edit. Captured as a Phase 1 testing watch-item in the
decision log below.

---

### O4 — Diagram node budget (presentation)

**Review claim:** `system-context.md` and `container.md` are "well under the 30-node
threshold." For a hackathon submission, use more of the budget.

**Triage: DEFER — pre-submission polish, not `/system-design` blocker.**

**Rationale:** Correct observation, wrong moment. `/system-design` is about
contract shapes and component responsibilities; diagram density is a submission-readiness
concern. Revisit in Phase 2 when building the submission deck (already planned in
FEAT-PO-005 technical write-up scaffolding).

**Action:** Captured as a pre-submission polish item in the decision log; no task
spawned now.

---

### O5 — Graphiti seeding decision

**Review claim:** Do NOT seed `domain-model.md`, `system-context.md`, `container.md`,
or `assumptions.yaml` as `full_doc` Graphiti episodes. Keep Graphiti as the decision
record, disk as the reference library.

**Triage: ACCEPT as a confirmed decision — record in decisions log.**

**Rationale:** The reviewer is confirming a handoff decision that was made but not yet
captured formally. Writing it down prevents the decision being re-litigated every
time someone notices the reference docs aren't in Graphiti.

**Action:** Record as a new decision entry (proposed: `DEC-09` or next available ID)
in `docs/research/ideas/decisions-log-2026-04-17.md`: "Reference prose (domain-model,
system-context, container, assumptions) stays on disk; Graphiti holds decisions and
session-derived entities only."

---

## Go / No-Go on `/system-design`

**Decision: GO to `/system-design` Sunday morning, conditional on F1–F4 being applied
first.**

Reasoning:

1. **F1 is the only hard blocker.** Everything else is a doc-consistency fix.
2. **F2–F4 are low-effort ADR edits** (single ADR, a few lines each). They take
   under an hour combined and prevent `/system-design` from inheriting wrong framing.
3. **F5 is correctly scoped for `/system-design`** — the carry-forward note below
   ensures the decision actually gets made there rather than lost.
4. **No new finding surfaced in this triage** that changes the recommendation. The
   reviewer's list was complete and accurate.

No timeline slip is implied; F1–F4 are ~1–2 hours of editing + one verification
check, well within the Saturday→Sunday morning window.

## Carry-Forward to `/system-design`

The `/system-design` prompt must explicitly address:

- **F5 — Subject enum value shape.** Decide between:
  - Slug-style values (`Subject.ENGLISH_LANGUAGE = "english-language"`) with a
    separate `.display` property (or a module-level display map).
  - Keep human-readable values but add a `.slug` property to the enum.
  - Constraint: the chosen shape must align with ADR-014 group-ID conventions
    (`subject:gcse-english`) without requiring a per-MCP-call translation step.

No other findings are deferred to `/system-design`. (O3 and O4 are Phase 1 / Phase 2
concerns respectively.)

## Spawned Subtasks

The following implementation tasks are recommended. They will be created automatically
via the [I]mplement checkpoint (if the user chooses that route).

### Wave 1 (blocking `/system-design`, can run in parallel)

1. **TASK-PO-FIX-EMBED-DIM** — Fix `embedding_dimensions` 1024 → 768 (F1)
   - Files: `docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md`,
     `.guardkit/graphiti.yaml`
   - Add a one-line note to ADR-007 confirming nomic-embed-text-v1.5's native dimension.
   - Mode: task-work (has quality gate — wrong value breaks Phase 1 seeding).
   - Complexity: 2.

2. **TASK-PO-ADR008-SESSION-SCOPE** — Clarify ADR-008 rationale + stdio session scope (F2 + F3)
   - File: `docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md`
   - Edit 1: Add rationale note in the SR-07 classification table clarifying that
     `tutor_start_session` is "architected as long-running for Phase-1 forward
     compatibility," not because Phase 0 reads Graphiti.
   - Edit 2: Add a "Phase 0 session scope" behavioural note covering stdio child-process
     lifetime + demo-script constraint.
   - Mode: direct (doc-only).
   - Complexity: 2.

3. **TASK-PO-ADR015-REGION** — Verify eu-west-2 Bedrock Custom Model Import + update ADR-015 (F4)
   - Step 1: Verify eu-west-2 availability for Gemma 4 31B Custom Model Import (folds
     into FEAT-PO-004 prerequisites, 21–22 April).
   - Step 2: Rewrite the "UK-adjacent" framing in
     `docs/architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md` to
     match actual region. If US region, explicitly acknowledge residency posture as
     a Phase 3 concern for the hackathon.
   - Mode: task-work (has a verification step).
   - Complexity: 3.

### Wave 2 (non-blocking, can happen any time before Phase 2)

4. **TASK-PO-ADR013-MIDDLEWARE-SEAM** — Make CompositeBackend seam explicit (O1)
   - File: `docs/architecture/decisions/ADR-ARCH-013-middleware-level-gamification-engine-future.md`
   - Add one sentence to "Consequences" linking the middleware shape to ADR-012's
     CompositeBackend route-scoped permissions.
   - Mode: direct (doc-only, one-line edit).
   - Complexity: 1.

5. **TASK-PO-ASSUM007-CONTINGENCY** — Capture Bedrock-out contingency (O2)
   - Files: `docs/architecture/assumptions.yaml` (ASSUM-007 revisit_trigger) and/or
     `docs/research/ideas/phase-0-build-plan.md`.
   - **Owner decision required (user):** which of the three DEC-07 GB10 workloads
     (dataset expansion / re-fine-tune / architect-agent training) gets squeezed if
     FEAT-PO-004 fails on 22 Apr?
   - Record the chosen priority ordering so the decision is not made at 3am on 11 May.
   - Mode: task-work (decision + doc update).
   - Complexity: 3.

6. **TASK-PO-DEC09-NO-SEED-REF-DOCS** — Record Graphiti seeding decision (O5)
   - File: `docs/research/ideas/decisions-log-2026-04-17.md`.
   - Add a new decision entry (next available DEC-NN) confirming that reference prose
     stays on disk, Graphiti holds decisions only.
   - Mode: direct (doc-only).
   - Complexity: 1.

### No action (watch-list / deferred)

- **O3** (ADR-003 framing) — revisit if Phase 1 testing surfaces real MCP disconnects.
- **O4** (diagram node budget) — revisit during FEAT-PO-005 submission write-up.
- **F5** (Subject enum shape) — decided in `/system-design` (carry-forward above).

## Summary Table

| ID | Finding | Triage | Action | Target |
|---|---|---|---|---|
| F1 | Embedding dim 1024 vs 768 | **Accept** | Spawn task 1 | Pre-`/system-design` |
| F2 | `tutor_start_session` rationale | **Accept** | Bundle into task 2 | Pre-`/system-design` |
| F3 | stdio child-process session scope | **Accept** | Bundle into task 2 | Pre-`/system-design` |
| F4 | ADR-015 UK-adjacent region | **Accept** | Spawn task 3 + FEAT-PO-004 check | Pre-`/system-design` (verify 22 Apr) |
| F5 | Subject enum value shape | **Defer** | Carry-forward note | `/system-design` |
| O1 | ADR-013 middleware seam | **Accept** | Spawn task 4 | Before Phase 2 |
| O2 | ASSUM-007 Bedrock contingency | **Accept** | Spawn task 5 (user decision) | Before 11 May |
| O3 | ADR-003 turn-loss framing | **Defer** | Phase 1 watch-list | Phase 1 testing |
| O4 | Diagram node budget | **Defer** | Pre-submission polish | FEAT-PO-005 |
| O5 | Graphiti seeding decision | **Accept** | Spawn task 6 (record DEC-NN) | Before `/system-design` |

## Appendix — Verification Evidence

| Finding | File verified | Line(s) |
|---|---|---|
| F1 | `.guardkit/graphiti.yaml` | 14 |
| F1 | `docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md` | 52 |
| F2 | `docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md` | 37 |
| F3 | `docs/architecture/container.md` | 31 |
| F3 | `docs/architecture/assumptions.yaml` (ASSUM-003) | 45–53 |
| F4 | `docs/architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md` | 62 |
| F4 | `docs/architecture/assumptions.yaml` (ASSUM-007) | 99–116 |
| F5 | `docs/architecture/domain-model.md` | 366–368 |
| F5 | `docs/architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md` | 38 |
| O1 | `docs/architecture/decisions/ADR-ARCH-013-middleware-level-gamification-engine-future.md` | 25–62 |
| O2 | `docs/architecture/assumptions.yaml` (ASSUM-007) | 112–116 |
| O3 | `docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md` | 74–76 |
