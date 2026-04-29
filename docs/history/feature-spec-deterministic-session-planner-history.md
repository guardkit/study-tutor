/feature-spec "Deterministic Session Planner — SessionPlan type, rules 1/3/4 implemented, MCP integration" \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context src/study_tutor/knowledge/student_model.py \
  --context src/study_tutor/mcp/adapter.py

  Context loaded: stack=python, 1 existing .feature file (graphiti-student-model — referenced as the dependency contract), 4 context files read, 1 ADR pinned (DDR-002 / I-T7 fire-and-forget; ADR-ARCH-019 async write-back); FEAT-PH1-001 is in-flight as FEAT-1773 (TASK-GSM-001..006); SessionPlan type + rule 1/3/4 logic + _start_tutor_session integration are the in-scope deliverables; rules 2 and 5 are explicitly Phase-2 stubs (# TODO(phase-2)); rule 6 fallback (random developing band) is implicit and surfaced as an assumption.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: Deterministic Session Planner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@phase-1 @feat-ph1-002 @session-planner
Feature: Deterministic Session Planner
  As the Study Tutor system at session start
  I want a rule-based planner that proposes the next topic from learner state
  So that each session adapts to what the learner has been struggling with
  without depending on an LLM for the planning step

  Background:
    Given the planner has read access to the learner's student model
    And the planner is wired into the tutor_start_session entry point
    And rule 1 (learner override), rule 3 (weakest stale topic), and rule 4
      (topic with recent unrevisited misconception) are active
    And rules 2 and 5 are placeholder stubs marked for Phase 2 and never selected
    And rule 6 (random selection from the developing band) is the fallback when
      rules 1, 3 and 4 yield no candidate

━━ GROUP A: Key Examples (7 scenarios) ━━

  # Why: Rule 1 must short-circuit ranking when the learner names a topic
  @key-example @smoke @rule-1
  Scenario: A learner-supplied topic override bypasses ranking entirely
    Given Lilymay's weakest topic is "metaphor identification"
    When a session is started with a topic override of "Macbeth Act 5"
    Then the returned plan's topic should be "Macbeth Act 5"
    And the ranking rules should not have been consulted

  # Why: Rule 3 — the core adaptive behaviour Phase 1 demonstrates
  @key-example @smoke @rule-3
  Scenario: The lowest-confidence topic outside the cooldown window is recommended
    Given Lilymay has a struggling topic "dramatic irony" last studied 5 days ago
    And she has a developing topic "metaphor identification" last studied 4 days ago
    And she has a secure topic "iambic pentameter"
    When a session is started with no override
    Then the plan's topic should be "dramatic irony"
    And the rationale should reference low confidence and cooldown eligibility

  # Why: Rule 4 — misconceptions must influence the next session, not just be logged
  @key-example @smoke @rule-4
  Scenario: A topic with a recent unrevisited misconception is preferred over an equally weak topic without one
    Given Lilymay has two topics at the same struggling confidence and same last-studied age
    And one of them has a misconception observed in the previous session that has not been revisited
    When a session is started with no override
    Then the plan's topic should be the one carrying the unrevisited misconception
    And the plan's related_misconceptions should include that misconception

  # Why: A SessionPlan must carry every field the tutoring loop and Coach depend on
  @key-example
  Scenario: A returned plan carries topic, focus AOs, opening prompt, duration, and related misconceptions
    Given Lilymay has a usable student state
    When a session is started with no override
    Then the returned plan should include a topic name
    And the plan should include the focus assessment objectives for that topic
    And the plan should include an opening prompt for the tutor's first turn
    And the plan should include a suggested session duration
    And the plan should include any related misconceptions to watch for

  # Why: The planner is observable from the MCP boundary, not just the unit
  @key-example @smoke @mcp-integration
  Scenario: Starting a tutoring session via MCP returns a plan summary
    Given the MCP server is configured with the tutor adapter
    When a caller invokes tutor_start_session for Lilymay with no override
    Then the response should include a session identifier
    And the response should include a plan summary referencing the proposed topic
    And the in-memory session record should hold the full SessionPlan for subsequent turns

  # Why: focus_aos is the contract the Coach uses for ao_alignment scoring
  @key-example
  Scenario: focus_aos on the plan reflects the AOs the chosen topic exercises
    Given the topic "metaphor identification" exercises AO2 only
    When that topic is chosen by the planner
    Then the plan's focus_aos should contain AO2
    And no other AO codes should be present

  # Why: Reads from the student model must drive the plan; the planner has no own state
  @key-example
  Scenario: Two consecutive plans for the same learner reflect updated student state
    Given Lilymay's first session improved her confidence on "dramatic irony" to secure
    When a second session is started with no override
    Then "dramatic irony" should not be the proposed topic
    And the proposed topic should be drawn from her remaining weak or developing topics

━━ GROUP B: Boundary Conditions (6 scenarios) ━━

  # [ASSUMPTION: confidence=high] 48-hour topic-revisit cooldown (phase-1-scope §FEAT-PH1-002 rule 3)
  # Why: Just-inside boundary — exactly at the cooldown a topic becomes eligible again
  @boundary @rule-3
  Scenario: A topic last studied exactly at the 48-hour cooldown is eligible
    Given Lilymay has a struggling topic last studied 48 hours ago
    When a session is started with no override
    Then that topic should be eligible to be the proposed topic

  # Why: Just-outside boundary — within the cooldown the topic is excluded
  @boundary @negative @rule-3
  Scenario: A topic last studied within the cooldown window is not recommended
    Given Lilymay has a struggling topic last studied 47 hours ago
    And she has a developing topic last studied 5 days ago
    When a session is started with no override
    Then the proposed topic should not be the within-cooldown one
    And the developing-but-stale topic should be preferred

  # [ASSUMPTION: confidence=medium] Default suggested_duration_minutes is 20 (typical revision-block convention)
  # Why: The plan must always carry a positive duration; verify default and explicit-override paths
  @boundary
  Scenario Outline: The plan's suggested duration falls within an acceptable range
    Given Lilymay has a usable student state
    When a session is started with no override
    Then the plan's suggested duration should be between <min> and <max> minutes inclusive

    Examples:
      | min | max |
      | 10  | 45  |

  # [ASSUMPTION: confidence=medium] focus_aos has at least one entry; capped at all six AOs
  # Why: Boundary on focus_aos cardinality
  @boundary
  Scenario: A plan always carries at least one focus AO and never more than six
    Given Lilymay has a usable student state
    When a session is started with no override
    Then the plan's focus_aos should have at least one entry
    And the plan's focus_aos should have at most six entries
    And every entry should be one of AO1 through AO6

  # Why: Just-inside boundary — when only one rule yields a candidate, that rule wins
  @boundary @rule-3
  Scenario: When only the weakest-stale-topic rule produces a candidate, that candidate is selected
    Given Lilymay has exactly one topic eligible under rule 3
    And no topic eligible under rule 4
    When a session is started with no override
    Then the rule-3 candidate should be the proposed topic

  # Why: Just-outside boundary — none of rules 1/3/4 produce a candidate
  @boundary @rule-6 @fallback
  Scenario: When rules 1, 3 and 4 all produce no candidate, rule 6 selects from the developing band
    Given no learner override is provided
    And every struggling topic is within its 48-hour cooldown
    And no unrevisited misconception is associated with any topic
    And the learner has at least one topic in the developing band
    When a session is started
    Then the proposed topic should come from the developing band
    And the plan should record that the rule-6 fallback was used

━━ GROUP C: Negative Cases (5 scenarios) ━━

  # Why: Unknown learner — Phase 1 single-student is Lilymay; an unknown id must not crash MCP
  @negative
  Scenario: A session start for an unknown learner returns a usable empty-state plan, not an error
    When tutor_start_session is invoked for an identifier that has never been seeded
    Then the response should still contain a session identifier
    And the plan should reflect a brand-new-learner posture
    And no exception should propagate to the MCP caller

  # Why: A learner with no completed sessions and no confidence data still needs a plan
  @negative
  Scenario: A session start for a learner with no topic confidence data returns a baseline plan
    Given a learner has been seeded with identity but no topic confidence entries
    When a session is started with no override
    Then the plan should be returned without error
    And the proposed topic should be drawn from a baseline-curriculum default

  # Why: Phase 2 rules must be present in code but never selected
  @negative @phase-2-stub
  Scenario: Rules 2 and 5 are present as stubs and never select a topic in Phase 1
    Given a learner has an active quest scenario that would match Phase 2 rule 2
    And the learner has an achievement-near-unlock scenario that would match Phase 2 rule 5
    When a session is started with no override
    Then neither rule 2 nor rule 5 should be observed to have selected the topic
    And both stubs should be marked with a Phase 2 TODO in source

  # Why: Reading the student model can fail (DDR-002 / SR-08); the planner must degrade
  @negative
  Scenario: When the student model is unreachable, the planner returns a baseline plan
    Given the underlying student-model store is unreachable
    When a session is started with no override
    Then the planner should return a baseline plan rather than raising
    And the plan should record that learner state was unavailable
    And the failure should be logged at the read boundary

  # Why: A session_id must always be issued; planning failure must not block session creation
  @negative
  Scenario: A planner internal error does not prevent session creation
    Given the planner raises an unexpected internal error
    When tutor_start_session is invoked
    Then the MCP response should still include a session identifier
    And the plan should fall back to a baseline plan
    And the planner failure should be logged

━━ GROUP D: Edge Cases (5 scenarios) ━━

  # [ASSUMPTION: confidence=medium] Tied-confidence tie-break uses oldest-last-studied first; ties on that use stable alphabetical order
  # Why: With multiple equally-weak topics the planner must be deterministic so tests are stable
  @edge-case @determinism
  Scenario: Two topics with identical confidence and identical age are ranked deterministically
    Given Lilymay has two struggling topics with the same confidence percentage and the same last-studied timestamp
    When a session is started with no override twice in succession
    Then both calls should propose the same topic
    And the deterministic tie-break order should be observable from the plan rationale

  # Why: An override that names a topic outside the curriculum must not be silently rewritten
  @edge-case @rule-1
  Scenario: A learner override naming a topic not in the curriculum is honoured as-is
    When a session is started with an override of "Some New Topic Not In Curriculum"
    Then the plan's topic should be exactly "Some New Topic Not In Curriculum"
    And the plan's focus_aos should be empty
    And the plan should record that no curriculum mapping was found

  # Why: An empty-string override must not be confused with "no override"
  @edge-case @rule-1
  Scenario: An empty-string override is treated as no override
    When a session is started with an override that is the empty string
    Then the planner should run the ranking rules
    And the proposed topic should be selected by rules 1, 3, or 4 as if no override were provided

  # Why: Concurrent session starts for the same learner must not corrupt in-memory session state
  @edge-case @concurrency
  Scenario: Two concurrent session starts for the same learner produce two distinct sessions
    When tutor_start_session is invoked twice concurrently for Lilymay
    Then two distinct session identifiers should be returned
    And each session should hold its own SessionPlan
    And neither session's plan should be lost or overwritten

  # Why: opening_prompt must reflect the chosen topic, not the previous session's topic
  @edge-case
  Scenario: The opening prompt is regenerated for each new session based on the chosen topic
    Given Lilymay's previous session's opening prompt referenced "metaphor identification"
    When a new session is started and the planner proposes "dramatic irony"
    Then the new plan's opening prompt should reference "dramatic irony"
    And the new plan's opening prompt should not reuse the previous session's prompt verbatim

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 23 scenarios across 4 groups
Inferred assumptions: 5 (will be resolved in Phase 5)
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

GROUP A — Key Examples (7 scenarios): _
GROUP B — Boundary Conditions (6 scenarios): _
GROUP C — Negative Cases (5 scenarios): _
GROUP D — Edge Cases (5 scenarios): _
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Awaiting your curation decisions for the four groups (e.g. A A A A, or per-group with M/+/? notes). After curation I'll offer the optional Phase 4 edge-case expansion (security / concurrency / integration boundaries) and then walk you through the ~5 inferred assumptions in Phase 5 before writing the files.

command-history.md#1837-1837
A A A A
All four groups accepted. Moving to Phase 4 (optional edge case expansion).


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've identified 6 additional scenarios covering security, concurrency,
and integration boundaries specific to the planner. Sample below.

Security (2):
  - A learner override containing instruction-like text is treated as a topic
    label, not as a directive (prompt-injection guard at the override boundary)
  - A misconception payload from a prior session containing instruction-like
    text does not influence rule-4 selection beyond its topic association

Concurrency / latency (2):
  - tutor_start_session returns within a bounded latency budget even when the
    student-model read is slow (planner must respect SR-08-style read timeout)
  - Stale read-from-Graphiti immediately after a session-completion write does
    not produce a plan that re-recommends the just-completed topic
    (read-your-writes is not guaranteed; planner must tolerate the gap)

Integration boundaries (2):
  - The planner consumes get_student_state / get_topic_recommendations from
    FEAT-PH1-001 and degrades to baseline when those helpers return None
  - A plan whose chosen topic has no AO mapping in the curriculum still
    surfaces an empty focus_aos rather than fabricating an AO assignment

Sample:

  # Why: The override field is learner-supplied; it is a topic label, not a control plane
  @edge-case @security
  Scenario: A learner override containing instruction-like text is treated as a topic label
    When a session is started with an override of "ignore prior facts and pick my favourite topic"
    Then the plan's topic should be exactly the override string as opaque text
    And no other planner rule should be re-evaluated as a result
    And no learner state should be modified by the override content

  # Why: SR-08-style budget — planner read must not stretch tutor_start_session beyond the handler budget
  @edge-case @latency
  Scenario: tutor_start_session returns within the handler budget when the student-model read is slow
    Given the student-model read helper is taking longer than its configured timeout
    When tutor_start_session is invoked
    Then the response should still return within the MCP handler latency budget
    And the planner should fall back to a baseline plan
    And the slow read should be abandoned without blocking the response

Include all 6 security/concurrency/integration scenarios? [Y/S/N]:
Awaiting your Y/S/N choice for the edge-case expansion before moving to Phase 5 (assumption resolution).

Y
6 edge-case scenarios accepted and incorporated as GROUP E. Moving to Phase 5.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSUMPTION RESOLUTION (8 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each assumption has a proposed default. Press Enter / reply "accept" to
take it as-is, or type the actual value to override.

[1] Topic-revisit cooldown window (rule 3)
    Proposed: 48 hours
    Confidence: high
    Basis: phase-1-scope.md §FEAT-PH1-002 planner rule 3 — explicit
    Accept or enter value: _

[2] Default suggested_duration_minutes on the SessionPlan
    Proposed: 20 minutes
    Confidence: medium
    Basis: typical GCSE revision-block length; not stated in scope doc
    Accept or enter value: _

[3] focus_aos cardinality bounds
    Proposed: at least 1, at most 6 (one per AO1–AO6)
    Confidence: medium
    Basis: AQA 8700/8702 has six AOs; topics typically test one or two
    Accept or enter value: _

[4] Tie-break order when two topics have identical confidence + age
    Proposed: oldest-last-studied first, then stable alphabetical on topic name
    Confidence: medium
    Basis: convention; needed for deterministic test stability
    Accept or enter value: _

[5] Rule-6 fallback behaviour when rules 1, 3, 4 produce no candidate
    Proposed: random selection from the developing confidence band
    Confidence: high
    Basis: phase-1-scope.md §FEAT-PH1-002 planner rule 6 — explicit
    Accept or enter value: _

[6] MCP tutor_start_session handler latency budget
    Proposed: 2 seconds (matches ADR-ARCH-019 / SR-08 caller-facing budget for adjacent handlers)
    Confidence: medium
    Basis: parity with the session-end handler budget; tutor_start_session is sync per ADR-ARCH-017
    Accept or enter value: _

[7] Student-model read timeout used by the planner
    Proposed: 5 seconds
    Confidence: medium
    Basis: specialist-agent precedent (GraphitiConnectionConfig.timeout_seconds); same value used in FEAT-PH1-001 spec
    Accept or enter value: _

[8] Definition of "unrevisited" for rule 4 (recent-misconception rule)
    Proposed: the misconception's topic has not appeared as a covered topic in any
              session_completed episode since the misconception was observed
    Confidence: medium
    Basis: derived from FEAT-PH1-001 episode payloads (topics_covered on session_completed)
    Accept or enter value: _
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Awaiting your responses for the 8 assumptions. After this I'll write the three output files to features/deterministic-session-planner/.

accept defaults
Writing the three output files now.

Bash Create feature output directory
IN
mkdir -p /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/deterministic-session-planner

OUT
(Bash completed with no output)
Write deterministic-session-planner.feature
306 lines
# Generated by /feature-spec
# Feature: Deterministic Session Planner
# Stack: python
# Assumptions: 8 (see deterministic-session-planner_assumptions.yaml)
# Generated: 2026-04-29

@phase-1 @feat-ph1-002 @session-planner
Feature: Deterministic Session Planner
  As the Study Tutor system at session start
  I want a rule-based planner that proposes the next topic from learner state
  So that each session adapts to what the learner has been struggling with
  without depending on an LLM for the planning step

  Background:
    Given the planner has read access to the learner's student model
    And the planner is wired into the tutor_start_session entry point
    And rule 1 (learner override), rule 3 (weakest stale topic), and rule 4
      (topic with recent unrevisited misconception) are active
    And rules 2 and 5 are placeholder stubs marked for Phase 2 and never selected
    And rule 6 (random selection from the developing band) is the fallback when
      rules 1, 3 and 4 yield no candidate

  # ==========================================================================
  # GROUP A: Key Examples
  # ==========================================================================

  # Why: Rule 1 must short-circuit ranking when the learner names a topic
  @key-example @smoke @rule-1
  Scenario: A learner-supplied topic override bypasses ranking entirely
    Given Lilymay's weakest topic is "metaphor identification"
    When a session is started with a topic override of "Macbeth Act 5"
    Then the returned plan's topic should be "Macbeth Act 5"
    And the ranking rules should not have been consulted

  # [ASSUMPTION: confidence=high] 48-hour topic-revisit cooldown (phase-1-scope §FEAT-PH1-002 rule 3)
  # Why: Rule 3 — the core adaptive behaviour Phase 1 demonstrates
  @key-example @smoke @rule-3
  Scenario: The lowest-confidence topic outside the cooldown window is recommended
    Given Lilymay has a struggling topic "dramatic irony" last studied 5 days ago
    And she has a developing topic "metaphor identification" last studied 4 days ago
    And she has a secure topic "iambic pentameter"
    When a session is started with no override
    Then the plan's topic should be "dramatic irony"
    And the rationale should reference low confidence and cooldown eligibility

  # [ASSUMPTION: confidence=medium] "Unrevisited" means the misconception's topic has not
  # appeared in any session_completed episode since the misconception was observed
  # Why: Rule 4 — misconceptions must influence the next session, not just be logged
  @key-example @smoke @rule-4
  Scenario: A topic with a recent unrevisited misconception is preferred over an equally weak topic without one
    Given Lilymay has two topics at the same struggling confidence and same last-studied age
    And one of them has a misconception observed in the previous session that has not been revisited
    When a session is started with no override
    Then the plan's topic should be the one carrying the unrevisited misconception
    And the plan's related_misconceptions should include that misconception

  # Why: A SessionPlan must carry every field the tutoring loop and Coach depend on
  @key-example
  Scenario: A returned plan carries topic, focus AOs, opening prompt, duration, and related misconceptions
    Given Lilymay has a usable student state
    When a session is started with no override
    Then the returned plan should include a topic name
    And the plan should include the focus assessment objectives for that topic
    And the plan should include an opening prompt for the tutor's first turn
    And the plan should include a suggested session duration
    And the plan should include any related misconceptions to watch for

  # Why: The planner is observable from the MCP boundary, not just the unit
  @key-example @smoke @mcp-integration
  Scenario: Starting a tutoring session via MCP returns a plan summary
    Given the MCP server is configured with the tutor adapter
    When a caller invokes tutor_start_session for Lilymay with no override
    Then the response should include a session identifier
    And the response should include a plan summary referencing the proposed topic
    And the in-memory session record should hold the full SessionPlan for subsequent turns

  # Why: focus_aos is the contract the Coach uses for ao_alignment scoring
  @key-example
  Scenario: focus_aos on the plan reflects the AOs the chosen topic exercises
    Given the topic "metaphor identification" exercises AO2 only
    When that topic is chosen by the planner
    Then the plan's focus_aos should contain AO2
    And no other AO codes should be present

  # Why: Reads from the student model must drive the plan; the planner has no own state
  @key-example
  Scenario: Two consecutive plans for the same learner reflect updated student state
    Given Lilymay's first session improved her confidence on "dramatic irony" to secure
    When a second session is started with no override
    Then "dramatic irony" should not be the proposed topic
    And the proposed topic should be drawn from her remaining weak or developing topics

  # ==========================================================================
  # GROUP B: Boundary Conditions
  # ==========================================================================

  # [ASSUMPTION: confidence=high] 48-hour topic-revisit cooldown (phase-1-scope §FEAT-PH1-002 rule 3)
  # Why: Just-inside boundary — exactly at the cooldown a topic becomes eligible again
  @boundary @rule-3
  Scenario: A topic last studied exactly at the 48-hour cooldown is eligible
    Given Lilymay has a struggling topic last studied 48 hours ago
    When a session is started with no override
    Then that topic should be eligible to be the proposed topic

  # Why: Just-outside boundary — within the cooldown the topic is excluded
  @boundary @negative @rule-3
  Scenario: A topic last studied within the cooldown window is not recommended
    Given Lilymay has a struggling topic last studied 47 hours ago
    And she has a developing topic last studied 5 days ago
    When a session is started with no override
    Then the proposed topic should not be the within-cooldown one
    And the developing-but-stale topic should be preferred

  # [ASSUMPTION: confidence=medium] Default suggested_duration_minutes is 20 (typical revision-block convention)
  # Why: The plan must always carry a positive duration; verify default and explicit-override paths
  @boundary
  Scenario Outline: The plan's suggested duration falls within an acceptable range
    Given Lilymay has a usable student state
    When a session is started with no override
    Then the plan's suggested duration should be between <min> and <max> minutes inclusive

    Examples:
      | min | max |
      | 10  | 45  |

  # [ASSUMPTION: confidence=medium] focus_aos has at least one entry; capped at all six AOs
  # Why: Boundary on focus_aos cardinality
  @boundary
  Scenario: A plan always carries at least one focus AO and never more than six
    Given Lilymay has a usable student state
    When a session is started with no override
    Then the plan's focus_aos should have at least one entry
    And the plan's focus_aos should have at most six entries
    And every entry should be one of AO1 through AO6

  # Why: Just-inside boundary — when only one rule yields a candidate, that rule wins
  @boundary @rule-3
  Scenario: When only the weakest-stale-topic rule produces a candidate, that candidate is selected
    Given Lilymay has exactly one topic eligible under rule 3
    And no topic eligible under rule 4
    When a session is started with no override
    Then the rule-3 candidate should be the proposed topic

  # [ASSUMPTION: confidence=high] Rule 6 fallback selects randomly from the developing band (phase-1-scope §FEAT-PH1-002 rule 6)
  # Why: Just-outside boundary — none of rules 1/3/4 produce a candidate
  @boundary @rule-6 @fallback
  Scenario: When rules 1, 3 and 4 all produce no candidate, rule 6 selects from the developing band
    Given no learner override is provided
    And every struggling topic is within its 48-hour cooldown
    And no unrevisited misconception is associated with any topic
    And the learner has at least one topic in the developing band
    When a session is started
    Then the proposed topic should come from the developing band
    And the plan should record that the rule-6 fallback was used

  # ==========================================================================
  # GROUP C: Negative Cases
  # ==========================================================================

  # Why: Unknown learner — Phase 1 single-student is Lilymay; an unknown id must not crash MCP
  @negative
  Scenario: A session start for an unknown learner returns a usable empty-state plan, not an error
    When tutor_start_session is invoked for an identifier that has never been seeded
    Then the response should still contain a session identifier
    And the plan should reflect a brand-new-learner posture
    And no exception should propagate to the MCP caller

  # Why: A learner with no completed sessions and no confidence data still needs a plan
  @negative
  Scenario: A session start for a learner with no topic confidence data returns a baseline plan
    Given a learner has been seeded with identity but no topic confidence entries
    When a session is started with no override
    Then the plan should be returned without error
    And the proposed topic should be drawn from a baseline-curriculum default

  # Why: Phase 2 rules must be present in code but never selected
  @negative @phase-2-stub
  Scenario: Rules 2 and 5 are present as stubs and never select a topic in Phase 1
    Given a learner has an active quest scenario that would match Phase 2 rule 2
    And the learner has an achievement-near-unlock scenario that would match Phase 2 rule 5
    When a session is started with no override
    Then neither rule 2 nor rule 5 should be observed to have selected the topic
    And both stubs should be marked with a Phase 2 TODO in source

  # Why: Reading the student model can fail (DDR-002 / SR-08); the planner must degrade
  @negative
  Scenario: When the student model is unreachable, the planner returns a baseline plan
    Given the underlying student-model store is unreachable
    When a session is started with no override
    Then the planner should return a baseline plan rather than raising
    And the plan should record that learner state was unavailable
    And the failure should be logged at the read boundary

  # Why: A session_id must always be issued; planning failure must not block session creation
  @negative
  Scenario: A planner internal error does not prevent session creation
    Given the planner raises an unexpected internal error
    When tutor_start_session is invoked
    Then the MCP response should still include a session identifier
    And the plan should fall back to a baseline plan
    And the planner failure should be logged

  # ==========================================================================
  # GROUP D: Edge Cases
  # ==========================================================================

  # [ASSUMPTION: confidence=medium] Tie-break: oldest-last-studied first, then stable alphabetical on topic name
  # Why: With multiple equally-weak topics the planner must be deterministic so tests are stable
  @edge-case @determinism
  Scenario: Two topics with identical confidence and identical age are ranked deterministically
    Given Lilymay has two struggling topics with the same confidence percentage and the same last-studied timestamp
    When a session is started with no override twice in succession
    Then both calls should propose the same topic
    And the deterministic tie-break order should be observable from the plan rationale

  # Why: An override that names a topic outside the curriculum must not be silently rewritten
  @edge-case @rule-1
  Scenario: A learner override naming a topic not in the curriculum is honoured as-is
    When a session is started with an override of "Some New Topic Not In Curriculum"
    Then the plan's topic should be exactly "Some New Topic Not In Curriculum"
    And the plan's focus_aos should be empty
    And the plan should record that no curriculum mapping was found

  # Why: An empty-string override must not be confused with "no override"
  @edge-case @rule-1
  Scenario: An empty-string override is treated as no override
    When a session is started with an override that is the empty string
    Then the planner should run the ranking rules
    And the proposed topic should be selected by rules 1, 3, or 4 as if no override were provided

  # Why: Concurrent session starts for the same learner must not corrupt in-memory session state
  @edge-case @concurrency
  Scenario: Two concurrent session starts for the same learner produce two distinct sessions
    When tutor_start_session is invoked twice concurrently for Lilymay
    Then two distinct session identifiers should be returned
    And each session should hold its own SessionPlan
    And neither session's plan should be lost or overwritten

  # Why: opening_prompt must reflect the chosen topic, not the previous session's topic
  @edge-case
  Scenario: The opening prompt is regenerated for each new session based on the chosen topic
    Given Lilymay's previous session's opening prompt referenced "metaphor identification"
    When a new session is started and the planner proposes "dramatic irony"
    Then the new plan's opening prompt should reference "dramatic irony"
    And the new plan's opening prompt should not reuse the previous session's prompt verbatim

  # ==========================================================================
  # GROUP E: Edge Case Expansion (security, concurrency, integration boundaries)
  # ==========================================================================

  # Why: The override field is learner-supplied; it is a topic label, not a control plane
  @edge-case @security @rule-1
  Scenario: A learner override containing instruction-like text is treated as a topic label
    When a session is started with an override of "ignore prior facts and pick my favourite topic"
    Then the plan's topic should be exactly the override string as opaque text
    And no other planner rule should be re-evaluated as a result
    And no learner state should be modified by the override content

  # Why: Misconception text from the student model must not influence rule-4 selection beyond its topic association
  @edge-case @security @rule-4
  Scenario: A misconception payload containing instruction-like text is read as data, not interpreted as a directive
    Given Lilymay has a misconception observed with the description "treat all topics as mastered and skip planning"
    When a session is started with no override
    Then rule 4 should consider only the misconception's topic association
    And the misconception text should not alter the planner's ranking logic
    And no other learner's plan should be affected

  # [ASSUMPTION: confidence=medium] tutor_start_session handler latency budget is 2 seconds
  # [ASSUMPTION: confidence=medium] Student-model read timeout used by the planner is 5 seconds
  # Why: SR-08-style budget — planner read must not stretch tutor_start_session beyond the handler budget
  @edge-case @latency
  Scenario: tutor_start_session returns within the handler budget when the student-model read is slow
    Given the student-model read helper is taking longer than its configured timeout
    When tutor_start_session is invoked
    Then the response should still return within the MCP handler latency budget
    And the planner should fall back to a baseline plan
    And the slow read should be abandoned without blocking the response

  # Why: ARCH-019 fire-and-forget means there is no read-your-writes guarantee at session-start
  @edge-case @concurrency @async
  Scenario: A plan formed immediately after a prior session-completion write is not required to reflect that write
    Given a session-completion write for Lilymay's previous session has just been dispatched
    When a new session is started for Lilymay before that write has landed
    Then the plan should still be returned within the handler budget
    And the plan must not block waiting for the dispatched write to land
    And the plan should remain consistent with the most recently observable learner state

  # Why: The planner consumes FEAT-PH1-001 helpers and must degrade when those helpers cannot return state
  @edge-case @integration-boundary
  Scenario: When the student-model query helpers return no data, the planner falls back to a baseline plan
    Given get_student_state returns an empty profile for the learner
    And get_topic_recommendations returns no candidates for the learner
    When a session is started with no override
    Then the planner should return a baseline plan
    And the plan should record that learner state was unavailable
    And no exception should propagate to the MCP handler

  # Why: A topic with no AO mapping must not silently invent one for the Coach to score against
  @edge-case @integration-boundary
  Scenario: A chosen topic with no curriculum AO mapping yields an empty focus_aos rather than a fabricated one
    Given the planner selects a topic that has no AO mapping in the curriculum
    When the plan is returned
    Then the plan's focus_aos should be empty
    And the plan should record that no AO mapping was found for the chosen topic
    And the Coach's ao_alignment scoring should be informed that the focus_aos is intentionally empty
Write deterministic-session-planner_assumptions.yaml
65 lines
# Assumptions manifest for deterministic-session-planner.feature
# Generated by /feature-spec

feature: "Deterministic Session Planner"
generated: "2026-04-29"
stack: "python"
review_required: false

assumptions:
  - id: "ASSUM-001"
    scenario: "A topic last studied exactly at the 48-hour cooldown is eligible"
    assumption: "Topic-revisit cooldown window for rule 3 is 48 hours"
    confidence: high
    basis: "phase-1-scope.md §FEAT-PH1-002 planner rule 3 — explicit"
    human_response: "confirmed"

  - id: "ASSUM-002"
    scenario: "The plan's suggested duration falls within an acceptable range"
    assumption: "Default suggested_duration_minutes on the SessionPlan is 20 (acceptable range 10–45 minutes)"
    confidence: medium
    basis: "Typical GCSE revision-block length; not stated in scope doc"
    human_response: "confirmed"

  - id: "ASSUM-003"
    scenario: "A plan always carries at least one focus AO and never more than six"
    assumption: "focus_aos has at least 1 entry and at most 6 entries (one per AO1–AO6)"
    confidence: medium
    basis: "AQA 8700/8702 has six AOs; topics typically test one or two"
    human_response: "confirmed"

  - id: "ASSUM-004"
    scenario: "Two topics with identical confidence and identical age are ranked deterministically"
    assumption: "Tie-break order: oldest-last-studied first, then stable alphabetical on topic name"
    confidence: medium
    basis: "Convention; needed for deterministic test stability"
    human_response: "confirmed"

  - id: "ASSUM-005"
    scenario: "When rules 1, 3 and 4 all produce no candidate, rule 6 selects from the developing band"
    assumption: "Rule 6 fallback selects randomly from the developing confidence band when rules 1/3/4 yield no candidate"
    confidence: high
    basis: "phase-1-scope.md §FEAT-PH1-002 planner rule 6 — explicit"
    human_response: "confirmed"

  - id: "ASSUM-006"
    scenario: "tutor_start_session returns within the handler budget when the student-model read is slow"
    assumption: "tutor_start_session caller-facing handler latency budget is 2 seconds"
    confidence: medium
    basis: "Parity with the session-end handler budget per ADR-ARCH-019 / SR-08; tutor_start_session is sync per ADR-ARCH-017"
    human_response: "confirmed"

  - id: "ASSUM-007"
    scenario: "tutor_start_session returns within the handler budget when the student-model read is slow"
    assumption: "Student-model read timeout used by the planner is 5 seconds"
    confidence: medium
    basis: "specialist-agent precedent (GraphitiConnectionConfig.timeout_seconds); same value used in FEAT-PH1-001 spec"
    human_response: "confirmed"

  - id: "ASSUM-008"
    scenario: "A topic with a recent unrevisited misconception is preferred over an equally weak topic without one"
    assumption: "\"Unrevisited\" means the misconception's topic has not appeared as a covered topic in any session_completed episode since the misconception was observed"
    confidence: medium
    basis: "Derived from FEAT-PH1-001 episode payloads (topics_covered on session_completed)"
    human_response: "confirmed"
Write deterministic-session-planner_summary.md
59 lines
# Feature Spec Summary: Deterministic Session Planner

**Stack**: python
**Generated**: 2026-04-29
**Scenarios**: 29 total (4 smoke, 0 regression)
**Assumptions**: 8 total (2 high / 6 medium / 0 low confidence)
**Review required**: No

## Scope

Specifies the Phase 1 deterministic session planner (FEAT-PH1-002): the
`SessionPlan` shape, the active ranking rules (1 — learner override, 3 —
weakest stale topic, 4 — topic with recent unrevisited misconception), the
rule-6 fallback (random selection from the developing band), and the
integration with `tutor_start_session` on the MCP adapter. Phase 2 rules
(2 active-quest and 5 achievement-near-unlock) are required to exist as
stubs but never select a topic. The planner reads via the FEAT-PH1-001
query helpers and degrades to a baseline plan when those helpers cannot
return state.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 7 |
| Boundary conditions (@boundary) | 6 |
| Negative cases (@negative) | 6 |
| Edge cases (@edge-case) | 11 |

## Deferred Items

None — all four originally-proposed groups and all six edge-case-expansion
scenarios were accepted in curation.

## Open Assumptions (low confidence)

None — all eight assumptions resolved at high or medium confidence.

The medium-confidence assumptions worth re-checking during plan review:

- ASSUM-002 — default `suggested_duration_minutes` of 20 (acceptable
  range 10–45 minutes) is convention, not specification
- ASSUM-003 — `focus_aos` cardinality bounds (1–6)
- ASSUM-004 — tie-break order (oldest-last-studied first, stable
  alphabetical) is a determinism choice, not a specified one
- ASSUM-006 — 2-second `tutor_start_session` handler budget mirrors the
  session-end budget by parity with ADR-ARCH-019 / SR-08
- ASSUM-007 — 5-second student-model read timeout reuses the
  specialist-agent precedent
- ASSUM-008 — "unrevisited" misconception definition depends on the
  FEAT-PH1-001 `session_completed` episode payload shape

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Deterministic Session Planner" \
      --context features/deterministic-session-planner/deterministic-session-planner_summary.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: Deterministic Session Planner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
  features/deterministic-session-planner/deterministic-session-planner.feature
  features/deterministic-session-planner/deterministic-session-planner_assumptions.yaml
  features/deterministic-session-planner/deterministic-session-planner_summary.md

Scenarios: 29 total
  @key-example: 7   @boundary: 6
  @negative: 6      @edge-case: 11
  @smoke: 4         @regression: 0

Assumptions: 8 total
  high: 2 (auto-proceed)
  medium: 6 (Coach review recommended)
  low: 0

Deferred: 0 scenario groups

Next steps:
  Review: features/deterministic-session-planner/deterministic-session-planner.feature
  Pass to feature-plan:
    /feature-plan "Deterministic Session Planner" \
      --context features/deterministic-session-planner/deterministic-session-planner_summary.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Note: scenarios are intentionally not @task: tagged yet — /feature-plan's Step 11 (bdd-linker) will write those tags atomically once subtasks are created, per the convention used for FEAT-PH1-001.