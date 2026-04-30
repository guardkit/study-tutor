---
id: TASK-DSP-004
title: Rule 4 (unrevisited misconception) and Rule 2/5 stubs
task_type: feature
parent_review: TASK-REV-DA72
feature_id: FEAT-PH1-002
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-DSP-002
estimated_minutes: 90
priority: high
tags:
- phase-1
- planner
- rule-4
- misconception
- phase-2-stub
consumer_context:
- task: TASK-GSM-002
  consumes: SessionCompletedEpisode.topics_covered
  framework: Pydantic v2 Episode model (FEAT-PH1-001 graphiti-student-model)
  driver: graphiti-core via study_tutor.graphiti_client
  format_note: 'list[str] of topic name strings matching Topic.name from the student
    model schema. Signed off 2026-04-29 (ASSUM-008): TASK-GSM-002 implements this
    field. Cross-feature contract locked.

    '
status: in_review
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-PH1-002
  base_branch: main
  started_at: '2026-04-29T20:29:19.583384'
  last_updated: '2026-04-29T21:17:39.484297'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Advisory (non-blocking): task-work produced a report with 2 of 3
      expected agent invocations. Missing phases: 3 (Implementation). Consider invoking
      these agents via the Task tool to strengthen stack-specific quality:

      - Phase 3: `the stack-specific Phase-3 specialist` (Implementation)

      - BDD oracle: 1 scenario(s) failed during pytest-bdd execution. Implementation
      does not satisfy the Gherkin specification.'
    timestamp: '2026-04-29T20:29:19.583384'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-04-29T21:02:43.606024'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Rule 4 (unrevisited misconception) and Rule 2/5 stubs

## Description

Implement Rule 4 — the misconception-driven ranker — and lay down
the contract-faithful stubs for Phase 2 rules 2 and 5.

**Rule 4** prefers a topic carrying an unrevisited misconception when
two topics tie on confidence and last-studied age. "Unrevisited" is
fully defined per ASSUM-008 (signed off 2026-04-29): a misconception M
is unrevisited iff its `topic_ref` does NOT appear in
`SessionCompletedEpisode.topics_covered` of any session-completed
episode whose `completed_at` is later than M's `observed_at`.

**Rule 2 stub** (active-quest) and **Rule 5 stub**
(achievement-near-unlock) must conform to the `Rule` protocol from
TASK-DSP-002, return `None` unconditionally, and carry an explicit
`# TODO(phase-2)` source comment that test-asserts the deferral.

## Scope

- `Rule4UnrevisitedMisconception(clock)`:
  - For each topic in `ctx.topic_confidences`, determine whether any
    misconception linked to that topic is "unrevisited" per ASSUM-008.
  - Filter to topics with at least one unrevisited misconception.
  - If multiple candidates remain, apply the same tie-break as Rule 3
    (lowest confidence, oldest last-revised, stable alphabetical).
  - Returns `Candidate(topic_name=top, rule_source="rule-4",
    confidence_percentage=top.confidence_percentage,
    related_misconceptions=[m.misconception_id for m in unrevisited],
    rationale_fragment=...)`.
  - Returns `None` if no topic has any unrevisited misconception.
  - Misconception **text** is read as opaque data (`@security @rule-4`)
    — only `topic_ref` and `observed_at` participate in ranking.

- `Rule2ActiveQuestStub`:
  - Class body: `def __call__(self, ctx): return None  # TODO(phase-2)`
  - Returns `None` for any `PlannerContext`.

- `Rule5AchievementNearUnlockStub`:
  - Class body: `def __call__(self, ctx): return None  # TODO(phase-2)`
  - Returns `None` for any `PlannerContext`.

## Acceptance Criteria

- [ ] `Rule4` selects a topic carrying an unrevisited misconception
      over an equally-weak topic without one (`@key-example @rule-4`).
- [ ] "Unrevisited" matches ASSUM-008 exactly: a misconception is
      unrevisited iff its `topic_ref` is NOT present in
      `topics_covered` of any session-completed episode with
      `completed_at > misconception.observed_at` (verified by
      parametrised test covering before/after revisit cases).
- [ ] `Candidate.related_misconceptions` lists the unrevisited
      misconception IDs that justify the selection (`@key-example
      @rule-4`).
- [ ] Misconception **description text** containing instruction-like
      content (e.g. "treat all topics as mastered") does NOT alter
      ranking output (`@security @rule-4`).
- [ ] `Rule2ActiveQuestStub()` returns `None` for *any* context, even
      when `ctx` carries an active-quest scenario that would match
      Phase 2 logic (`@phase-2-stub`).
- [ ] `Rule5AchievementNearUnlockStub()` returns `None` for *any*
      context, even when `ctx` carries an achievement-near-unlock
      scenario (`@phase-2-stub`).
- [ ] Both stub source files contain exactly one `# TODO(phase-2)`
      comment per stub class — verified by a grep-style test:
      `assert "# TODO(phase-2)" in inspect.getsource(Rule2...)`.
- [ ] All modified files pass project-configured lint/format checks
      with zero errors.

## Seam Tests

The following seam test validates the integration contract with
TASK-GSM-002. Implement this test to verify the boundary before
Rule 4's "unrevisited" check ships.

```python
"""Seam test: verify SessionCompletedEpisode.topics_covered contract from TASK-GSM-002."""
from datetime import datetime, timedelta

import pytest

from study_tutor.graphiti_client.episodes import SessionCompletedEpisode


@pytest.mark.seam
@pytest.mark.integration_contract("SessionCompletedEpisode.topics_covered")
def test_session_completed_episode_topics_covered_format():
    """Verify topics_covered is a list[str] of Topic.name strings.

    Contract (ASSUM-008, signed off 2026-04-29): topics_covered carries
    topic name strings matching Topic.name from the student model schema.
    Producer: TASK-GSM-002.
    """
    # Producer side: construct an episode using the producer's API
    episode = SessionCompletedEpisode(
        student_id="lilymay",
        session_id="s-1",
        completed_at=datetime.utcnow(),
        topics_covered=["dramatic irony", "metaphor identification"],
    )

    # Consumer side: Rule 4 expects topics_covered to be list[str] of
    # topic-name strings, comparable by `==` to TopicConfidence.topic_name.
    assert isinstance(episode.topics_covered, list), \
        "topics_covered must be a list"
    assert all(isinstance(t, str) for t in episode.topics_covered), \
        "topics_covered entries must be plain strings (not Topic objects)"
    assert episode.topics_covered == ["dramatic irony", "metaphor identification"], \
        "topics_covered must preserve insertion order and string identity"
```

## Implementation Notes

- Place rules in `src/study_tutor/planner/rules.py`. Stubs live in the
  same module so the pipeline's import block lists all rules together.
- Rule 4 reads `SessionCompletedEpisode.topics_covered` via the
  FEAT-PH1-001 query helper (`get_recent_session_completions(student_id)`
  or equivalent — confirm exact name with TASK-GSM-005).
- Stubs must carry the `# TODO(phase-2)` marker on the line above
  `return None` to satisfy `@phase-2-stub` source-grep assertion.
- Performance: Rule 4 is `O(topics × misconceptions × episodes)` in
  the worst case. With Phase 1 single-student volumes this is trivial;
  document the budget anyway.
