# Cross-Repo RAG Impact Analysis

## For: Fleet-wide review of OpenWebUI RAG empirical findings
## Date: 24 April 2026
## Status: Analysis complete — actions identified per repo
## Predecessor: [openwebui-rag-empirical-findings-2026-04-23.md](./openwebui-rag-empirical-findings-2026-04-23.md)
## ADR: [ADR-FLEET-002-selective-retrieval-over-always-on-rag.md](../../../../guardkit/docs/architecture/decisions/ADR-FLEET-002-selective-retrieval-over-always-on-rag.md)

---

## Purpose

The 23 April empirical session revealed that always-on RAG against a partial corpus actively degrades a well-trained model below its no-retrieval baseline. This document examines whether that finding affects the four repos currently under active development — specialist-agent, study-tutor, forge, and jarvis — and identifies concrete actions for each.

---

## The generalised principle

The mechanism is not RAG-specific. It applies whenever an agent receives an instruction that conflates "use this context as evidence" (additive) with "only use this context" (ceiling). The suppression occurs silently: the model produces plausible output that omits knowledge it would otherwise contribute. This makes the failure mode harder to detect than outright hallucination — the output looks reasonable, it's just worse than it should be.

The study tutor made this visible because Shakespeare quotations are binary (correct or fabricated). Architectural reasoning, product analysis, and pipeline decisions are continuous — degradation is present but harder to measure without a deliberate before/after comparison.

---

## 1. Specialist-Agent — Architect Role

### Exposure: MODERATE-HIGH (different mechanism, same effect)

The architect role does not use always-on RAG injection in the OpenWebUI sense. Graphiti is wired as an opt-in tool (`graphiti_query`) that the Player calls when it decides to. This is architecturally sound — the Player controls when to retrieve.

However, **product documentation IS always injected** via `_build_initial_input()` in `session.py`, which unconditionally includes `## Product Documentation\n{doc_context}`. This is the equivalent of always-on RAG for the product-docs corpus.

The suppression manifests through three reinforcing instructions in `player.md`:

1. **Scope constraint rule**: "Only include components, actors, and integrations that are evidenced in the product documentation or explicitly requested."
2. **PHANTOM detection** (Coach, critical severity, -0.10 penalty): "Requirements or components invented without documentary evidence — not traceable to stated product goals."
3. **Web search gap-filling prohibition**: "If product documentation is silent on a topic, flag it as an Open Question rather than filling the gap with web search results."

These three rules together create a product-docs-as-ceiling effect. If the product docs don't mention authentication, observability, rate limiting, or disaster recovery, the model cannot include them in the C4 diagrams or ADRs without risking a PHANTOM detection. The model knows these are important — it has extensive training on architectural best practices — but is penalised for including them.

**Partial mitigation already present**: Rule 3 includes an escape valve — "flag it as an Open Question." A model that surfaces missing cross-cutting concerns as Open Questions rather than including them as components should not be penalised. But the Coach's PHANTOM detection doesn't currently distinguish between "invented a phantom component" and "raised a legitimate architectural concern not evidenced in docs." A Player that adds authentication to the container diagram will be penalised; one that asks "Should the architecture include an authentication service?" in Open Questions may not — but the Coach prompt doesn't explicitly protect Open Questions from PHANTOM scoring.

### Actions

1. **Audit `player.md` scope constraint language.** Soften from "Only include components... that are evidenced" to "Prioritise components evidenced in product documentation. For cross-cutting concerns (security, observability, operability, resilience) that product docs are silent on, include them as Open Questions rather than omitting them."

2. **Add a Coach detection override.** The Coach should not fire PHANTOM on Open Questions that raise legitimate cross-cutting concerns. Consider adding a `SUPPRESSED_CONCERN` detection pattern (informational, no penalty) that fires when the Player output lacks any mention of security, observability, or operability — indicating the product docs may have created a ceiling effect.

3. **Verify Graphiti `query_at_startup` behaviour.** The `role.yaml` sets `query_at_startup: true` but the session code doesn't appear to consume this flag for pre-injection. If this is wired elsewhere (or planned), ensure it follows the selective-retrieval pattern: check coverage before injecting.

---

## 2. Specialist-Agent — Product Owner Role

### Exposure: MODERATE

The product-owner role shares the same always-injected product docs pattern. `_build_product_owner_input()` includes `## Product Documentation\n{doc_context}` for all modes that accept docs. The Coach for product-owner has its own detection patterns (UNGROUNDED_FEATURE, MISSING_COVERAGE, SCOPE_CREEP) that create similar ceiling effects.

**Specific concern**: MISSING_COVERAGE fires when the Player output doesn't cover documents in the manifest. But the inverse — the model suppressing knowledge because the docs don't cover a topic — has no detection. A product roadmap that omits NFRs because the product docs don't mention them is a ceiling-driven omission, not a MISSING_COVERAGE gap.

### Actions

1. **Review Phase C (NFR extraction) prompt.** NFRs are inherently a cross-cutting concern that product docs may not explicitly address. The Phase C prompt should explicitly instruct the Player to draw on general knowledge of NFR categories (performance, security, scalability, availability) even when product docs are silent — product docs describe what the system does, not what it must withstand.

2. **No immediate code changes required.** The product-owner role is less exposed than the architect because product docs are the primary input by design — the PO role is extracting structure from docs, not generating novel architectural analysis. The ceiling effect matters less when the task is "organise what's in the docs" than when it's "identify what's missing from the docs."

---

## 3. Study Tutor

### Exposure: HIGH (empirically validated)

The study tutor is the origin of the finding. The persona-split interim deployment (§3e of the empirical findings) is the immediate fix, but several items need attention for the deep-agents harness build.

### The study-guide corpus question

Open question 2 from the empirical findings — "Is the study-guide corpus worth keeping at all?" — deserves a clear answer. Based on the evidence:

**The study-guide corpus should be replaced with an AO3-context corpus.** The reasoning:

- Study-guide material contributed "little beyond filler" in empirical testing (Finding 1).
- The fine-tune already knows how to structure AO1/AO2 analysis — that's what the behaviour training taught it.
- What the fine-tune is weakest on is AO3 (historical, social, cultural context), which requires factual knowledge about specific historical periods. This is the one category where retrieval would genuinely add value rather than suppress existing knowledge.
- An AO3 corpus (Jacobean society, Edwardian class structure, Victorian industrialisation, post-war disillusionment) is:
  - Almost entirely public domain (historical facts, not copyrighted analysis)
  - Small (a few hundred entries, each a paragraph of context)
  - Genuinely additive (fills a knowledge gap rather than duplicating existing capability)
  - Not subject to the quote-discipline suppression effect (AO3 is context analysis, not quotation)

### Remaining retrieval-gap risks

The Phase A quote verifier (FEAT-PO-006) must implement source-type labelling (R1 from the empirical findings). The risk without it: verifier matches a study-guide paraphrase against primary text with low edit distance and "corrects" a legitimate paraphrase into a misattributed quote (open question 3 from the empirical findings).

The dynamic retrieval decision (R2) should be implemented as a pre-turn check in the harness: "For this query, do I have primary-text evidence in the corpus?" Architecturally, this maps cleanly to a Player/Coach pattern — the Coach evaluates corpus coverage before the Player runs.

### Actions

1. **Replace study-guide corpus with AO3-context corpus.** Curate historical/social context entries for each set text. This is a content task, not an infrastructure task.
2. **Implement source-type labelling in FEAT-PO-006.** Every corpus entry needs a `source_type` field: `primary_text`, `secondary_analysis`, `historical_context`.
3. **Implement dynamic retrieval decision.** Pre-turn coverage check before injecting context. Below-threshold → answer from training, flag epistemic status.
4. **Update FEAT-PH1-004 + SR-09** to reference ADR-FLEET-002 as the governing architectural decision.

---

## 4. Forge

### Exposure: MODERATE (projected, not yet empirically validated)

Forge's confidence-gated checkpoints already embody the right principle (don't proceed if context coverage is low). The finding adds two nuances:

### Nuance 1: Distinguish pause from skip

The current checkpoint logic treats low context coverage as a pause signal. The empirical finding reveals a third state:

| Coverage level | Correct response |
|---|---|
| High coverage | Retrieve and proceed |
| Low coverage, retrieval adds value | Pause for enrichment or human input |
| Low coverage, retrieval actively misleads | **Skip retrieval**, proceed on model knowledge, flag epistemic status |

The third state is new. It applies when the retrieved context is not just incomplete but actively harmful — pulling the model toward the partial corpus's perspective and away from knowledge it would otherwise apply correctly. The study tutor's Shakespeare case is the clearest example, but the same pattern applies when Graphiti has partial ADR coverage: retrieving 3 out of 7 relevant ADRs is worse than retrieving none, because the model assumes the 3 retrieved ADRs are the complete set and doesn't consider the concerns the missing 4 would have raised.

### Nuance 2: Player-Coach shared corpus blind spot

This is the most structurally concerning finding for Forge. In the AutoBuild pipeline, the Player implements against retrieved Graphiti context, and the Coach validates against the same Graphiti context. If the context is partial:

- The Player omits a concern because Graphiti didn't surface it.
- The Coach doesn't flag the omission because Graphiti didn't surface it for the Coach either.
- Both are degraded by the same gap — the Coach cannot be the safety net for retrieval failures it shares.

This is analogous to having both pilot and co-pilot looking at the same faulty instrument. The redundancy is illusory.

**Mitigation**: The Coach needs an independent quality signal that is NOT derived from the same retrieval source. Options:

1. **Checklist-based cross-cutting concern detection.** The Coach maintains a hardcoded checklist of architectural concerns (error handling, logging, configuration, testing, security) and flags when the Player output is silent on any of them — regardless of whether Graphiti mentioned them.
2. **Asymmetric retrieval.** Player and Coach query different Graphiti scopes or with different query strategies, so they have partially non-overlapping coverage. This reduces the probability of a shared blind spot but doesn't eliminate it.
3. **Post-build smoke test as independent signal.** The TASK-SMK-F703A feature-level smoke gates are already in the backlog. These provide a retrieval-independent quality signal because they test actual runtime behaviour, not retrieved documentation.

### Actions

1. **Add a three-state coverage response** to checkpoint logic: high → proceed, low-additive → pause, low-misleading → skip retrieval.
2. **Evaluate Coach-side independent quality signal.** Option 1 (checklist-based detection) is cheapest and could land with TASK-AC-53445 (assertable-AC linter). Option 3 (smoke gates) is already planned via TASK-SMK-F703A.
3. **Document the shared-corpus blind spot** in the Forge design docs as a known limitation with the mitigation strategy.

---

## 5. Jarvis

### Exposure: LOW (v1 scope)

Jarvis at v1 is an intent router and dispatch layer. It classifies user intent and routes to specialist agents. It does not perform deep knowledge-grounded reasoning, so the RAG degradation pattern doesn't apply to its current design.

### Future risk (v1.5+)

If Jarvis adds RAG for skill/capability lookup (e.g., "which agent handles this?" against a capabilities index), the selective-retrieval pattern applies. A partial capabilities index would cause Jarvis to route to known agents and miss unknown-but-relevant ones.

### Actions

1. **No v1 actions required.**
2. **Add a one-line design note** in the Jarvis Phase 3/4 docs: "If RAG is added to dispatch logic, ADR-FLEET-002 (selective retrieval) applies. Evaluate corpus coverage before dispatch decisions."

---

## Cross-cutting action: Seed ADR-FLEET-002 to Graphiti

The ADR has been written to `guardkit/docs/architecture/decisions/ADR-FLEET-002-selective-retrieval-over-always-on-rag.md`. It should be seeded to Graphiti under the `appmilla-fleet` group ID so all agents in the fleet can retrieve it as context when making retrieval-related decisions.

---

## Summary table

| Repo | Exposure | Key risk | Immediate action |
|---|---|---|---|
| specialist-agent (architect) | Moderate-High | Product-docs-as-ceiling + PHANTOM detection suppresses legitimate architectural concerns | Soften scope-constraint language; add SUPPRESSED_CONCERN detection |
| specialist-agent (PO) | Moderate | NFR extraction limited by product-doc coverage | Review Phase C prompt for cross-cutting NFR categories |
| study-tutor | High (validated) | RAG degrades fine-tune quality for known texts | Replace study-guide corpus with AO3-context corpus; implement source-type labelling |
| forge | Moderate | Player-Coach shared-corpus blind spot; three-state coverage response needed | Add skip-retrieval state; evaluate independent Coach quality signal |
| jarvis | Low | None at v1; future RAG for dispatch would apply | Design note only |

---

## References

- [openwebui-rag-empirical-findings-2026-04-23.md](./openwebui-rag-empirical-findings-2026-04-23.md) — primary empirical evidence
- [rag-grounding-design.md](./rag-grounding-design.md) — Phase A MVP design
- [ADR-FLEET-002](../../../../guardkit/docs/architecture/decisions/ADR-FLEET-002-selective-retrieval-over-always-on-rag.md) — fleet-level architectural decision
- [structured-uncertainty-handling.md](../../../../guardkit/docs/research/structured-uncertainty-handling.md) §3.4 — Graphiti-Gated Execution
- `specialist-agent/roles/architect/prompts/player.md` — architect Player prompt (reviewed 24 April 2026)
- `specialist-agent/roles/architect/prompts/coach.md` — architect Coach prompt (reviewed 24 April 2026)
- `specialist-agent/src/specialist_agent/orchestrator/session.py` — context injection code (reviewed 24 April 2026)
