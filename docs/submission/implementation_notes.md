Short answer
Both RAG and Graphiti memory work — but they have different verification strengths, and you should describe them with slightly different confidence levels. Graphiti has a documented live end-to-end demo; RAG has live wiring smokes but its full two-path validation is still unticked.

Graphiti memory — ✅ live-verified, claim it confidently
This is the stronger of the two. There is a real, documented live demo on 2026-05-07 (TASK-GR-DEMO, recorded in phase-1-validation.md):

4 full tutoring sessions ran end-to-end through Claude Desktop → MCP → FalkorDB.
The persistent student model (year_group=10, target_grade=7, subjects, 6 topic confidences) was read at tutor_start_session and written at tutor_session_end.
Topic confidence for "Lady Macbeth's ambition" demonstrably moved 55% → 56% → 57% → 58% across the four sessions — that's the round-trip proving itself.
Validation gates G3/G4/G5/G6/G13 flipped from "Falsified" to "Held" with cited evidence.
Two honest caveats to keep in your pocket (don't overclaim):

The session_completed episode write is verified by a direct GRAPH.QUERY against FalkorDB, not via the Graphiti MCP get_episodes tool — that tool has an upstream bug (queries the wrong graph). Your write path is fine; the read-back convenience tool isn't. Non-blocking.
The Phase 1 seed writes intra-group edges only (confidences, topic coverage); cross-group relationship edges were deliberately deferred (denormalised instead). So say "persistent student model with topic-confidence tracking", not "full multi-entity knowledge graph".
Suggested wording: "A Graphiti knowledge-graph student model persists the learner's profile and per-topic confidence in FalkorDB. Each session reads prior state at start and writes outcomes at end — verified live across four sessions, with topic confidence measurably progressing session-over-session."


Short answer: partially — it drives topic selection, but not generation
There is a real adaptive loop, but it operates at the planning layer, not at the layer where the fine-tuned model actually writes the tutoring content.

✅ What Graphiti memory genuinely influences
At tutor_start_session, the deterministic planner (pipeline.py:375) reads get_student_state from Graphiti and uses the stored per-topic confidence scores to:

Pick the session's focus topic — pick_lowest_confidence_topic, the learner's weakest topic outside a 48-hour cooldown (rules.py:114).
Set focus_aos, and compute related_misconceptions, an opening_prompt, and a rationale.
That focus topic flows all the way through into the turn via SessionState.topic. And at session-end, outcomes write back and shift confidence — which is exactly your observed 55→56→57→58% progression. So which topic a session is about genuinely adapts to the learner's history. That loop is real.

The full plan (topic, opening prompt, misconceptions) is also returned to the MCP caller in the tutor_start_session response as plan_summary (adapter.py:105).

⚠️ What it does not do — the nuance that matters
The fine-tuned Gemma Player model does not receive any of this in its prompt. Look at the Player adapter (llm_player_adapter.py:147-164) — the docstring is explicit:

"session_state is accepted for Protocol parity but its fields are not yet woven into the prompt — Phase-1 wiring keeps the prompt scope narrow (player system prompt + raw learner message)."

The code does _ = session_state.session_id (a no-op touch) and then client.generate(learner_message, self._player_prompt) — a static system prompt plus the raw message. Topic, focus AOs, confidence, and misconceptions never reach the model. And SessionState itself only carries session_id / student_id / text_name / topic / focus_aos / mode — it doesn't even transport misconceptions or confidence (session_state.py:39-44).

So: the tutor's explanations are not conditioned on Lilymay's stored misconceptions or weak areas. The graph chooses the subject; it doesn't shape the words.

If your sessions felt strongly personalised, that's most likely because Claude Desktop's side received the plan_summary from tutor_start_session and steered with it — not because the Gemma fine-tune was conditioned on memory.

What to say in the submission
Accurate:

"A Graphiti knowledge graph persists per-topic confidence for the learner. A deterministic planner reads it to select each session's focus — the weakest topic outside a cooldown window — and session outcomes write back, so topic selection adapts measurably across sessions."

Don't claim: that the tutor tailors its teaching to the student's specific misconceptions — that signal is computed but never reaches the model.

This is a more impactful gap than the citation anchors, and it's a contained fix: add misconceptions / confidence to SessionState, populate them in adapter.py, and weave topic + focus_aos + misconceptions into the Player prompt. That turns "memory selects the topic" into "memory shapes the lesson" — a genuinely stronger hackathon story.

Want me to scope that change and tell you if it's safely doable today? I'd recommend prioritising it over the anchors.


The corpus does contain all three texts
data/chroma/ holds 581 embedded chunks, and the primary-text sidecar registers all three:

Text	Chunks	Type
macbeth	253	play
an_inspector_calls	274	play
power_and_conflict_poems	54	poetry anthology
So selective RAG retrieval will fire for all three — a session on any of them gets reason=retrieve:primary_present, not the analysis-mode skip I incorrectly described. That materially upgrades what you can claim: the fine-tune-plus-RAG selective-retrieval story is genuinely active across your whole demo set, not just Macbeth.

⚠️ But — one real gap I need to flag: citation anchors
I checked every chunk's chunk_json. All 581 chunks have citation_anchor: null — zero structured anchors across all three texts.

What this means concretely:

Retrieval works — the right passages come back and ground the Player's answer. ✅
Quote verification works — the verifier can still confirm a quote is authentic primary text (verbatim match) and strip/correct fabricated ones. ✅
What's missing: verified quotes are not getting a structured Act/Scene/Line (or poem/line) citation attached. The "annotated citation anchor" enrichment is producing nothing on this corpus.
Why:

Power & Conflict poems (54 chunks) — expected. There's no PoetryCitationAnchor in the schema yet (that's TASK-PRV-009, still in backlog). Poems were always going to land anchor-less.
Macbeth + An Inspector Calls (both plays) — should have PlayCitationAnchors but don't. The likely cause: the anchor inferrer was built for the Standard Ebooks .txt layout, and docling's .md output flattens the Act/Scene structure — e.g. Macbeth's chunk 0 is a run-on "Contents ACT I .......3SCENE I. A desert place..." blob. The inferrer can't see clean Act/Scene headings to anchor against.
This is exactly the gap TASK-RAG-003 (the unticked two-path live smoke) was designed to catch — its AC literally says "expect ≥90% anchor coverage for plays post-PRV-008." You're currently at 0%.

What to say in the submission
Safe and accurate:

"Selective RAG over a licensed corpus of three GCSE set texts — Macbeth, An Inspector Calls, and the AQA Power & Conflict anthology (581 embedded chunks). A per-turn decision retrieves primary-text passages to ground the tutor's answer, and a post-hoc verifier checks every quotation against the source text, correcting or stripping anything not verbatim."

Avoid claiming: that quotes are annotated with precise Act/Scene/Line citations — that specific enrichment isn't firing on the docling corpus right now.

Two things I can do, given today's deadline:

Investigate the anchor inference — confirm whether it's the docling .md heading-format mismatch, and whether it's a quick fix (re-running ingest after a small inferrer tweak) or genuinely a same-day risk. This would let you make the stronger "structured citations" claim.
Draft the submission writeup (still all stubs in technical-writeup.md).
Want me to start with the anchor investigation? It's the one thing standing between "RAG retrieves and verifies" and "RAG retrieves, verifies, and cites" — and the latter is a much stronger hackathon line.

thanks so is the information in the Graphiti memory actually used to influenece the content of a study tutor session at all?
Good question — reading the state is one thing; actually using it to shape the session is another. Let me trace the code path from get_student_state through to what the Player and Coach actually see.

Bash Find where student state is consumed
IN
echo "=== get_student_state / get_topic_recommendations callers ===" && grep -rn "get_student_state\|get_topic_recommendations\|StudentState\|student_state" src/ --include=*.py | grep -v "def get_student_state\|def get_topic" && echo && echo "=== planner pipeline inputs ===" && grep -rn "student\|StudentState\|recommend\|confidence\|misconception" src/study_tutor/planner/*.py | head -40

OUT
=== get_student_state / get_topic_recommendations callers ===
src/study_tutor/knowledge/queries.py:20:- **Read-path timeout** (ASSUM-005): :func:`get_student_state` returns
src/study_tutor/knowledge/queries.py:21:  ``None`` and logs ``event=student_state_read_timeout`` if the underlying
src/study_tutor/knowledge/queries.py:115:class StudentState(BaseModel):
src/study_tutor/knowledge/queries.py:116:    """Aggregated student-model snapshot returned by :func:`get_student_state`.
src/study_tutor/knowledge/queries.py:315:def _build_student_state(
src/study_tutor/knowledge/queries.py:320:) -> StudentState:
src/study_tutor/knowledge/queries.py:321:    """Project raw nodes/facts into a :class:`StudentState`.
src/study_tutor/knowledge/queries.py:329:    state = StudentState(student_id=student_id)
src/study_tutor/knowledge/queries.py:444:) -> StudentState | None:
src/study_tutor/knowledge/queries.py:445:    """Return the full :class:`StudentState` for a student.
src/study_tutor/knowledge/queries.py:453:            ``StudentState.stale=True`` (per ASSUM-006). Default 180.
src/study_tutor/knowledge/queries.py:456:        - :class:`StudentState` populated from the graph on success.
src/study_tutor/knowledge/queries.py:457:        - ``StudentState(empty=True)`` when ``client`` is ``None`` or the
src/study_tutor/knowledge/queries.py:461:          ``event=student_state_read_timeout`` is emitted in that path.
src/study_tutor/knowledge/queries.py:464:        return StudentState(empty=True)
src/study_tutor/knowledge/queries.py:468:        return StudentState(empty=True)
src/study_tutor/knowledge/queries.py:482:                "event": "student_state_read_timeout",
src/study_tutor/knowledge/queries.py:489:    return _build_student_state(student_id, nodes, facts, stale_threshold_days)
src/study_tutor/knowledge/queries.py:517:    state = await get_student_state(client, student_id)
src/study_tutor/knowledge/queries.py:979:    "StudentState",
src/study_tutor/knowledge/queries.py:982:    "get_student_state",
src/study_tutor/knowledge/queries.py:983:    "get_topic_recommendations",
src/study_tutor/planner/pipeline.py:45:from study_tutor.knowledge.queries import get_student_state
src/study_tutor/planner/pipeline.py:347:    :func:`get_student_state` to fetch the learner's per-topic
src/study_tutor/planner/pipeline.py:375:            get_student_state(client, student_id),
src/study_tutor/planner/pipeline.py:444:            client. Forwarded to :func:`get_student_state`. ``None`` is

=== planner pipeline inputs ===
src/study_tutor/planner/types.py:12:  student-model read fails (``learner_state_available=False``) or the
src/study_tutor/planner/types.py:13:  learner has been seeded but has no topic-confidence entries
src/study_tutor/planner/types.py:119:    related_misconceptions: list[str] = Field(
src/study_tutor/planner/types.py:235:    - ``learner_state_available=False`` — the student-model read failed
src/study_tutor/planner/types.py:237:      empty misconceptions, default duration, and the no-state opening
src/study_tutor/planner/types.py:242:      they have no usable topic-confidence entries yet. Draws topic +
src/study_tutor/planner/types.py:257:            related_misconceptions=[],
src/study_tutor/planner/types.py:275:        related_misconceptions=[],
src/study_tutor/planner/types.py:277:            "Baseline plan: learner has no topic-confidence entries yet — "
src/study_tutor/planner/protocols.py:38:from study_tutor.knowledge.student_model import (
src/study_tutor/planner/protocols.py:97:        confidence_percentage: The learner's current confidence on the
src/study_tutor/planner/protocols.py:99:            no confidence record exists.
src/study_tutor/planner/protocols.py:100:        related_misconceptions: Misconception summaries the tutor should
src/study_tutor/planner/protocols.py:109:    confidence_percentage: float | None
src/study_tutor/planner/protocols.py:110:    related_misconceptions: list[str]
src/study_tutor/planner/protocols.py:130:        student_id: Identifier of the learner this plan is for.
src/study_tutor/planner/protocols.py:131:        topic_confidences: Per-topic confidence records read from the
src/study_tutor/planner/protocols.py:132:            student-model service (FEAT-PH1-001).
src/study_tutor/planner/protocols.py:133:        misconceptions: Documented misconceptions for the learner.
src/study_tutor/planner/protocols.py:143:    student_id: str
src/study_tutor/planner/protocols.py:144:    topic_confidences: list[TopicConfidence]
src/study_tutor/planner/protocols.py:145:    misconceptions: list[Misconception]
src/study_tutor/planner/protocols.py:161:        student_id: str,
src/study_tutor/planner/protocols.py:162:        topic_confidences: list[TopicConfidence],
src/study_tutor/planner/protocols.py:163:        misconceptions: list[Misconception],
src/study_tutor/planner/protocols.py:197:            student_id=student_id,
src/study_tutor/planner/protocols.py:198:            topic_confidences=topic_confidences,
src/study_tutor/planner/protocols.py:199:            misconceptions=misconceptions,
src/study_tutor/planner/protocols.py:220:            empty), preserving the order of :attr:`topic_confidences`.
src/study_tutor/planner/protocols.py:231:        return [tc for tc in self.topic_confidences if tc.band == band]
src/study_tutor/planner/rules.py:12:- **Rule 4 (TASK-DSP-004)** — unrevisited-misconception preference per
src/study_tutor/planner/rules.py:37:- **Rule 4 reads misconception ``text`` as opaque data
src/study_tutor/planner/rules.py:39:  participate in ranking; an adversarial misconception body cannot
src/study_tutor/planner/rules.py:53:from study_tutor.knowledge.student_model import Misconception, TopicConfidence
src/study_tutor/planner/rules.py:102:            confidence_percentage=None,
src/study_tutor/planner/rules.py:103:            related_misconceptions=[],
src/study_tutor/planner/rules.py:114:    """Pick the lowest-confidence topic that is outside the 48h cooldown.
src/study_tutor/planner/rules.py:128:    learner has no topic-confidence entries at all).
src/study_tutor/planner/rules.py:145:            confidence_percentage=float(winner.percentage),
src/study_tutor/planner/rules.py:146:            related_misconceptions=[],
Bash Trace plan flow in MCP adapter and session
IN
echo "=== mcp adapter (start_session / turn) ===" && grep -n "plan\|Plan\|student\|topic\|confidence\|misconception\|prompt\|build_pipeline\|orchestrat" src/study_tutor/mcp/adapter.py | head -60 && echo && echo "--- session/tutor_session.py ---" && grep -n "plan\|Plan\|student\|topic\|misconception\|prompt\|opening" src/study_tutor/session/tutor_session.py | head -50

OUT
=== mcp adapter (start_session / turn) ===
6:  ``session_id`` *before* the deterministic planner is invoked so a
7:  planner failure or timeout never blocks session creation. The plan is
8:  produced by :func:`study_tutor.planner.pipeline.plan_session` wrapped in
11:  learner — degrades to :func:`_baseline_plan(False)` rather than
13:  planner pipeline.
30:Concurrency note (TASK-DSP-006): the per-instance ``_plan_sessions`` dict
32:effectively zero, and :class:`SessionPlan` is ``frozen=True``, so no
35:other's plan.
49:    record_topic_confidence_update,
52:from study_tutor.planner.pipeline import plan_session
53:from study_tutor.planner.types import SessionPlan, _baseline_plan
61:from study_tutor.tutoring.orchestrator import PlayerCoachOrchestrator
81:def _planner_handler_budget_sec() -> float:
82:    """Return the outer ``plan_session`` budget for ``tutor_start_session``.
105:def _plan_summary(plan: SessionPlan) -> dict[str, Any]:
106:    """Project a :class:`SessionPlan` into the MCP-response summary shape.
109:    the first session turn — ``topic_name`` and ``rule_selected`` are
111:    coach side can audit the plan without a second round-trip.
114:        "topic_name": plan.topic_name,
115:        "rule_selected": plan.rule_selected,
116:        "fallback_used": plan.fallback_used,
117:        "focus_aos": list(plan.focus_aos),
118:        "opening_prompt": plan.opening_prompt,
119:        "suggested_duration_minutes": plan.suggested_duration_minutes,
120:        "rationale": plan.rationale,
121:        "related_misconceptions": list(plan.related_misconceptions),
122:        "ao_mapping_found": plan.ao_mapping_found,
123:        "learner_state_available": plan.learner_state_available,
134:        orchestrator_factory: Any = None,
141:        self._player_prompt = role_config.load_player_prompt()
144:        # Per-instance plan store (TASK-DSP-006). Keyed by session_id;
145:        # holds the immutable :class:`SessionPlan` produced by
146:        # :func:`plan_session` for subsequent ``tutor_turn`` consumption.
147:        self._plan_sessions: dict[str, SessionPlan] = {}
148:        # TASK-DTL-003: optional per-turn orchestrator factory. When
154:        self._orchestrator_factory = orchestrator_factory
170:        # When an orchestrator factory is wired (Phase-1 production path
181:        # The Phase-0 backward-compatible path (``orchestrator_factory
186:        if self._orchestrator_factory is not None:
187:            self._orchestrator_factory()  # noqa: F841 — discarded; smoke-check invocation only
194:            # shows the state. Gated on ``orchestrator_factory is not
196:            # build orchestrators (and therefore doesn't run RAG).
215:        student_id: str,
216:        topic_override: str | None = None,
219:        """Create a session and plan it via the deterministic planner.
222:        the planner pipeline. ``session_id`` is minted *before* the
223:        planner is invoked (AC-002) so a planner failure or timeout
226:        :func:`_baseline_plan(False) <study_tutor.planner.types._baseline_plan>`
232:        always fires before the inner 5.0s student-model read timeout
238:            student_id: Stable learner slug, e.g. ``"lilymay"``.
239:            topic_override: Optional learner-supplied topic. When set,
241:                :func:`plan_session`.
247:            ``{"session_id": <uuid4>, "plan_summary": {...}}`` — see
248:            :func:`_plan_summary` for the summary shape.
250:        # Mint session_id *before* the planner is invoked (AC-002). The
255:            subject=student_id, topic=topic_override
260:        # pay cold-start latency. Independent of the planner so a planner
269:        budget = _planner_handler_budget_sec()
271:            plan = await asyncio.wait_for(
272:                plan_session(student_id, topic_override),

--- session/tutor_session.py ---
28:    topic: str | None
42:    def create(self, subject: str, topic: str | None = None) -> TutorSession:
46:            topic=topic,
Bash Read tutor_turn handler
IN
sed -n '280,420p' src/study_tutor/mcp/adapter.py

OUT
                extra={
                    "event": "planner_handler_budget_exceeded",
                    "student_id": student_id,
                    "session_id": session_id,
                    "budget_sec": budget,
                },
            )
            plan = _baseline_plan(learner_state_available=False)
        except Exception as exc:  # noqa: BLE001 — boundary catch
            # Any non-timeout failure mode: log with traceback (so
            # observability captures the root cause) and degrade. Never
            # re-raise — the MCP contract is "always return a plan".
            logger.exception(
                "planner internal error — degrading to baseline plan",
                extra={
                    "event": "planner_internal_error",
                    "student_id": student_id,
                    "session_id": session_id,
                    "error": str(exc),
                },
            )
            plan = _baseline_plan(learner_state_available=False)

        self._plan_sessions[session_id] = plan
        return {
            "session_id": session_id,
            "plan_summary": _plan_summary(plan),
        }

    async def tutor_turn(
        self,
        session_id: str,
        user_message: str,
        player_model: str | None = None,
    ) -> dict[str, Any]:
        """Generate one tutor reply for ``user_message`` within the session."""
        try:
            session = self._store.get(session_id)
        except SessionNotFoundError:
            return _session_not_found(session_id)

        if session.status == "ended":
            return {
                "error": f"Session '{session_id}' has ended.",
                "error_type": "SessionEnded",
            }

        self._store.append_turn(session_id, "user", user_message)

        # TASK-DTL-003: route through PlayerCoachOrchestrator when a
        # factory is wired (production Phase 1 path). Per-turn
        # construction guarantees concurrency isolation — two concurrent
        # ``tutor_turn`` calls get two independent orchestrator
        # instances and cannot contaminate each other's Coach
        # observations.
        if self._orchestrator_factory is not None:
            # TASK-LCA-003: build the typed SessionState boundary object
            # from the cached SessionPlan + TutorSession. This is the
            # producer for the §4 SessionState integration contract
            # consumed by TASK-LCA-001 (Player adapter) and TASK-LCA-002
            # (Coach adapter). Optional fields default to ``None`` /
            # ``()`` so a baseline-degraded plan (no ``text_name`` /
            # missing ``focus_aos``) still yields a valid construction
            # (ASSUM-LCA-007).
            plan = self._plan_sessions.get(session_id)
            text_name_value = (
                getattr(plan, "text_name", None) if plan is not None else None
            )
            session_state = SessionState(
                session_id=session_id,
                student_id=session.subject,
                text_name=text_name_value if text_name_value else None,
                topic=plan.topic_name if plan is not None else None,
                focus_aos=tuple(plan.focus_aos) if plan is not None else (),
                mode="tutor",
            )
            orchestrator: PlayerCoachOrchestrator = self._orchestrator_factory()
            turn_result = await orchestrator.run_turn(
                session_state=session_state,
                learner_message=user_message,
            )
            self._store.append_turn(session_id, "tutor", turn_result.response)
            return {
                "tutor_response": turn_result.response,
                "decision": turn_result.decision,
                "attempts": turn_result.attempts,
                "flagged_for_review": turn_result.flagged_for_review,
                "duration_seconds": turn_result.duration_seconds,
            }

        provider = player_model or _default_player_model()
        client = LLMClient(provider=provider)

        # Generate in a worker thread so async MCP framework isn't blocked
        # by the synchronous httpx call inside LLMClient.generate().
        response = await asyncio.to_thread(
            client.generate, user_message, self._player_prompt
        )

        self._store.append_turn(session_id, "tutor", response)
        return {"tutor_response": response}

    async def tutor_session_status(self, session_id: str) -> dict[str, Any]:
        """Return current session state."""
        try:
            session = self._store.get(session_id)
        except SessionNotFoundError:
            return _session_not_found(session_id)

        return {
            "session_id": session.session_id,
            "status": session.status,
            "turn_count": len(session.turns),
            "started_at": session.started_at.isoformat(),
        }

    async def tutor_session_end(self, session_id: str) -> dict[str, Any]:
        """Mark the session ended (TASK-GR-WIRE BLOCK-3a).

        Delegates to
        :func:`study_tutor.tutoring.session_end.perform_session_end` which
        owns the full FEAT-PH1-003 session-end workflow:

        * F4 in-flight ``tutor_turn`` resolution (3 s inner timeout).
        * I-T6 zero-turn invariant guard — sessions ended before any tutor
          turn flip status to ``"ended"`` but do NOT emit
          ``session.completed`` and do NOT schedule the F3 Graphiti write.
        * DDR-003 ordering: bus emit precedes the F3 ``create_task`` call.
        * F3 fire-and-forget Graphiti write via the injected
          :class:`GraphitiWriteHelper` (graceful no-op if ``None``).
        * Caller-facing return within the ASSUM-004 2 s wall-clock budget
          regardless of Graphiti latency (ADR-ARCH-019).

        ``topics_covered`` and ``aos_exercised`` are sourced from the
        cached :class:`SessionPlan` for ``session_id``. If no plan is
        cached (e.g. a session_id from a prior process restart), both
        default to empty — :func:`build_session_completed_episode` will
        fall back to ``[session.topic]`` if available, otherwise the
        learner subject slug.
        """
        try:
Let me confirm exactly what the Player adapter receives — whether misconceptions/confidence reach it.

Bash Inspect SessionState and Player adapter
IN
echo "=== SessionState fields ===" && grep -n "class SessionState\|:\s*str\|:\s*tuple\|:\s*int\|: str\| = \|misconception\|confidence\|topic\|focus" src/study_tutor/tutoring/adapters/session_state.py | head -40 && echo && echo "=== Player adapter: what it reads from session_state ===" && grep -n "session_state\.\|misconception\|confidence\|topic\|focus_aos\|prompt" src/study_tutor/tutoring/adapters/llm_player_adapter.py | head -40

OUT
=== SessionState fields ===
20:``focus_aos``).
31:class SessionState:
39:    session_id: str
40:    student_id: str
41:    text_name: str | None = None
42:    topic: str | None = None
43:    focus_aos: tuple[str, ...] = field(default_factory=tuple)
44:    mode: str = "tutor"

=== Player adapter: what it reads from session_state ===
10:  system prompt loaded once at construction.
14:Load-bearing safety invariant (ASSUM-008 / ASSUM-LCA-006): the prompt
15:assembled by :meth:`_assemble_revise_prompt` carries **only** structured
19:use, but feeding it into the Player prompt re-opens the prose-injection
121:    Holds no per-session state — the player system prompt is static for
129:        """Cache the player system prompt resolved from ``role_config``.
131:        Reading the prompt at construction time (not per-call) is
132:        deliberate: the prompt is a static role manifest artefact, and
134:        without changing behaviour. ``RoleConfig.load_player_prompt``
139:        self._player_prompt = role_config.load_player_prompt()
150:        are not yet woven into the prompt — Phase-1 wiring keeps the
151:        prompt scope narrow (player system prompt + raw learner message)
154:        context (text_name, focus_aos) without changing the call shape.
159:        _ = session_state.session_id
163:            client.generate, learner_message, self._player_prompt
177:        The assembled prompt carries the original learner message, the
182:        :meth:`_assemble_revise_prompt`.
184:        _ = session_state.session_id
185:        prompt = self._assemble_revise_prompt(
193:            client.generate, prompt, self._player_prompt
198:    def _assemble_revise_prompt(
204:        """Build the deterministic revise prompt.
216:            # short fixed precision so the prompt is byte-stable across
230:            # and the prompt must remain syntactically valid either way.
Read llm_player_adapter.py (lines 142-166)
I traced the full path — get_student_state → planner → SessionState → Player adapter. Here's the honest answer, and it has an important nuance.

Short answer: partially — it drives topic selection, but not generation
There is a real adaptive loop, but it operates at the planning layer, not at the layer where the fine-tuned model actually writes the tutoring content.

✅ What Graphiti memory genuinely influences
At tutor_start_session, the deterministic planner (pipeline.py:375) reads get_student_state from Graphiti and uses the stored per-topic confidence scores to:

Pick the session's focus topic — pick_lowest_confidence_topic, the learner's weakest topic outside a 48-hour cooldown (rules.py:114).
Set focus_aos, and compute related_misconceptions, an opening_prompt, and a rationale.
That focus topic flows all the way through into the turn via SessionState.topic. And at session-end, outcomes write back and shift confidence — which is exactly your observed 55→56→57→58% progression. So which topic a session is about genuinely adapts to the learner's history. That loop is real.

The full plan (topic, opening prompt, misconceptions) is also returned to the MCP caller in the tutor_start_session response as plan_summary (adapter.py:105).

⚠️ What it does not do — the nuance that matters
The fine-tuned Gemma Player model does not receive any of this in its prompt. Look at the Player adapter (llm_player_adapter.py:147-164) — the docstring is explicit:

"session_state is accepted for Protocol parity but its fields are not yet woven into the prompt — Phase-1 wiring keeps the prompt scope narrow (player system prompt + raw learner message)."

The code does _ = session_state.session_id (a no-op touch) and then client.generate(learner_message, self._player_prompt) — a static system prompt plus the raw message. Topic, focus AOs, confidence, and misconceptions never reach the model. And SessionState itself only carries session_id / student_id / text_name / topic / focus_aos / mode — it doesn't even transport misconceptions or confidence (session_state.py:39-44).

So: the tutor's explanations are not conditioned on Lilymay's stored misconceptions or weak areas. The graph chooses the subject; it doesn't shape the words.

If your sessions felt strongly personalised, that's most likely because Claude Desktop's side received the plan_summary from tutor_start_session and steered with it — not because the Gemma fine-tune was conditioned on memory.

What to say in the submission
Accurate:

"A Graphiti knowledge graph persists per-topic confidence for the learner. A deterministic planner reads it to select each session's focus — the weakest topic outside a cooldown window — and session outcomes write back, so topic selection adapts measurably across sessions."

Don't claim: that the tutor tailors its teaching to the student's specific misconceptions — that signal is computed but never reaches the model.

This is a more impactful gap than the citation anchors, and it's a contained fix: add misconceptions / confidence to SessionState, populate them in adapter.py, and weave topic + focus_aos + misconceptions into the Player prompt. That turns "memory selects the topic" into "memory shapes the lesson" — a genuinely stronger hackathon story.

Want me to scope that change and tell you if it's safely doable today? I'd recommend prioritising it over the anchors.

