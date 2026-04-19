Architecture Review — Study Tutor /system-arch Output
Overall: this is genuinely good, and you can proceed to /system-design with confidence. The ADRs are proportionate, consistent with the scope/decisions log, and the timeline-driven tradeoffs are explicit rather than pretending to be principled. Below I've flagged what's strong, what has structural issues worth fixing before /system-design, and what's minor enough to note but not block on.
What's working well
The three-layer architecture (ADR-002) and six bounded contexts (ADR-001) hang together cleanly, and the anti-corruption layer framing of the Inference Runtime (LLMClient) is exactly the right seam — it makes the Ollama↔Bedrock switch (ADR-006) a factory detail rather than a refactor. The dual inference path solves DEC-07's GB10 scheduling conflict without forcing you to pick a winner.
The async Graphiti write-back at session-end boundary (ADR-003) is the single most important latency decision in the document, and it's correctly rationalised against CC-08 and the LES1 §4 POLR evidence. The fact that ADR-012 then leverages deepagents 0.5.3 AsyncSubAgent natively (rather than hand-rolling) closes the loop — you're using the SDK's fire-and-forget primitives for exactly the pattern LES1 taught you to be paranoid about.
LES1 elevated to CC-01 through CC-08 (ADR-009) is the right call. It turns tribal knowledge into structural requirements with test hooks.
ADR-016 (deadline as constraint) is unusual and I like it — explicitly naming the timeline as load-bearing prevents an "ideal architecture" drift later. The slip-absorption ordering (Reachy → Phase 2 engine → ... but never CC-01–CC-10) is a real forcing function.
Structural issues worth addressing before /system-design
1. Embedding dimension inconsistency — FalkorDB will reject writes
This is the only hard bug I found. graphiti.yaml in ADR-007 declares embedding_dimensions: 1024, but nomic-embed-text-v1.5 is a 768-dimension model (as reflected in your memory for the existing agentic-dataset-factory ChromaDB wiring). If FalkorDB's index is provisioned at 1024 and the embedder returns 768, Phase 1 seeding will fail.
Two options: (a) fix the config to embedding_dimensions: 768, or (b) intentionally run nomic at a different dimension if you're using Matryoshka truncation — but the latter isn't mentioned anywhere so I assume (a).
Action: correct in ADR-007 and in the actual .guardkit/graphiti.yaml before Phase 1 seeding begins.
2. Phase 0 tool classification conflicts with the scope doc
The scope (SR-07 provisional table) classifies tutor_start_session as long-running because it "includes Graphiti read of student model." But the architecture also says Phase 0 has no Graphiti (ADR-001 bounded contexts table, ADR-005, ADR-011 implicitly). So in Phase 0, tutor_start_session is really just a UUID mint + in-memory dict insert — easily sub-second and perfectly sync.
The domain-model container doc and ADR-008 already reflect this ("returns session_id ≤ 1s"), but the framing "long-running" is still used. There's no actual contradiction in behaviour (returning session_id ≤1s satisfies either framing), but the reason is different:

Scope says: long-running because future Graphiti read
Architecture (correctly) says: long-running as a forward-compatible SR-07 classification so Phase 1 doesn't need to reclassify the MCP contract when Graphiti lands

Worth making this explicit in ADR-008's rationale so /feature-spec FEAT-PO-002 doesn't get confused between "it is long-running" and "it is architected as long-running for phase stability."
3. In-memory session state and CC-02 interact badly
ADR-008 + domain-model §7 describe MCP stdio as the transport boundary. The Phase 0 session state lives in an in-memory dict inside a single MCP server process (scope FEAT-PO-002 item 3, and container.md Container(session, ..., "Python / in-memory dict")).
That's fine operationally, but Claude Desktop launches a fresh stdio child per conversation. If the user starts a session in one Claude Desktop conversation, then opens a new conversation, the second conversation gets a new process with a new (empty) session dict. tutor_session_status(session_id=...) against the second process will fail.
This is probably acceptable for Phase 0 (ASSUM-003 already says "sessions surviving MCP server restarts is not a Phase 0 requirement") but the scope of the limitation should be captured in ADR-008 or ADR-014 as an explicit behavioural note, so the demo script doesn't trip over it on 16 May. Specifically: a Phase 0 demo must not close-and-reopen the stdio connection mid-session.
4. ADR-015 has a minor accuracy issue about AWS region
ADR-015 says Bedrock "runs in a UK-adjacent region" but ADR-006 + the build plan prerequisites both say "likely us-east-1 or us-west-2 for earliest Gemma 4 import support." us-east-1 is Virginia and us-west-2 is Oregon — neither is UK-adjacent in a data-residency sense that a GDPR-aware reader would accept. The eu-west-2 (London) region may not yet support Bedrock Custom Model Import for Gemma 4 at 31B (worth confirming with a search during Phase 0 prerequisites).
If eu-west-2 supports it, use it and the claim holds. If only us-east-1/us-west-2 support it, the ADR needs to be honest: "Bedrock runs in us-east-1 during demo week; residency posture is a Phase-3 concern" — which is fine for a hackathon but shouldn't hide behind "UK-adjacent" framing.
5. Shared Kernel A taxonomy vs domain-model §8.1 enum values
Minor but catchable now. In domain-model.md §8.1:
pythonclass Subject(StrEnum):
    ENGLISH_LANGUAGE = "English Language"
    ENGLISH_LITERATURE = "English Literature"
Human-readable string values inside StrEnum are fine for display but awful for Graphiti group IDs (subject:gcse-english in ADR-014) and for JSON stability. When you land the Pydantic models in Phase 1, you'll want either slug-style values ("english-language") or a separate .slug property. The current shape will force a join/map step every time a subject crosses the MCP boundary.
Worth resolving during /system-design — it's a contract-shape decision, not architecture — but flagging now since it's in the architecture's shared kernel.
Smaller observations
ADR-013 (middleware gamification) is marked Proposed which is correct — this is a Phase 2 call. One thing it should explicitly note: the CompositeBackend route-based permissions (ADR-012) already give you a middleware-shaped insertion point. If you go the middleware route in P2, the integration seam is already there; if you go standalone, you pay a small wiring cost. This is implicit in the ADR but worth making explicit so FEAT-PO-007 inherits the awareness.
ASSUM-007 (Bedrock supports Gemma 4 31B natively) is currently medium confidence and sits on the Phase 0 critical path. The FEAT-PO-004 validation test on Tuesday 22 April is the right gate, but the ADR-006 fallback posture ("Ollama-primary posture stays and demo-week scheduling becomes tighter") doesn't actually solve the demo-week problem if it fails — GB10 is still needed for the architect-agent training run per DEC-07 workload 3. You may want a written contingency: if Bedrock is out, which training workload gets squeezed? The decision is easier to make now than at 3am on 11 May.
ADR-003 says "per-turn async fire-and-forget (per turn) — Considered for streaming-style write-back. Deferred." This is correct for Phase 1, but the Coach is already going to be accumulating per-turn observations in session memory (domain-model §2.2 TurnFeedback). If a session ends abnormally (MCP process killed, Claude Desktop restart), all accumulated Coach feedback is lost. ADR-003 acknowledges this ("If the tutor crashes between session-end and Graphiti flush, the session-level state is lost") but frames it as a single event. In practice it's potentially every turn of an active session. Worth revisiting if you see real MCP disconnects during Phase 1 testing.
Node counts in system-context.md and container.md are flagged as "well under the 30-node threshold." For a hackathon submission where the three-layer architecture is the core narrative, I'd actually encourage using more of the budget — the current container diagram is dense enough that a judge unfamiliar with your stack needs to zoom in. Not an architecture bug, a presentation nit for the demo.
On the optional Graphiti seeding question in your handoff: I agree — don't seed domain-model.md, system-context.md, container.md, or assumptions.yaml as full_doc. The 16 ADRs already encode every decision, and domain-model.md is reference prose that loses fidelity in Graphiti's extraction step (per your existing memory on "nagging doubts / content fidelity failures"). Disk-read them from /system-design and /system-plan. Keeps Graphiti the "decision record," disk the "reference library."
Recommendation
Go ahead with /system-design once you've:

Fixed the embedding dimension in ADR-007 + graphiti.yaml (1024 → 768).
Clarified ADR-008's long-running rationale for tutor_start_session (forward compatibility, not current Graphiti read).
Added a one-line behavioural note in ADR-008 or ADR-014 about stdio child-process session scope.
Corrected ADR-015's AWS region framing to match reality (pending a quick check of eu-west-2 Bedrock Custom Model Import availability for Gemma 4 31B).

The Subject enum slug decision (item 5) can wait for /system-design — that's where contract shapes get nailed down. Everything else is either proposed (ADR-013), already phase-gated correctly, or a presentation nit.
Per the Phase 0 build plan, Sunday-morning /system-design after these edits looks right. Nothing here justifies slipping the timeline.