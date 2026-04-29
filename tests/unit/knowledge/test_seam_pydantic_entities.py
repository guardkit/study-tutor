"""Seam test: verify PydanticEntities contract from TASK-GSM-001.

This test sits at the boundary between TASK-GSM-001 (producer of entity /
relationship Pydantic types in ``student_model.py``) and TASK-GSM-002
(this task — episode types in ``episodes.py``). It ensures the two
modules can co-exist without circular imports and that the discriminator
contract on ``EpisodeBase`` is honoured.
"""

from __future__ import annotations

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
        AssessmentObjective,
        Misconception,
        Student,
        Subject,
        Text,
        Topic,
        TopicConfidence,
    )

    # Consumer side: import this task's episode types
    from study_tutor.knowledge.episodes import (
        EpisodeBase,
        MisconceptionObservedEpisode,
        SessionCompletedEpisode,
        TopicConfidenceUpdatedEpisode,
    )

    # Format assertions derived from §4 contract:
    # - All entity classes are importable (no circular deps)
    assert Student is not None
    assert Subject is not None
    assert Text is not None
    assert Topic is not None
    assert AssessmentObjective is not None
    assert Misconception is not None
    assert TopicConfidence is not None

    # - EpisodeBase has the discriminator field
    assert "episode_kind" in EpisodeBase.model_fields

    # - Each concrete episode subclasses EpisodeBase
    for cls in (
        SessionCompletedEpisode,
        TopicConfidenceUpdatedEpisode,
        MisconceptionObservedEpisode,
    ):
        assert issubclass(cls, EpisodeBase), (
            f"{cls.__name__} must inherit from EpisodeBase"
        )
