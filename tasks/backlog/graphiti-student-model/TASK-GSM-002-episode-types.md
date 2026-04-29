---
id: TASK-GSM-002
title: "Define Pydantic episode types for student-model write paths"
task_type: declarative
parent_review: TASK-REV-7DC0
feature_id: FEAT-1773
wave: 1
implementation_mode: direct
complexity: 2
estimated_minutes: 30
status: backlog
priority: high
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
dependencies: []
tags: [graphiti, episodes, schema, pydantic, declarative]
consumer_context:
  - task: TASK-GSM-001
    consumes: PydanticEntities
    framework: "Pydantic v2 (BaseModel)"
    driver: "pydantic"
    format_note: "Episode payloads reference Topic / Misconception / Student / Subject types from student_model.py — type-only imports, no runtime coupling"
---

# Task: Define Pydantic episode types for student-model write paths

## Description

Define the three episode types that flow through the shared async write helper into Graphiti. Each episode is a Pydantic model whose serialised payload is what Graphiti's extraction LLM sees; the shape is therefore part of the data contract, not just internal to the helper.

Per the build plan (Saturday afternoon, step 5) and `phase-1-scope.md §FEAT-PH1-001`.

## Scope

**Episode types** (`src/study_tutor/knowledge/episodes.py`):

1. `SessionCompletedEpisode` — emitted at flush point F3 by the Tutor handler on `active → ended` state transition (per DDR-002 + DDR-003).
   - Fields: `session_id: str`, `student_id: str`, `subject_slug: str`, `text_name: str`, `topics_covered: list[str]`, `aos_exercised: list[str]`, `narrative_summary: str`, `started_at: datetime`, `ended_at: datetime`

2. `TopicConfidenceUpdatedEpisode` — emitted at flush point F2 by the Tutor handler when the planner produces a confidence delta.
   - Fields: `student_id: str`, `topic_name: str`, `previous_band: str`, `new_band: str`, `previous_percentage: int`, `new_percentage: int`, `observed_at: datetime`, `triggering_session_id: str | None`

3. `MisconceptionObservedEpisode` — emitted at flush point F1 by the Coach AsyncSubAgent (per DDR-002) when the Coach identifies a misconception.
   - Fields: `student_id: str`, `topic_name: str`, `misconception_text: str`, `observed_at: datetime`, `triggering_session_id: str`, `confidence_band_at_observation: str`

All three inherit from a shared `EpisodeBase(BaseModel)` that provides:
- `episode_kind: Literal["session_completed", "topic_confidence_updated", "misconception_observed"]`
- `to_graphiti_episode_body() -> str` — produces the natural-language string Graphiti's `add_episode` ingests

## Acceptance Criteria

- [ ] `EpisodeBase` and three concrete episode classes defined as `pydantic.BaseModel` subclasses
- [ ] `episode_kind` discriminator field present on each, matching the scope-doc names exactly
- [ ] `to_graphiti_episode_body()` produces a deterministic string (same payload → same string)
- [ ] Required fields rejected when omitted; type coercion correct on construction
- [ ] No imports from graphiti-core; episode types are stack-agnostic
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- Unit tests in `tests/unit/knowledge/test_episodes.py`:
  - Each episode rejects partial payloads
  - `to_graphiti_episode_body()` is deterministic across two calls with the same input
  - The discriminator field is checked at construction (not silently coerced)
  - Round-trip: `Episode.model_validate(episode.model_dump())` returns an equal instance

## Implementation Notes

- This is a **declarative** task — pure types, no async, no Graphiti.
- The `to_graphiti_episode_body()` content is what an adversarial misconception text would manipulate (see RISK 3 in IMPLEMENTATION-GUIDE.md). Sanitisation is NOT done here — that lives in TASK-GSM-004's helper. This task only defines the shape.
- `MisconceptionObservedEpisode.misconception_text` is `str` (no length cap) at this layer; the cap is enforced by the helper. Don't pre-empt that decision here.

## §4 Integration Contract Producer

This task produces one contract consumed by downstream slices:

**EpisodeTypes** — `EpisodeBase`, `SessionCompletedEpisode`, `TopicConfidenceUpdatedEpisode`, `MisconceptionObservedEpisode`. Consumed by TASK-GSM-004 (write helper passes them through), TASK-GSM-005 (`record_session_completion` constructs `SessionCompletedEpisode`), TASK-GSM-006 (seeding constructs `TopicConfidenceUpdatedEpisode` for Lilymay's baseline).

See `IMPLEMENTATION-GUIDE.md §4` for full contract specification.

## Seam Tests

The following seam test validates the integration contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify PydanticEntities contract from TASK-GSM-001."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("PydanticEntities")
def test_pydantic_entities_imports_and_shape():
    """Verify PydanticEntities contract is honoured by episode types.

    Contract: Episode payloads reference Topic / Misconception / Student / Subject types
              from student_model.py — type-only imports, no runtime coupling.
    Producer: TASK-GSM-001
    """
    # Producer side: import the producer's exports
    from study_tutor.knowledge.student_model import (
        Student,
        Subject,
        Text,
        Topic,
        AssessmentObjective,
        Misconception,
        TopicConfidence,
    )

    # Consumer side: import this task's episode types
    from study_tutor.knowledge.episodes import (
        EpisodeBase,
        SessionCompletedEpisode,
        TopicConfidenceUpdatedEpisode,
        MisconceptionObservedEpisode,
    )

    # Format assertions derived from §4 contract:
    # - All entity classes are importable (no circular deps)
    assert Student is not None
    assert Topic is not None
    assert Misconception is not None

    # - EpisodeBase has the discriminator field
    assert "episode_kind" in EpisodeBase.model_fields

    # - Each concrete episode subclasses EpisodeBase
    for cls in (SessionCompletedEpisode, TopicConfidenceUpdatedEpisode, MisconceptionObservedEpisode):
        assert issubclass(cls, EpisodeBase), f"{cls.__name__} must inherit from EpisodeBase"
```
