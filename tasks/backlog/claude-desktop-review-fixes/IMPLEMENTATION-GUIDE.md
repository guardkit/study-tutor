---
feature_id: FEAT-CDR-C7D1
parent_review: TASK-REV-C7D1
feature_slug: claude-desktop-review-fixes
---

# Implementation Guide — Claude Desktop Review Fixes

## Execution Strategy

Two waves. Within each wave, subtasks touch different files and can run in parallel
(Conductor-optional). Across waves, Wave 1 must complete before `/system-design` runs;
Wave 2 can happen any time before Phase 2.

## Wave 1 — Blocks `/system-design`

Run these before Sunday morning.

### TASK-CDR-001 — Fix embedding_dimensions (F1)

**Files:**
- [`docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md`](../../../docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md) — line 52
- [`.guardkit/graphiti.yaml`](../../../.guardkit/graphiti.yaml) — line 14

**Change:**
```diff
- embedding_dimensions: 1024
+ embedding_dimensions: 768
```

**Why:** `nomic-embed-text-v1.5` is natively 768-dimensional. No Matryoshka truncation
is configured anywhere in the repo, so the 1024 value is an error. FalkorDB index
provisioning at 1024 would reject the 768-dim vectors the embedder returns, breaking
Phase 1 seeding at the first write.

**ADR note to add** (in ADR-ARCH-007, near the config block):

> Dimension is 768 — `nomic-embed-text-v1.5`'s native output. If Matryoshka truncation
> is ever introduced, update both this ADR and `.guardkit/graphiti.yaml` in the same
> commit.

**Verification:**
```bash
grep -n "embedding_dimensions" .guardkit/graphiti.yaml \
  docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md
# Both must show 768.
```

**Mode:** task-work (verifiable invariant).

---

### TASK-CDR-002 — ADR-008 rationale + stdio session scope note (F2, F3)

**File:** [`docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md`](../../../docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md)

**Edit 1 (F2)** — clarify the `tutor_start_session` row in the SR-07 classification
table (line ~37) or add a footnote immediately below it:

> `tutor_start_session` is architected as long-running for Phase-1 forward
> compatibility (where it will read the student model from Graphiti). In Phase 0
> the implementation is a UUID mint + in-memory dict insert that returns in ≤1s.
> The classification is stable across phases so `/feature-spec` does not need to
> re-classify the MCP contract when Graphiti lands.

**Edit 2 (F3)** — add a new "Phase 0 session scope" subsection to "Consequences"
(or directly below the classification table):

> **Phase 0 session scope.** Session state lives in an in-memory dict inside the
> single MCP stdio child process. Claude Desktop spawns a fresh child per
> conversation, so:
>
> - A new Claude Desktop conversation = a fresh process = an empty session dict.
> - `tutor_session_status(session_id=...)` against a session created in a prior
>   conversation will fail.
> - **Demo-script constraint (16 May):** do not close and re-open the stdio
>   transport mid-session.
>
> This limitation is generalised by ASSUM-003 and is fine for Phase 0. Phase 1
> Graphiti-backed sessions remove it.

**Mode:** direct (doc-only).

---

### TASK-CDR-003 — ADR-015 region verification + framing fix (F4)

**Files:**
- [`docs/architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md`](../../../docs/architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md) — line 62 ("UK-adjacent region")
- [`docs/architecture/assumptions.yaml`](../../../docs/architecture/assumptions.yaml) — ASSUM-007 (may need region update)

**Step 1 — Verify.** During FEAT-PO-004 setup (21–22 Apr), confirm whether AWS
Bedrock Custom Model Import in **eu-west-2 (London)** supports Gemma 4 31B.
Authoritative source: the AWS Bedrock console's "Custom model import" region
selector + the supported-model list for that region.

**Step 2 — Rewrite.** Based on the verification result:

- **If eu-west-2 supports it:** use eu-west-2. Update ADR-015 from
  "UK-adjacent region" to "eu-west-2 (London) — UK-region."
- **If eu-west-2 does not support it:** use us-east-1 or us-west-2. Update ADR-015
  to read something like:

  > Bedrock runs in us-east-1 (Virginia) for demo week, because eu-west-2 does not
  > yet support Bedrock Custom Model Import for Gemma 4 31B. This is a deliberate
  > residency trade-off for the hackathon: only prompts and responses pass
  > through, no student identity or session metadata beyond what the prompt
  > carries. Residency posture is a Phase 3 concern — post-hackathon migration to
  > a UK region (or a local-only inference path) when eu-west-2 catches up.

**Mode:** task-work (verification step + doc update).

---

## Wave 2 — Non-blocking

### TASK-CDR-004 — ADR-013 CompositeBackend seam (O1)

**File:** [`docs/architecture/decisions/ADR-ARCH-013-middleware-level-gamification-engine-future.md`](../../../docs/architecture/decisions/ADR-ARCH-013-middleware-level-gamification-engine-future.md)

**Edit** — one sentence in "Consequences":

> ADR-012's `CompositeBackend` route-scoped permissions already provide the
> middleware insertion point `GamificationMiddleware` would attach to. If Phase 2
> chooses middleware, the wiring seam is already there; if it chooses the
> standalone-module alternative, the cost is a small amount of additional wiring,
> not a re-architecture.

**Mode:** direct (doc-only).

---

### TASK-CDR-005 — ASSUM-007 Bedrock-out contingency (O2) — **user decision required**

**Files:**
- [`docs/architecture/assumptions.yaml`](../../../docs/architecture/assumptions.yaml) — ASSUM-007 revisit_trigger
- [`docs/research/ideas/phase-0-build-plan.md`](../../../docs/research/ideas/phase-0-build-plan.md) — FEAT-PO-004 section

**Decision needed (user):** if FEAT-PO-004 fails on 22 Apr and Bedrock is out,
which of the three DEC-07 GB10 workloads gets squeezed?

1. Study-tutor training-dataset expansion (additional subjects)
2. Study-tutor re-fine-tune
3. Architect-agent training + fine-tune for DDD Southwest (16 May)

Record the answer under ASSUM-007's `revisit_trigger` so the call is made before
22 Apr, not at 3am on 11 May.

**Mode:** task-work — user decision plus doc capture; task stays in backlog with
`blocked_by_decision: user` until the answer is recorded.

---

### TASK-CDR-006 — DEC-NN "do not seed reference prose to Graphiti" (O5)

**File:** [`docs/research/ideas/decisions-log-2026-04-17.md`](../../../docs/research/ideas/decisions-log-2026-04-17.md)

**Edit** — add a new decision entry with the next available DEC-NN:

> **DEC-NN — Reference prose stays on disk; Graphiti holds decisions only.**
>
> Do NOT seed `domain-model.md`, `system-context.md`, `container.md`, or
> `assumptions.yaml` as `full_doc` Graphiti episodes. The 16 ADRs already encode
> every decision. Domain-model is reference prose that loses fidelity in
> Graphiti's extraction step. Read reference docs from disk in `/system-design`
> and `/system-plan`.
>
> Graphiti remains the "decision record" (ADRs + session-derived entities); disk
> remains the "reference library." Revisit only if Graphiti's extraction fidelity
> improves materially.

**Mode:** direct (doc-only).

---

## Suggested Ordering

1. **Saturday afternoon:** TASK-CDR-001 (unblocks Phase 1 seeding confidence).
2. **Saturday afternoon:** TASK-CDR-002 (low-effort; bundled edit).
3. **Saturday evening or Monday 21 Apr:** TASK-CDR-003 verification step; edit
   can land after the 22 Apr verification if the region check needs more than a
   console glance.
4. **Any time before `/system-design`:** TASK-CDR-006 (30-second edit).
5. **Before 11 May:** TASK-CDR-005 (needs user decision).
6. **Before Phase 2 kickoff (12 May):** TASK-CDR-004.

`/system-design` can proceed as soon as TASK-CDR-001/002 are done and TASK-CDR-003
has at least the ADR-015 framing rewrite applied (even ahead of the 22 Apr
verification — the framing can be conditional prose that the verification later
narrows).
