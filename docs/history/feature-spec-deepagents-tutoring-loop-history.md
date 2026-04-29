/feature-spec "DeepAgents Tutoring Loop with Coach — Player-Coach integration, Coach rubric, session-end summary, async Graphiti write-back" \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context roles/tutor/prompts/coach.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/agents/coach.py \
  --context src/study_tutor/mcp/adapter.py


I'll execute the six-phase Propose-Review methodology for this feature. Starting with Phase 1 (silent context gathering).

Bash List project root
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/ 2>&1 | head -30

OUT
AGENTS.md
command_history.md
docs
domains
features
LICENSE
migrations
pyproject.toml
README.md
roles
scripts
src
tasks
tests
uv.lock
Bash Check existing features directory
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features 2>/dev/null || echo "no features dir"

OUT
graphiti-student-model
Read phase-1-scope.md
Read phase-1-build-plan.md
Read coach.md
Read coach.py
Read adapter.py
Bash List prompts dir and existing feature
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/roles/tutor/prompts/ 2>&1; ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/graphiti-student-model/ 2>&1

OUT
player.md
graphiti-student-model_assumptions.yaml
graphiti-student-model_summary.md
graphiti-student-model.feature
Read pyproject.toml
Read graphiti-student-model.feature
Read player.md
Bash Locate Tutoring DDRs and API contract
IN
find /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/design -name "DDR-002*" -o -name "DDR-003*" -o -name "API-tutoring*" 2>/dev/null | head -20

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/design/contracts/API-tutoring.md
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md
Read DDR-002-coach-async-subagent-owns-graphiti-writes.md
Read DDR-003-session-completed-emits-on-state-transition.md
Read API-tutoring.md
Context loaded: stack=python, 5 source modules found (mcp/adapter.py, llm/client.py, session/, knowledge/), 1 existing .feature file (graphiti-student-model), 4 ADRs (ARCH-018, ARCH-019, ARCH-012, ARCH-014), 4 DDRs (DDR-001..004), 1 latency spike (add_episode median 78.98s)

Proceeding to Phase 2 (Initial Proposal).


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: DeepAgents Tutoring Loop with Coach
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@phase-1 @feat-ph1-003 @tutoring-loop @coach
Feature: DeepAgents Tutoring Loop with Coach
  As the Study Tutor system
  I want every Player response gated by an evaluation-only Coach
    against a weighted pedagogical rubric, with revisions on failure,
    a session-end narrative summary, and fire-and-forget persistence
    of misconceptions and the session episode
  So that learners only see curriculum-accurate, AO-aligned, scaffolded responses,
    so that the student model gets richer at no caller-latency cost,
    and so that no caller-facing path ever waits on the knowledge graph.

  Background:
    Given a tutoring session is active for Lilymay on a planned topic
    And the Player is configured with the fine-tuned tutor and a Player prompt
    And the Coach is configured as an evaluation-only agent with no tools
    And the Coach uses a different provider than the Player
    And the Coach rubric has six weighted criteria with an acceptance threshold
    And the maximum number of Player revision attempts per turn is bounded
    And the Graphiti write helper is the single dispatch surface for every write
    And every Graphiti write site is fire-and-forget from the caller's perspective

━━ GROUP A: Key Examples (8 scenarios) ━━

  # Why: Core happy path — Player passes Coach on first attempt and the student sees the response
  @task:TASK-DTL-003
  @key-example @smoke @player-coach
  Scenario: A Player response that meets the Coach threshold is emitted to the learner
    Given the learner has just sent a turn message
    When the Player produces a response
    And the Coach evaluates the response against the rubric
    And the weighted Coach score meets or exceeds the acceptance threshold
    Then the Coach decision should be "accept"
    And the Player's response should be returned to the learner
    And the Coach's reasoning should be recorded in session-only logs
    And the Coach's reasoning should never be shown to the learner

  # Why: The revision loop is the entire point of having a Coach — a rejected response must trigger Player to revise
  @task:TASK-DTL-003
  @key-example @smoke @revision-loop
  Scenario: A Player response below the threshold triggers a revision that is then accepted
    Given the learner has just sent a turn message
    And the Player's first response scores below the acceptance threshold
    When the Player is asked to revise using the Coach's rubric feedback
    And the revised response scores at or above the acceptance threshold
    Then the Coach decision on the revision should be "accept"
    And the revised response should be returned to the learner
    And the original below-threshold response should never be shown to the learner

  # Why: All six rubric criteria are weighted — the score is a weighted sum, not a min or majority
  @task:TASK-DTL-002
  @key-example @rubric
  Scenario: The Coach reports a per-criterion score and a weighted total
    Given the learner has just sent a turn message
    When the Coach evaluates the Player's response
    Then the Coach output should include a score for curriculum accuracy
    And a score for AO alignment
    And a score for scaffolding depth
    And a score for grade-appropriate language
    And a score for constructive feedback
    And a score for quote fidelity
    And a single weighted total derived from the criteria and their weights
    And a list of any misconceptions the Coach observed in the learner's turn

  # Why: Misconceptions are how the student model gets richer over time — Coach owns this write per DDR-002
  @task:TASK-DTL-004
  @key-example @smoke @async @misconception
  Scenario: A misconception observed by the Coach is persisted without blocking the turn return
    Given the Coach is evaluating a Player response
    When the Coach identifies a misconception in the learner's turn
    Then the turn should return to the caller within the per-turn latency budget
    And a misconception-observed episode should eventually be persisted for the learner
    And the Coach should be the dispatcher of that persistence write
    And a write failure should be logged but never raised to the caller

  # Why: Session-end summary is the second-half outcome of the loop — it consolidates the session for next time
  @task:TASK-DTL-005
  @key-example @smoke @session-end @summary
  Scenario: Ending a session produces a session-completed episode with topics, AOs, turns, and narrative
    Given the session has had several tutor turns and at least one observed misconception
    When the learner ends the session
    Then the caller-facing acknowledgement should return within the session-end budget
    And a session-completed episode should eventually be persisted for the learner
    And the persisted episode should record the topics covered
    And the persisted episode should record the assessment objectives exercised
    And the persisted episode should record the number of turns and the duration
    And the persisted episode should include a short narrative summary of the session
    And the persisted episode should include the misconceptions surfaced during the session

  # Why: Events bus is the source of truth for subscribers; per DDR-003 it must not wait on the Graphiti write
  @task:TASK-DTL-005
  @key-example @events @async
  Scenario: The session.completed event emits on state transition, before the Graphiti write is scheduled
    Given the session has had at least one tutor turn
    When the learner ends the session
    Then the session.completed event should fire on the active-to-ended state transition
    And the session.completed event should fire before the session-end Graphiti write task is scheduled
    And subscribers should observe the event regardless of whether the Graphiti write succeeds

  # Why: Quote verification is the criterion that integrates with the source-typed RAG layer
  @task:TASK-DTL-002
  @key-example @rubric @quote-fidelity
  Scenario: A primary-text quote in the Player response is annotated and scored as fidelity-passing
    Given the session is on a primary text whose canonical edition is in the corpus
    And the Player's response contains a verbatim quote from that primary text
    When the quote verifier is run on the response before the Coach evaluates it
    Then the quote should be annotated with its canonical citation
    And the Coach's quote-fidelity score for the response should pass
    And the annotated response should be the version evaluated by the Coach

  # Why: Coach is structurally not a tutor — D5 invariant from agentic-dataset-factory carries forward
  @task:TASK-DTL-001
  @key-example @invariant @coach-shape
  Scenario: The Coach is constructed without tools and never produces learner-visible output
    Given the Coach factory is asked to construct a Coach for the session
    When the Coach is constructed
    Then the Coach should be configured with no tools
    And the Coach should have no filesystem access surface
    And no Coach-produced text should be returned to the learner under any branch of the loop

━━ GROUP B: Boundary Conditions (8 scenarios) ━━

  # Why: Threshold is the single load-bearing number in the loop — the just-inside / just-outside pair must be explicit
  @task:TASK-DTL-002
  @boundary @rubric
  Scenario Outline: Scores at and around the acceptance threshold drive the accept-or-revise decision
    Given the learner has just sent a turn message
    When the Player produces a response that scores <score>
    Then the Coach decision should be <decision>

    Examples:
      | score | decision |
      | 0.70  | accept   |
      | 0.69  | revise   |
      | 1.00  | accept   |
      | 0.00  | revise   |

  # Why: Revision budget is bounded — at exhaustion the loop must release the lowest-scoring reply, not loop forever
  @task:TASK-DTL-003
  @boundary @revision-loop
  Scenario: Three consecutive sub-threshold revisions release the lowest-scoring reply with a silent marker
    Given the learner has just sent a turn message
    And every Player response and revision so far has scored below the acceptance threshold
    When the maximum number of revision attempts has been reached
    Then the lowest-scoring reply observed across the attempts should be returned to the learner
    And a silent log marker should be recorded for session-end review
    And no further revision should be attempted on this turn

  # Why: Coach reasoning length is bounded by prompt instruction so reasoning logs stay tractable
  @task:TASK-DTL-001
  @boundary @coach-shape
  Scenario Outline: Coach reasoning at and around the length cap is recorded as expected
    When the Coach produces reasoning of approximately <length> words
    Then the recorded reasoning length should be <outcome>

    Examples:
      | length | outcome                              |
      | 199    | recorded in full                     |
      | 200    | recorded in full                     |
      | 201    | recorded in full but flagged as long |

  # Why: Per-turn latency budget is the hard constraint that justifies async writes and the revise-or-fallback rule
  @task:TASK-DTL-003
  @boundary @latency
  Scenario Outline: Turn latency at and around the per-turn budget meets or breaches the budget
    When a turn completes its Player-Coach loop in <elapsed> seconds
    Then the turn outcome should be <outcome>

    Examples:
      | elapsed | outcome                                            |
      | 29.99   | within the per-turn budget                         |
      | 30.00   | within the per-turn budget                         |
      | 30.01   | over the per-turn budget; logged for review        |

  # Why: tutor_session_end has its own tighter budget that must hold even when Graphiti is slow
  @task:TASK-DTL-005
  @boundary @latency @async
  Scenario: Session-end returns within budget even when the Graphiti write helper would take much longer
    Given the Graphiti write helper is configured to take longer than the session-end budget
    When the learner ends the session
    Then the caller-facing acknowledgement should still return within the session-end budget
    And the session-end Graphiti write should still be dispatched as a background task

  # Why: The narrative summary length is part of the session-end contract; just-inside vs just-outside must be made explicit
  @task:TASK-DTL-005
  @boundary @summary
  Scenario Outline: The session-end narrative summary stays within the prescribed sentence range
    When a session-end summary is generated
    Then the narrative summary should consist of <sentences> sentences

    Examples:
      | sentences |
      | one       |
      | two       |

  # Why: Min-quote-length boundary is the verifier's contract; quote_fidelity scoring depends on it
  @task:TASK-DTL-002
  @boundary @quote-fidelity
  Scenario Outline: The quote verifier only inspects quoted spans at or above the minimum length
    Given the Player response contains a quoted span of <words> words
    Then the verifier should <action>

    Examples:
      | words | action                              |
      | 3     | ignore the span                     |
      | 4     | inspect and verify the span         |
      | 5     | inspect and verify the span         |

  # Why: Empty rubric prompt is the just-outside constructor boundary — must fail loudly before any session uses it
  @task:TASK-DTL-001
  @boundary @negative @coach-shape
  Scenario: Constructing the Coach with an empty system prompt fails before the agent is built
    When the Coach factory is invoked with an empty system prompt
    Then construction should fail with an error indicating the prompt is required
    And no agent should be returned

━━ GROUP C: Negative Cases (7 scenarios) ━━

  # Why: Coach output must be schema-checked — malformed Coach output cannot be allowed to corrupt the loop
  @task:TASK-DTL-002
  @negative @rubric
  Scenario: A Coach response that does not match the expected schema is treated as a transient failure
    Given the Coach returns text that cannot be parsed as the expected verdict shape
    When the loop processes the Coach output
    Then the loop should treat the turn under the Coach-fallback policy
    And no malformed Coach output should be persisted as a misconception
    And the failure should be logged for session-end review

  # Why: Coach unreachable is a documented fallback path — the loop must not lock up when the Coach provider fails
  @task:TASK-DTL-003
  @negative @fallback
  Scenario: The Coach provider is unreachable for an entire turn
    Given the Coach provider returns no response within its evaluation budget
    When the loop processes the unevaluated turn
    Then the Player's response should still be returned to the learner under the documented fallback policy
    And the turn should be flagged for session-end review
    And no revision attempts should be made against an absent Coach evaluation

  # Why: Mid-session writes must never raise into the handler — this is the load-bearing async-write guarantee
  @task:TASK-DTL-004
  @negative @async @misconception
  Scenario: A misconception write that fails inside Graphiti does not surface to the caller
    Given a misconception has been observed by the Coach
    When the Graphiti write helper raises an error during the misconception write
    Then the error should be logged with structured fields
    And the error should not be raised from the turn handler
    And the turn should still return successfully to the learner

  # Why: Session-end write failure is symmetric to the mid-session case but applies at the session-end budget
  @task:TASK-DTL-005
  @negative @async @session-end
  Scenario: A session-end Graphiti write failure does not stop the session ending cleanly
    Given the learner has ended the session
    When the session-end Graphiti write task fails after dispatch
    Then the failure should be logged with structured fields
    And the session-completed event should still have been emitted on state transition
    And the caller should still observe the session as ended

  # Why: Role separation is structural, not prompt-based — Coach cannot be allowed to call tools even by mistake
  @task:TASK-DTL-001
  @negative @invariant @coach-shape
  Scenario: A Coach configuration that includes any tools is rejected at construction
    When the Coach factory is invoked with a non-empty tools list
    Then construction should fail with an error indicating tools are forbidden for the Coach
    And no agent should be returned

  # Why: Coach must never become a second tutor — output leaking to the learner is a hard failure
  @task:TASK-DTL-003
  @negative @invariant
  Scenario: A misconfigured loop that would expose Coach reasoning to the learner is detected and refused
    Given a loop configuration would route Coach reasoning into the learner-facing response
    When the configuration is validated at session start
    Then session start should fail with an error indicating Coach output may not reach the learner

  # Why: Two-provider rule is an explicit invariant from agentic-dataset-factory — same provider for both is forbidden
  @task:TASK-DTL-001
  @negative @invariant @coach-shape
  Scenario: A Coach configured to use the same provider as the Player is refused at construction
    Given the Player is configured with a provider
    When the Coach factory is invoked with the same provider
    Then construction should fail with an error indicating Coach and Player must differ
    And no agent should be returned

━━ GROUP D: Edge Cases (10 scenarios) ━━

  # Why: Two flush points can be in flight simultaneously — they must not interfere or share state
  @task:TASK-DTL-004
  @edge-case @async @concurrency
  Scenario: A misconception write in flight at session end coexists with the session-end write
    Given the Coach has dispatched a misconception write that has not yet completed
    When the learner ends the session
    Then the session-end write should be dispatched as a separate background task
    And both writes should run to completion or failure independently
    And neither write should block or be blocked by the other

  # Why: Multiple misconceptions in one turn must each get their own write, per DDR-002 per-observation ownership
  @task:TASK-DTL-004
  @edge-case @async @misconception
  Scenario: Two misconceptions observed in the same turn are written as two independent episodes
    Given the Coach observes two distinct misconceptions in a single turn
    When the misconception writes are dispatched
    Then each misconception should be persisted as its own episode
    And neither misconception write should be batched with the other
    And a failure of one write should not affect the other

  # Why: Session abandoned before any tutor turn must NOT emit session.completed — preserves I-T6 invariant
  @task:TASK-DTL-005
  @edge-case @events @invariant
  Scenario: Ending a session that never produced a tutor turn does not emit session.completed
    Given a session has been started but no tutor turn has been produced
    When the learner ends the session
    Then the session-completed event should not be emitted
    And no session-completed Graphiti episode should be scheduled

  # Why: AO3 contextual content path bypasses primary-text retrieval; quote_fidelity must not penalise the Player for that
  @task:TASK-DTL-002
  @edge-case @quote-fidelity @retrieval
  Scenario: A turn that runs in analysis mode is not penalised on quote fidelity for the absence of retrieved evidence
    Given the session-plan focus is contextual and retrieval is skipped
    When the Player produces a response that contains no primary-text quotes
    Then the Coach should not down-rank the response on quote fidelity
    And the turn metadata should record that retrieval was skipped with a reason

  # Why: A fabricated quote must be removed before it reaches the learner, not merely down-ranked
  @task:TASK-DTL-002
  @edge-case @quote-fidelity @safety
  Scenario: A fabricated primary-text quote in the Player response is corrected before the Coach evaluates
    Given the Player produces a response containing a quoted phrase that does not appear in the corpus
    When the quote verifier processes the response before the Coach evaluates it
    Then the unmatched quote should be removed or rewritten as paraphrase
    And the Coach should evaluate the rewritten response, not the original
    And the rewrite should be observable in the turn's recorded metadata

  # Why: Filesystem-backed corpus contents could carry malicious filename-style content; Coach must not be tricked into a tool call
  @task:TASK-DTL-001
  @edge-case @security @coach-shape
  Scenario: Adversarial content in the corpus does not cause the Coach to attempt a tool call
    Given the corpus contains a chunk whose text resembles a tool-call instruction
    When the Coach evaluates a Player response that quotes the adversarial chunk
    Then the Coach should produce its verdict as text only
    And no tool-call should be attempted by the Coach

  # Why: Misconception text comes from learner input — sanitisation is critical before it reaches the write helper
  @task:TASK-DTL-004
  @edge-case @security @async
  Scenario: A misconception derived from learner-supplied text is sanitised before the write is dispatched
    Given the learner's turn contains text resembling a prompt-injection attempt
    When the Coach records a misconception derived from that turn
    Then the misconception payload should be sanitised before dispatch
    And the persisted episode should not contain unescaped injection markers

  # Why: A graceful shutdown must not silently drop in-flight writes — DDR-002 promises a drain on shutdown
  @task:TASK-DTL-004
  @edge-case @async @lifecycle
  Scenario: A graceful shutdown drains in-flight Graphiti writes within the shutdown grace window
    Given several Graphiti writes are in flight
    When the runtime is asked to shut down gracefully
    Then in-flight writes should be allowed to finish within the shutdown grace window
    And any writes that did not finish within the window should be logged with structured fields

  # Why: Two concurrent sessions must keep their Coach evaluations strictly separated
  @task:TASK-DTL-003
  @edge-case @concurrency
  Scenario: Coach evaluations from two concurrent sessions do not contaminate each other
    Given two sessions are active for two different learners
    When each session has a Player response under Coach evaluation at the same time
    Then each session's accept-or-revise decision should reflect only its own response
    And neither session's misconception write should be attributed to the other learner

  # Why: A revision loop where the Coach changes its mind across attempts must still terminate predictably
  @task:TASK-DTL-003
  @edge-case @revision-loop
  Scenario: A revision attempt that scores below an earlier accepted attempt is not emitted in place of it
    Given a turn that has already been accepted at one revision level
    When a subsequent revision is somehow scored
    Then the originally accepted response should remain the response shown to the learner
    And no further attempt should be made on this turn

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 33 scenarios across 4 groups
  Group A — Key Examples: 8
  Group B — Boundary Conditions: 8 (including 4 outlines with multi-row tables)
  Group C — Negative Cases: 7
  Group D — Edge Cases: 10
Inferred assumptions: 9 (will be resolved in Phase 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review each group
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each group, you may:

  [A] Accept  — include all scenarios in this group as-is
  [R] Reject  — exclude all scenarios in this group
  [M] Modify  — accept but specify changes (provide inline)
  [+] Add     — accept and add additional scenarios you describe
  [?] Defer   — mark group for future specification; excluded from output

Fast path: type "A A A A" to accept all four groups at once.

GROUP A — Key Examples (8 scenarios): _
GROUP B — Boundary Conditions (8 scenarios): _
GROUP C — Negative Cases (7 scenarios): _
GROUP D — Edge Cases (10 scenarios): _
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Awaiting curation decisions per group before proceeding to Phase 4 (edge case expansion offer) and Phase 5 (assumption resolution).

command-history.md#1837-1837
A A A A
All four groups accepted. Proceeding to Phase 4.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Six additional scenarios identified — themes beyond what Group D already covers:

Security (2):
  - Coach output that contains directives intended to be obeyed by the
    Player on revision is not treated as instructions
  - A learner turn that contains a prompt-injection attempt against the
    Coach is evaluated as content, not obeyed as a directive

Integration boundaries (2):
  - The Player provider becomes unavailable between an initial Player
    response and a Coach-requested revision
  - The quote verifier itself raises an exception while processing a
    response (verifier failure must not block the loop)

Concurrency / lifecycle (2):
  - tutor_session_end is invoked while a tutor_turn for the same session
    is still inside its Player-Coach loop
  - The shared Graphiti write helper receives two simultaneous
    dispatches (one from the Coach, one from the Tutor handler)

[Y] Yes — show and curate them (same A/R/M/+/? actions)
[S] Sample — show 2 examples, then decide
[N] No — skip and proceed to Phase 5

Your choice [Y/S/N]:
Awaiting your choice.

Y
Drafting the six additional scenarios for curation.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION — 6 additional scenarios
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━ Security (2) ━━

  # Why: Coach reasoning is a free-text channel; if treated as Player instructions on revision, a malformed Coach
  #      response could effectively become a covert prompt rewrite. Revision input must be reduced to rubric scores
  #      and structured feedback, not pasted Coach prose.
  @task:TASK-DTL-003
  @edge-case @security @revision-loop
  Scenario: Directive-shaped Coach text on a rejected turn is not obeyed by the Player on revision
    Given the Coach rejects a Player response with reasoning that contains directive-shaped text
    When the Player is asked to revise based on that Coach feedback
    Then the Player's revision should be driven by the structured rubric feedback, not by free-text directives
    And no part of the Coach's free-text reasoning should be passed to the Player as a system-level instruction

  # Why: Learner-supplied input could contain an instruction-shaped payload aimed at the Coach's evaluator role.
  #      The Coach must score it as content quality, never act on it.
  @task:TASK-DTL-001
  @edge-case @security @coach-shape
  Scenario: A learner turn that contains a prompt-injection attempt against the Coach is evaluated as content
    Given the learner's turn contains text that resembles instructions addressed to the Coach
    When the Coach evaluates the Player's response to that turn
    Then the Coach should produce its verdict as a structured evaluation only
    And the Coach should not change its decision shape, score schema, or output channel based on the learner's text

━━ Integration boundaries (2) ━━

  # Why: Provider availability can change mid-turn — the loop must not deadlock or silently drop the turn
  @task:TASK-DTL-003
  @edge-case @integration @fallback
  Scenario: The Player provider becomes unavailable between the first response and a requested revision
    Given the Player produced a first response that scored below the acceptance threshold
    When the Player provider is unavailable for the revision attempt
    Then the loop should fall back to the documented unevaluated-turn policy for this turn
    And the turn should be flagged for session-end review with a provider-unavailable reason

  # Why: A failure inside the quote verifier must not propagate as a turn failure — the loop has to keep moving
  @task:TASK-DTL-002
  @edge-case @integration @quote-fidelity
  Scenario: The quote verifier raises an exception while processing a Player response
    Given the quote verifier raises an unexpected exception on a Player response
    When the loop processes the verifier failure
    Then the response should be passed to the Coach unannotated
    And the Coach should evaluate the unannotated response under the documented fallback policy
    And the verifier failure should be logged for session-end review

━━ Concurrency / lifecycle (2) ━━

  # Why: Sessions are append-only and end-once, but a slow turn could overlap with a session-end call;
  #      behaviour must be deterministic and never both end the session AND emit a turn afterwards
  @task:TASK-DTL-005
  @edge-case @concurrency @lifecycle
  Scenario: tutor_session_end is invoked while a tutor_turn for the same session is still in flight
    Given a tutor_turn is still inside its Player-Coach loop for an active session
    When tutor_session_end is invoked for the same session
    Then the in-flight turn should either complete and append before the session is marked ended, or be discarded with no append
    And no tutor turn should be appended to the session after the session has been marked ended
    And no session-completed event should be emitted before the in-flight turn has been resolved one way or the other

  # Why: The shared write helper is the single dispatch surface; it must remain correct under simultaneous calls
  @task:TASK-DTL-004
  @edge-case @concurrency @async
  Scenario: The shared write helper handles simultaneous dispatches from the Coach and the Tutor handler
    Given the Coach is about to dispatch a misconception write
    And the Tutor handler is about to dispatch a topic-confidence-update write
    When both dispatches occur simultaneously
    Then both writes should be scheduled as independent fire-and-forget tasks
    And neither dispatch should block or be blocked by the other
    And the structured-log line for one write should not be conflated with the other

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review the 6 expansion scenarios
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Same A/R/M/+/? actions, by sub-group:

EXPANSION — Security (2 scenarios):              _
EXPANSION — Integration boundaries (2 scenarios):_
EXPANSION — Concurrency / lifecycle (2 scenarios):_

Fast path: "A A A" accepts all three sub-groups.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Awaiting curation of the expansion sub-groups.

A A A
All expansion sub-groups accepted (39 scenarios total now). Proceeding to Phase 5.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSUMPTION RESOLUTION (10 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each assumption has a proposed default. Press Enter (or type "accept") to
take the default; or type the value you want to use.

[1] Coach acceptance threshold (weighted score)
    Proposed: 0.70   Confidence: high
    Basis: phase-1-scope.md §FEAT-PH1-003.1 — "Acceptance threshold: 0.7"
    Accept or enter value: _

[2] Maximum Player revision attempts per turn
    Proposed: 3   Confidence: high
    Basis: phase-1-scope.md §FEAT-PH1-003.1 — "max 3 attempts, then surface lowest-scoring reply"
    Accept or enter value: _

[3] Per-turn latency budget (Player-Coach loop end-to-end, p95)
    Proposed: 30 seconds   Confidence: high
    Basis: phase-1-scope.md §FEAT-PH1-003.3 — "tutor_turn p95 < 30 seconds"
    Accept or enter value: _

[4] tutor_session_end caller-facing budget
    Proposed: 2 seconds   Confidence: high
    Basis: API-tutoring.md §3.4 — "Latency target: < 2s"; SR-08 acceptance criterion
    Accept or enter value: _

[5] Coach reasoning length cap
    Proposed: 200 words   Confidence: high
    Basis: phase-1-scope.md §FEAT-PH1-003.6 + Coach prompt structure — "max 200 words of reasoning"
    Accept or enter value: _

[6] Behaviour when Coach reasoning exceeds the 200-word cap
    Proposed: recorded in full but flagged as long for session-end review (no truncation, no rejection)
    Confidence: low
    Basis: scope states the cap as a prompt instruction but does not specify what happens at 201+ words.
           A flag-not-truncate default preserves diagnostic information for tuning.
    Accept or enter value: _

[7] Loop policy when Coach output is malformed (cannot parse the verdict)
    Proposed: same as Coach-unreachable — apply documented unevaluated-turn fallback;
              do not persist any misconception derived from the malformed output;
              flag the turn for session-end review
    Confidence: medium
    Basis: scope documents an "accept-first-revise-later" fallback for Coach unavailability;
           extending it to the malformed-output case is the safest symmetric default.
    Accept or enter value: _

[8] How Coach rejection feedback reaches the Player on revision
    Proposed: structured rubric feedback only (per-criterion scores + structured "what to improve")
              — Coach free-text reasoning is NOT pasted into the Player's system prompt or user message
    Confidence: medium
    Basis: D5 invariant (Coach evaluation-only) + DDR-003 / DDR-002 separation of surfaces.
           Treating Coach prose as Player instructions would create a covert rewrite channel.
    Accept or enter value: _

[9] Two-provider invariant (Coach != Player) enforcement point
    Proposed: enforced at Coach factory construction time — factory raises an error if both
              are configured to the same provider
    Confidence: medium
    Basis: scope ("Coach uses a different provider than Player. Two-provider separation is an
           explicit invariant") names it as an invariant; the agentic-dataset-factory `create_coach`
           does not check this today, so the rule is being introduced as a structural check here.
    Accept or enter value: _

[10] Session-end narrative summary length
     Proposed: 1 to 2 sentences (both lengths acceptable)
     Confidence: medium
     Basis: scope says "a two-sentence narrative summary" — wording suggests two but does not
            forbid one. A tolerant 1–2 range avoids spurious revision loops on summary length.
     Accept or enter value: _

[11] Shutdown grace window for in-flight Graphiti writes (drain duration)
     Proposed: 5 seconds   Confidence: low
     Basis: not specified in FEAT-PH1-003 scope; TASK-GSM-004 references a `drain()` helper
            without naming a duration. 5s is a small finite window that bounds shutdown latency
            while letting most short writes complete.
     Accept or enter value: _

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Awaiting your responses (one per item, or "accept all" to take every default).

command-history.md
accept defaults
All defaults accepted. Writing Phase 6 output files.

Bash Create output directory
IN
mkdir -p /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/deepagents-tutoring-loop

OUT
(Bash completed with no output)
Write deepagents-tutoring-loop.feature
469 lines
# Generated by /feature-spec
# Feature: DeepAgents Tutoring Loop with Coach
# Stack: python
# Assumptions: 11 (see deepagents-tutoring-loop_assumptions.yaml)
# Generated: 2026-04-29

@phase-1 @feat-ph1-003 @tutoring-loop @coach
Feature: DeepAgents Tutoring Loop with Coach
  As the Study Tutor system
  I want every Player response gated by an evaluation-only Coach
    against a weighted pedagogical rubric, with revisions on failure,
    a session-end narrative summary, and fire-and-forget persistence
    of misconceptions and the session episode
  So that learners only see curriculum-accurate, AO-aligned, scaffolded responses,
    so that the student model gets richer at no caller-latency cost,
    and so that no caller-facing path ever waits on the knowledge graph.

  Background:
    Given a tutoring session is active for Lilymay on a planned topic
    And the Player is configured with the fine-tuned tutor and a Player prompt
    And the Coach is configured as an evaluation-only agent with no tools
    And the Coach uses a different provider than the Player
    # [ASSUMPTION: confidence=high] Six rubric criteria: curriculum accuracy, AO alignment, scaffolding depth, grade-appropriate language, constructive feedback, quote fidelity
    And the Coach rubric has six weighted criteria with an acceptance threshold
    # [ASSUMPTION: confidence=high] Maximum revisions per turn: 3 (phase-1-scope §FEAT-PH1-003.1)
    And the maximum number of Player revision attempts per turn is bounded
    And the Graphiti write helper is the single dispatch surface for every write
    And every Graphiti write site is fire-and-forget from the caller's perspective

  # ==========================================================================
  # GROUP A: Key Examples
  # ==========================================================================

  # Why: Core happy path — Player passes Coach on first attempt and the student sees the response
  @task:TASK-DTL-003
  @key-example @smoke @player-coach
  Scenario: A Player response that meets the Coach threshold is emitted to the learner
    Given the learner has just sent a turn message
    When the Player produces a response
    And the Coach evaluates the response against the rubric
    # [ASSUMPTION: confidence=high] Acceptance threshold: weighted score >= 0.70
    And the weighted Coach score meets or exceeds the acceptance threshold
    Then the Coach decision should be "accept"
    And the Player's response should be returned to the learner
    And the Coach's reasoning should be recorded in session-only logs
    And the Coach's reasoning should never be shown to the learner

  # Why: The revision loop is the entire point of having a Coach — a rejected response must trigger Player to revise
  @task:TASK-DTL-003
  @key-example @smoke @revision-loop
  Scenario: A Player response below the threshold triggers a revision that is then accepted
    Given the learner has just sent a turn message
    And the Player's first response scores below the acceptance threshold
    # [ASSUMPTION: confidence=medium] Coach feedback to Player on revision is structured rubric scores plus structured "what to improve" — not pasted Coach free-text prose
    When the Player is asked to revise using the Coach's rubric feedback
    And the revised response scores at or above the acceptance threshold
    Then the Coach decision on the revision should be "accept"
    And the revised response should be returned to the learner
    And the original below-threshold response should never be shown to the learner

  # Why: All six rubric criteria are weighted — the score is a weighted sum, not a min or majority
  @task:TASK-DTL-002
  @key-example @rubric
  Scenario: The Coach reports a per-criterion score and a weighted total
    Given the learner has just sent a turn message
    When the Coach evaluates the Player's response
    Then the Coach output should include a score for curriculum accuracy
    And a score for AO alignment
    And a score for scaffolding depth
    And a score for grade-appropriate language
    And a score for constructive feedback
    And a score for quote fidelity
    And a single weighted total derived from the criteria and their weights
    And a list of any misconceptions the Coach observed in the learner's turn

  # Why: Misconceptions are how the student model gets richer over time — Coach owns this write per DDR-002
  @task:TASK-DTL-004
  @key-example @smoke @async @misconception
  Scenario: A misconception observed by the Coach is persisted without blocking the turn return
    Given the Coach is evaluating a Player response
    When the Coach identifies a misconception in the learner's turn
    # [ASSUMPTION: confidence=high] Per-turn budget: p95 < 30 seconds
    Then the turn should return to the caller within the per-turn latency budget
    And a misconception-observed episode should eventually be persisted for the learner
    And the Coach should be the dispatcher of that persistence write
    And a write failure should be logged but never raised to the caller

  # Why: Session-end summary is the second-half outcome of the loop — it consolidates the session for next time
  @task:TASK-DTL-005
  @key-example @smoke @session-end @summary
  Scenario: Ending a session produces a session-completed episode with topics, AOs, turns, and narrative
    Given the session has had several tutor turns and at least one observed misconception
    When the learner ends the session
    # [ASSUMPTION: confidence=high] Session-end caller-facing budget: < 2 seconds
    Then the caller-facing acknowledgement should return within the session-end budget
    And a session-completed episode should eventually be persisted for the learner
    And the persisted episode should record the topics covered
    And the persisted episode should record the assessment objectives exercised
    And the persisted episode should record the number of turns and the duration
    # [ASSUMPTION: confidence=medium] Narrative summary is one to two sentences (both lengths acceptable)
    And the persisted episode should include a short narrative summary of the session
    And the persisted episode should include the misconceptions surfaced during the session

  # Why: Events bus is the source of truth for subscribers; per DDR-003 it must not wait on the Graphiti write
  @task:TASK-DTL-005
  @key-example @events @async
  Scenario: The session.completed event emits on state transition, before the Graphiti write is scheduled
    Given the session has had at least one tutor turn
    When the learner ends the session
    Then the session.completed event should fire on the active-to-ended state transition
    And the session.completed event should fire before the session-end Graphiti write task is scheduled
    And subscribers should observe the event regardless of whether the Graphiti write succeeds

  # Why: Quote verification is the criterion that integrates with the source-typed RAG layer
  @task:TASK-DTL-002
  @key-example @rubric @quote-fidelity
  Scenario: A primary-text quote in the Player response is annotated and scored as fidelity-passing
    Given the session is on a primary text whose canonical edition is in the corpus
    And the Player's response contains a verbatim quote from that primary text
    When the quote verifier is run on the response before the Coach evaluates it
    Then the quote should be annotated with its canonical citation
    And the Coach's quote-fidelity score for the response should pass
    And the annotated response should be the version evaluated by the Coach

  # Why: Coach is structurally not a tutor — D5 invariant from agentic-dataset-factory carries forward
  @task:TASK-DTL-001
  @key-example @invariant @coach-shape
  Scenario: The Coach is constructed without tools and never produces learner-visible output
    Given the Coach factory is asked to construct a Coach for the session
    When the Coach is constructed
    Then the Coach should be configured with no tools
    And the Coach should have no filesystem access surface
    And no Coach-produced text should be returned to the learner under any branch of the loop

  # ==========================================================================
  # GROUP B: Boundary Conditions
  # ==========================================================================

  # Why: Threshold is the single load-bearing number in the loop — the just-inside / just-outside pair must be explicit
  @task:TASK-DTL-002
  @boundary @rubric
  Scenario Outline: Scores at and around the acceptance threshold drive the accept-or-revise decision
    Given the learner has just sent a turn message
    When the Player produces a response that scores <score>
    Then the Coach decision should be <decision>

    Examples:
      | score | decision |
      | 0.70  | accept   |
      | 0.69  | revise   |
      | 1.00  | accept   |
      | 0.00  | revise   |

  # Why: Revision budget is bounded — at exhaustion the loop must release the lowest-scoring reply, not loop forever
  @task:TASK-DTL-003
  @boundary @revision-loop
  Scenario: Three consecutive sub-threshold revisions release the lowest-scoring reply with a silent marker
    Given the learner has just sent a turn message
    And every Player response and revision so far has scored below the acceptance threshold
    When the maximum number of revision attempts has been reached
    Then the lowest-scoring reply observed across the attempts should be returned to the learner
    And a silent log marker should be recorded for session-end review
    And no further revision should be attempted on this turn

  # Why: Coach reasoning length is bounded by prompt instruction so reasoning logs stay tractable
  @task:TASK-DTL-001
  @boundary @coach-shape
  Scenario Outline: Coach reasoning at and around the length cap is recorded as expected
    # [ASSUMPTION: confidence=high] Reasoning length cap: 200 words
    # [ASSUMPTION: confidence=low] Behaviour beyond the cap: recorded in full but flagged as long for session-end review (no truncation, no rejection)
    When the Coach produces reasoning of approximately <length> words
    Then the recorded reasoning length should be <outcome>

    Examples:
      | length | outcome                              |
      | 199    | recorded in full                     |
      | 200    | recorded in full                     |
      | 201    | recorded in full but flagged as long |

  # Why: Per-turn latency budget is the hard constraint that justifies async writes and the revise-or-fallback rule
  @task:TASK-DTL-003
  @boundary @latency
  Scenario Outline: Turn latency at and around the per-turn budget meets or breaches the budget
    When a turn completes its Player-Coach loop in <elapsed> seconds
    Then the turn outcome should be <outcome>

    Examples:
      | elapsed | outcome                                            |
      | 29.99   | within the per-turn budget                         |
      | 30.00   | within the per-turn budget                         |
      | 30.01   | over the per-turn budget; logged for review        |

  # Why: tutor_session_end has its own tighter budget that must hold even when Graphiti is slow
  @task:TASK-DTL-005
  @boundary @latency @async
  Scenario: Session-end returns within budget even when the Graphiti write helper would take much longer
    Given the Graphiti write helper is configured to take longer than the session-end budget
    When the learner ends the session
    Then the caller-facing acknowledgement should still return within the session-end budget
    And the session-end Graphiti write should still be dispatched as a background task

  # Why: The narrative summary length is part of the session-end contract; just-inside vs just-outside must be made explicit
  @task:TASK-DTL-005
  @boundary @summary
  Scenario Outline: The session-end narrative summary stays within the prescribed sentence range
    # [ASSUMPTION: confidence=medium] Acceptable narrative summary lengths: one or two sentences
    When a session-end summary is generated
    Then the narrative summary should consist of <sentences> sentences

    Examples:
      | sentences |
      | one       |
      | two       |

  # Why: Min-quote-length boundary is the verifier's contract; quote_fidelity scoring depends on it
  @task:TASK-DTL-002
  @boundary @quote-fidelity
  Scenario Outline: The quote verifier only inspects quoted spans at or above the minimum length
    # [ASSUMPTION: confidence=high] Minimum quoted-span length for verification: 4 words (FEAT-PH1-004 §4)
    Given the Player response contains a quoted span of <words> words
    Then the verifier should <action>

    Examples:
      | words | action                              |
      | 3     | ignore the span                     |
      | 4     | inspect and verify the span         |
      | 5     | inspect and verify the span         |

  # Why: Empty rubric prompt is the just-outside constructor boundary — must fail loudly before any session uses it
  @task:TASK-DTL-001
  @boundary @negative @coach-shape
  Scenario: Constructing the Coach with an empty system prompt fails before the agent is built
    When the Coach factory is invoked with an empty system prompt
    Then construction should fail with an error indicating the prompt is required
    And no agent should be returned

  # ==========================================================================
  # GROUP C: Negative Cases
  # ==========================================================================

  # Why: Coach output must be schema-checked — malformed Coach output cannot be allowed to corrupt the loop
  @task:TASK-DTL-002
  @negative @rubric
  Scenario: A Coach response that does not match the expected schema is treated as a transient failure
    Given the Coach returns text that cannot be parsed as the expected verdict shape
    # [ASSUMPTION: confidence=medium] Malformed Coach output policy mirrors Coach-unreachable: apply the documented unevaluated-turn fallback; do not persist any misconception derived from the malformed output; flag the turn for session-end review
    When the loop processes the Coach output
    Then the loop should treat the turn under the Coach-fallback policy
    And no malformed Coach output should be persisted as a misconception
    And the failure should be logged for session-end review

  # Why: Coach unreachable is a documented fallback path — the loop must not lock up when the Coach provider fails
  @task:TASK-DTL-003
  @negative @fallback
  Scenario: The Coach provider is unreachable for an entire turn
    Given the Coach provider returns no response within its evaluation budget
    When the loop processes the unevaluated turn
    Then the Player's response should still be returned to the learner under the documented fallback policy
    And the turn should be flagged for session-end review
    And no revision attempts should be made against an absent Coach evaluation

  # Why: Mid-session writes must never raise into the handler — this is the load-bearing async-write guarantee
  @task:TASK-DTL-004
  @negative @async @misconception
  Scenario: A misconception write that fails inside Graphiti does not surface to the caller
    Given a misconception has been observed by the Coach
    When the Graphiti write helper raises an error during the misconception write
    Then the error should be logged with structured fields
    And the error should not be raised from the turn handler
    And the turn should still return successfully to the learner

  # Why: Session-end write failure is symmetric to the mid-session case but applies at the session-end budget
  @task:TASK-DTL-005
  @negative @async @session-end
  Scenario: A session-end Graphiti write failure does not stop the session ending cleanly
    Given the learner has ended the session
    When the session-end Graphiti write task fails after dispatch
    Then the failure should be logged with structured fields
    And the session-completed event should still have been emitted on state transition
    And the caller should still observe the session as ended

  # Why: Role separation is structural, not prompt-based — Coach cannot be allowed to call tools even by mistake
  @task:TASK-DTL-001
  @negative @invariant @coach-shape
  Scenario: A Coach configuration that includes any tools is rejected at construction
    When the Coach factory is invoked with a non-empty tools list
    Then construction should fail with an error indicating tools are forbidden for the Coach
    And no agent should be returned

  # Why: Coach must never become a second tutor — output leaking to the learner is a hard failure
  @task:TASK-DTL-003
  @negative @invariant
  Scenario: A misconfigured loop that would expose Coach reasoning to the learner is detected and refused
    Given a loop configuration would route Coach reasoning into the learner-facing response
    When the configuration is validated at session start
    Then session start should fail with an error indicating Coach output may not reach the learner

  # Why: Two-provider rule is an explicit invariant from agentic-dataset-factory — same provider for both is forbidden
  @task:TASK-DTL-001
  @negative @invariant @coach-shape
  Scenario: A Coach configured to use the same provider as the Player is refused at construction
    Given the Player is configured with a provider
    # [ASSUMPTION: confidence=medium] The two-provider invariant is enforced at Coach factory construction time (factory raises an error if both are configured to the same provider)
    When the Coach factory is invoked with the same provider
    Then construction should fail with an error indicating Coach and Player must differ
    And no agent should be returned

  # ==========================================================================
  # GROUP D: Edge Cases
  # ==========================================================================

  # Why: Two flush points can be in flight simultaneously — they must not interfere or share state
  @task:TASK-DTL-004
  @edge-case @async @concurrency
  Scenario: A misconception write in flight at session end coexists with the session-end write
    Given the Coach has dispatched a misconception write that has not yet completed
    When the learner ends the session
    Then the session-end write should be dispatched as a separate background task
    And both writes should run to completion or failure independently
    And neither write should block or be blocked by the other

  # Why: Multiple misconceptions in one turn must each get their own write, per DDR-002 per-observation ownership
  @task:TASK-DTL-004
  @edge-case @async @misconception
  Scenario: Two misconceptions observed in the same turn are written as two independent episodes
    Given the Coach observes two distinct misconceptions in a single turn
    When the misconception writes are dispatched
    Then each misconception should be persisted as its own episode
    And neither misconception write should be batched with the other
    And a failure of one write should not affect the other

  # Why: Session abandoned before any tutor turn must NOT emit session.completed — preserves I-T6 invariant
  @task:TASK-DTL-005
  @edge-case @events @invariant
  Scenario: Ending a session that never produced a tutor turn does not emit session.completed
    Given a session has been started but no tutor turn has been produced
    When the learner ends the session
    Then the session-completed event should not be emitted
    And no session-completed Graphiti episode should be scheduled

  # Why: AO3 contextual content path bypasses primary-text retrieval; quote_fidelity must not penalise the Player for that
  @task:TASK-DTL-002
  @edge-case @quote-fidelity @retrieval
  Scenario: A turn that runs in analysis mode is not penalised on quote fidelity for the absence of retrieved evidence
    Given the session-plan focus is contextual and retrieval is skipped
    When the Player produces a response that contains no primary-text quotes
    Then the Coach should not down-rank the response on quote fidelity
    And the turn metadata should record that retrieval was skipped with a reason

  # Why: A fabricated quote must be removed before it reaches the learner, not merely down-ranked
  @task:TASK-DTL-002
  @edge-case @quote-fidelity @safety
  Scenario: A fabricated primary-text quote in the Player response is corrected before the Coach evaluates
    Given the Player produces a response containing a quoted phrase that does not appear in the corpus
    When the quote verifier processes the response before the Coach evaluates it
    Then the unmatched quote should be removed or rewritten as paraphrase
    And the Coach should evaluate the rewritten response, not the original
    And the rewrite should be observable in the turn's recorded metadata

  # Why: Filesystem-backed corpus contents could carry malicious filename-style content; Coach must not be tricked into a tool call
  @task:TASK-DTL-001
  @edge-case @security @coach-shape
  Scenario: Adversarial content in the corpus does not cause the Coach to attempt a tool call
    Given the corpus contains a chunk whose text resembles a tool-call instruction
    When the Coach evaluates a Player response that quotes the adversarial chunk
    Then the Coach should produce its verdict as text only
    And no tool-call should be attempted by the Coach

  # Why: Misconception text comes from learner input — sanitisation is critical before it reaches the write helper
  @task:TASK-DTL-004
  @edge-case @security @async
  Scenario: A misconception derived from learner-supplied text is sanitised before the write is dispatched
    Given the learner's turn contains text resembling a prompt-injection attempt
    When the Coach records a misconception derived from that turn
    Then the misconception payload should be sanitised before dispatch
    And the persisted episode should not contain unescaped injection markers

  # Why: A graceful shutdown must not silently drop in-flight writes — DDR-002 promises a drain on shutdown
  @task:TASK-DTL-004
  @edge-case @async @lifecycle
  Scenario: A graceful shutdown drains in-flight Graphiti writes within the shutdown grace window
    Given several Graphiti writes are in flight
    # [ASSUMPTION: confidence=low] Shutdown grace window for in-flight writes: 5 seconds
    When the runtime is asked to shut down gracefully
    Then in-flight writes should be allowed to finish within the shutdown grace window
    And any writes that did not finish within the window should be logged with structured fields

  # Why: Two concurrent sessions must keep their Coach evaluations strictly separated
  @task:TASK-DTL-003
  @edge-case @concurrency
  Scenario: Coach evaluations from two concurrent sessions do not contaminate each other
    Given two sessions are active for two different learners
    When each session has a Player response under Coach evaluation at the same time
    Then each session's accept-or-revise decision should reflect only its own response
    And neither session's misconception write should be attributed to the other learner

  # Why: A revision loop where the Coach changes its mind across attempts must still terminate predictably
  @task:TASK-DTL-003
  @edge-case @revision-loop
  Scenario: A revision attempt that scores below an earlier accepted attempt is not emitted in place of it
    Given a turn that has already been accepted at one revision level
    When a subsequent revision is somehow scored
    Then the originally accepted response should remain the response shown to the learner
    And no further attempt should be made on this turn

  # ==========================================================================
  # GROUP E: Edge Case Expansion — Security, Integration, Concurrency
  # ==========================================================================

  # Why: Coach reasoning is a free-text channel; if treated as Player instructions on revision, a malformed
  #      Coach response could effectively become a covert prompt rewrite
  @task:TASK-DTL-003
  @edge-case @security @revision-loop
  Scenario: Directive-shaped Coach text on a rejected turn is not obeyed by the Player on revision
    Given the Coach rejects a Player response with reasoning that contains directive-shaped text
    # [ASSUMPTION: confidence=medium] Player revision input is structured rubric feedback only — Coach free-text reasoning is not pasted into the Player's system prompt or user message
    When the Player is asked to revise based on that Coach feedback
    Then the Player's revision should be driven by the structured rubric feedback, not by free-text directives
    And no part of the Coach's free-text reasoning should be passed to the Player as a system-level instruction

  # Why: Learner-supplied input could contain an instruction-shaped payload aimed at the Coach's evaluator role
  @task:TASK-DTL-001
  @edge-case @security @coach-shape
  Scenario: A learner turn that contains a prompt-injection attempt against the Coach is evaluated as content
    Given the learner's turn contains text that resembles instructions addressed to the Coach
    When the Coach evaluates the Player's response to that turn
    Then the Coach should produce its verdict as a structured evaluation only
    And the Coach should not change its decision shape, score schema, or output channel based on the learner's text

  # Why: Provider availability can change mid-turn — the loop must not deadlock or silently drop the turn
  @task:TASK-DTL-003
  @edge-case @integration @fallback
  Scenario: The Player provider becomes unavailable between the first response and a requested revision
    Given the Player produced a first response that scored below the acceptance threshold
    When the Player provider is unavailable for the revision attempt
    Then the loop should fall back to the documented unevaluated-turn policy for this turn
    And the turn should be flagged for session-end review with a provider-unavailable reason

  # Why: A failure inside the quote verifier must not propagate as a turn failure — the loop has to keep moving
  @task:TASK-DTL-002
  @edge-case @integration @quote-fidelity
  Scenario: The quote verifier raises an exception while processing a Player response
    Given the quote verifier raises an unexpected exception on a Player response
    When the loop processes the verifier failure
    Then the response should be passed to the Coach unannotated
    And the Coach should evaluate the unannotated response under the documented fallback policy
    And the verifier failure should be logged for session-end review

  # Why: Sessions are append-only and end-once; a slow turn could overlap with a session-end call
  @task:TASK-DTL-005
  @edge-case @concurrency @lifecycle
  Scenario: tutor_session_end is invoked while a tutor_turn for the same session is still in flight
    Given a tutor_turn is still inside its Player-Coach loop for an active session
    When tutor_session_end is invoked for the same session
    Then the in-flight turn should either complete and append before the session is marked ended, or be discarded with no append
    And no tutor turn should be appended to the session after the session has been marked ended
    And no session-completed event should be emitted before the in-flight turn has been resolved one way or the other

  # Why: The shared write helper is the single dispatch surface; it must remain correct under simultaneous calls
  @task:TASK-DTL-004
  @edge-case @concurrency @async
  Scenario: The shared write helper handles simultaneous dispatches from the Coach and the Tutor handler
    Given the Coach is about to dispatch a misconception write
    And the Tutor handler is about to dispatch a topic-confidence-update write
    When both dispatches occur simultaneously
    Then both writes should be scheduled as independent fire-and-forget tasks
    And neither dispatch should block or be blocked by the other
    And the structured-log line for one write should not be conflated with the other
Write deepagents-tutoring-loop_assumptions.yaml
86 lines
# Assumptions manifest for deepagents-tutoring-loop.feature
# Generated by /feature-spec

feature: "DeepAgents Tutoring Loop with Coach"
generated: "2026-04-29"
stack: "python"
review_required: true   # 2 low-confidence assumptions remain (ASSUM-006, ASSUM-011)

assumptions:
  - id: "ASSUM-001"
    scenario: "A Player response that meets the Coach threshold is emitted to the learner"
    assumption: "Coach acceptance threshold is a weighted score >= 0.70"
    confidence: high
    basis: "phase-1-scope.md §FEAT-PH1-003.1 — 'Acceptance threshold: 0.7 weighted score. Below threshold triggers Player revision.'"
    human_response: "confirmed"

  - id: "ASSUM-002"
    scenario: "Three consecutive sub-threshold revisions release the lowest-scoring reply with a silent marker"
    assumption: "Maximum Player revision attempts per turn is 3"
    confidence: high
    basis: "phase-1-scope.md §FEAT-PH1-003.1 — 'max 3 attempts, then surface lowest-scoring reply with a silent log marker'"
    human_response: "confirmed"

  - id: "ASSUM-003"
    scenario: "Turn latency at and around the per-turn budget meets or breaches the budget"
    assumption: "Per-turn Player-Coach loop budget is p95 < 30 seconds end-to-end"
    confidence: high
    basis: "phase-1-scope.md §FEAT-PH1-003.3 — 'tutor_turn p95 < 30 seconds end-to-end'"
    human_response: "confirmed"

  - id: "ASSUM-004"
    scenario: "Session-end returns within budget even when the Graphiti write helper would take much longer"
    assumption: "tutor_session_end caller-facing budget is < 2 seconds"
    confidence: high
    basis: "API-tutoring.md §3.4 — 'Latency target: < 2s'; SR-08 acceptance criterion in phase-1-scope.md"
    human_response: "confirmed"

  - id: "ASSUM-005"
    scenario: "Coach reasoning at and around the length cap is recorded as expected"
    assumption: "Coach reasoning length cap is 200 words"
    confidence: high
    basis: "phase-1-scope.md §FEAT-PH1-003.6 — 'max 200 words of reasoning' (constraint in Coach prompt)"
    human_response: "confirmed"

  - id: "ASSUM-006"
    scenario: "Coach reasoning at and around the length cap is recorded as expected"
    assumption: "When Coach reasoning exceeds the cap, the reasoning is recorded in full but flagged as long for session-end review (no truncation, no rejection)"
    confidence: low
    basis: "Scope states the cap as a prompt instruction but does not specify behaviour at 201+ words. Flag-not-truncate default preserves diagnostic information for tuning."
    human_response: "confirmed"

  - id: "ASSUM-007"
    scenario: "A Coach response that does not match the expected schema is treated as a transient failure"
    assumption: "Loop policy when Coach output is malformed mirrors the Coach-unreachable policy: apply documented unevaluated-turn fallback; do not persist any misconception derived from the malformed output; flag the turn for session-end review"
    confidence: medium
    basis: "Scope documents an 'accept-first-revise-later' fallback for Coach unavailability; extending it to the malformed-output case is the safest symmetric default."
    human_response: "confirmed"

  - id: "ASSUM-008"
    scenario: "A Player response below the threshold triggers a revision that is then accepted; Directive-shaped Coach text on a rejected turn is not obeyed by the Player on revision"
    assumption: "Coach feedback to Player on revision is structured rubric scores plus structured 'what to improve' fields only — Coach free-text reasoning is NOT pasted into the Player's system prompt or user message"
    confidence: medium
    basis: "D5 invariant (Coach evaluation-only) + DDR-003 / DDR-002 separation of surfaces. Treating Coach prose as Player instructions would create a covert rewrite channel."
    human_response: "confirmed"

  - id: "ASSUM-009"
    scenario: "A Coach configured to use the same provider as the Player is refused at construction"
    assumption: "The two-provider invariant (Coach != Player) is enforced at Coach factory construction time; the factory raises an error if both are configured to the same provider"
    confidence: medium
    basis: "Scope names two-provider separation as 'an explicit invariant'. The agentic-dataset-factory create_coach does not check this today, so the rule is being introduced as a structural check at this feature's factory."
    human_response: "confirmed"

  - id: "ASSUM-010"
    scenario: "Ending a session produces a session-completed episode with topics, AOs, turns, and narrative; The session-end narrative summary stays within the prescribed sentence range"
    assumption: "Session-end narrative summary length is one to two sentences (both lengths acceptable)"
    confidence: medium
    basis: "Scope says 'a two-sentence narrative summary' — wording suggests two but does not forbid one. A tolerant 1–2 range avoids spurious revision loops on summary length."
    human_response: "confirmed"

  - id: "ASSUM-011"
    scenario: "A graceful shutdown drains in-flight Graphiti writes within the shutdown grace window"
    assumption: "Shutdown grace window for in-flight Graphiti writes is 5 seconds"
    confidence: low
    basis: "Not specified in FEAT-PH1-003 scope; TASK-GSM-004 references a drain() helper without naming a duration. 5s is a small finite window that bounds shutdown latency while letting most short writes complete."
    human_response: "confirmed"
Write deepagents-tutoring-loop_summary.md
86 lines
# Feature Spec Summary: DeepAgents Tutoring Loop with Coach

**Stack**: python
**Generated**: 2026-04-29
**Scenarios**: 39 total (5 smoke, 0 regression)
**Assumptions**: 11 total (5 high / 4 medium / 2 low confidence)
**Review required**: Yes (2 low-confidence assumptions remain — ASSUM-006, ASSUM-011)

## Scope

This specification covers FEAT-PH1-003: every learner-facing tutor turn passes through a Player-Coach loop where an evaluation-only Coach scores the Player's response against a six-criterion weighted rubric (curriculum accuracy, AO alignment, scaffolding depth, grade-appropriate language, constructive feedback, quote fidelity), accepts at-or-above the threshold, and otherwise drives a bounded Player revision cycle. It also covers session-end summary generation (topics, AOs, turn count, duration, narrative, misconceptions) and the fire-and-forget Graphiti write-back ownership at the three flush points (F1 Coach misconception writes, F2 planner topic-confidence updates, F3 session-end episode), with the `session.completed` event decoupled from Graphiti write success per DDR-003. Out of scope: Player prompt content, planner ranking logic (FEAT-PH1-002), retrieval/quote-verifier internals (FEAT-PH1-004), gamification consumers of `session.completed`.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 8 |
| Boundary conditions (@boundary) | 8 |
| Negative cases (@negative) | 7 |
| Edge cases (@edge-case) | 16 |
| Smoke (@smoke) | 5 |
| Regression (@regression) | 0 |

## Tag Footprint

| Tag | Count | Meaning |
|-----|-------|---------|
| `@coach-shape` | 8 | Structural Coach factory invariants (no tools, two-provider, etc.) |
| `@rubric` | 6 | Six-criterion weighted scoring |
| `@async` | 9 | Fire-and-forget Graphiti dispatch surface |
| `@quote-fidelity` | 5 | Integration with the source-typed quote verifier (FEAT-PH1-004) |
| `@revision-loop` | 6 | Player revision under Coach feedback |
| `@session-end` / `@summary` | 6 | F3 flush + narrative summary |
| `@misconception` | 4 | F1 flush — Coach-owned write per DDR-002 |
| `@events` | 3 | Shared Kernel B emit semantics per DDR-003 |
| `@security` | 4 | Prompt-injection / adversarial corpus / sanitisation |
| `@concurrency` | 4 | Two-session isolation, simultaneous dispatches, lifecycle race |
| `@invariant` | 5 | Hard architectural rules (D5, two-provider, never-learner-facing) |

## Task Tag Distribution (proposed)

| Task tag | Approx scenarios | Slice |
|----------|------------------|-------|
| `@task:TASK-DTL-001` | 9 | Coach factory + structural invariants (no-tools, empty-prompt, two-provider, adversarial-content) |
| `@task:TASK-DTL-002` | 10 | Coach rubric + quote-fidelity integration + verifier-failure path |
| `@task:TASK-DTL-003` | 12 | Player-Coach loop wiring, revision policy, latency, fallback, concurrency |
| `@task:TASK-DTL-004` | 6 | Async write helper + per-observation misconception writes + simultaneous dispatch + drain |
| `@task:TASK-DTL-005` | 8 | Session-end summary + F3 write + `session.completed` emit + lifecycle race |

`/feature-plan` Step 11 (`bdd-linker`) will refine this distribution against the actual subtasks it generates.

## Deferred Items

None. All proposed groups (A/B/C/D + edge-case expansion S/I/L) accepted.

## Open Assumptions (low confidence)

- **ASSUM-006** — Behaviour when Coach reasoning exceeds the 200-word cap (default: recorded in full but flagged for session-end review). The cap is stated; the behaviour at 201+ is inferred. Confirm with prompt-engineering review when the Coach prompt is finalised.
- **ASSUM-011** — Shutdown grace window for in-flight Graphiti writes (default: 5 seconds). Not stated in FEAT-PH1-003; the figure is a defensible default. Confirm against the shared write helper's planned `drain()` surface in TASK-GSM-004.

## Anchor Decisions Honoured

- **DDR-002** — Coach AsyncSubAgent owns its own misconception writes (F1). The Tutor handler dispatches F2 (planner topic-confidence) and F3 (session-end). Both go through a single shared Graphiti write helper.
- **DDR-003** — `session.completed` emits on the active→ended state transition, BEFORE the F3 Graphiti write task is scheduled. No `session.persisted` follow-up event. Sessions with zero tutor turns must not emit `session.completed` (I-T6).
- **CC-13 / ADR-ARCH-019** — Every Graphiti write site is fire-and-forget. Failures emit a structured-log line; they never raise into the caller-facing handler.
- **D5 (agentic-dataset-factory)** — Coach is `tools=[]`, no filesystem backend, never returns text to the learner. Construction-time checks enforce structurally rather than relying on prompt instructions.
- **Two-provider invariant** — Coach and Player must use different providers; enforced at Coach factory construction.

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "DeepAgents Tutoring Loop with Coach" \
      --context features/deepagents-tutoring-loop/deepagents-tutoring-loop_summary.md \
      --context features/deepagents-tutoring-loop/deepagents-tutoring-loop.feature \
      --context features/deepagents-tutoring-loop/deepagents-tutoring-loop_assumptions.yaml \
      --context docs/research/ideas/phase-1-scope.md \
      --context docs/research/ideas/phase-1-build-plan.md \
      --context docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md \
      --context docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md \
      --context docs/design/contracts/API-tutoring.md

`/feature-plan` Step 11 will run `bdd-linker` to map the 39 scenarios onto the
generated subtasks and replace the placeholder `@task:TASK-DTL-NNN` tags with
the real task IDs.
Bash Verify all 3 files written
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/deepagents-tutoring-loop/

OUT
total 88
drwxr-xr-x  5 richardwoollcott  staff    160 Apr 29 16:29 .
drwxr-xr-x  5 richardwoollcott  staff    160 Apr 29 16:26 ..
-rw-r--r--  1 richardwoollcott  staff   5427 Apr 29 16:28 deepagents-tutoring-loop_assumptions.yaml
-rw-r--r--  1 richardwoollcott  staff   5813 Apr 29 16:29 deepagents-tutoring-loop_summary.md
-rw-r--r--  1 richardwoollcott  staff  28270 Apr 29 16:28 deepagents-tutoring-loop.feature
All three files written. Summary below.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: DeepAgents Tutoring Loop with Coach
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
  features/deepagents-tutoring-loop/deepagents-tutoring-loop.feature
  features/deepagents-tutoring-loop/deepagents-tutoring-loop_assumptions.yaml
  features/deepagents-tutoring-loop/deepagents-tutoring-loop_summary.md

Scenarios: 39 total
  @key-example: 8     @boundary: 8
  @negative: 7        @edge-case: 16
  @smoke: 5           @regression: 0

Assumptions: 11 total
  high: 5 (auto-proceed)
  medium: 4 (Coach review recommended)
  low: 2 (human review required)

REVIEW REQUIRED: 2 low-confidence assumptions need verification
  - ASSUM-006: Coach reasoning behaviour beyond the 200-word cap
  - ASSUM-011: Shutdown grace window (5 seconds) for in-flight Graphiti writes
  See: features/deepagents-tutoring-loop/deepagents-tutoring-loop_assumptions.yaml

Deferred: 0 scenario groups

Anchor decisions honoured:
  DDR-002, DDR-003, CC-13 / ADR-ARCH-019, D5 (Coach evaluation-only),
  Two-provider invariant (enforced at construction)

Next steps:
  Review: features/deepagents-tutoring-loop/deepagents-tutoring-loop.feature
  Pass to feature-plan:
    /feature-plan "DeepAgents Tutoring Loop with Coach" \
      --context features/deepagents-tutoring-loop/deepagents-tutoring-loop_summary.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Note on @task: tags — I used placeholder IDs TASK-DTL-001..005 matching the natural slice boundaries (Coach factory, rubric+verifier, loop+revision, async writes, session-end). /feature-plan Step 11 (bdd-linker) will replace these with the real task IDs once the subtasks are generated.