"""Coach AsyncSubAgent package — factory, structural invariants, and dispatcher.

Public surface:

- :class:`Coach`, :func:`create_coach`, :func:`validate_coach_config`,
  :class:`CoachConfigurationError`, :class:`PlayerConfig`,
  :class:`CoachConfig`, :class:`WriteHelperLike` — TASK-DTL-001 factory and
  structural invariants.
- :class:`CriterionScore`, :class:`RubricFeedback`, :class:`CoachVerdict`,
  :class:`MisconceptionObservation`, :data:`REASONING_LONG_WORD_THRESHOLD`
  — TASK-DTL-001 canonical Pydantic v2 output models.
- :class:`CoachMisconceptionDispatcher`, :func:`sanitise_misconception`,
  :data:`MAX_MISCONCEPTION_TEXT_LENGTH`, :data:`TRUNCATION_SUFFIX` —
  TASK-DTL-004 caller-side sanitisation + per-observation dispatcher.
- :func:`score_rubric`, :func:`verify_quotes`, :func:`evaluate_player_turn`,
  :func:`parse_coach_output`, :func:`coach_unevaluated_fallback`,
  :class:`RubricWeights`, :class:`TurnContext`, :class:`QuoteVerifierLike`,
  :class:`QuoteVerificationResult`, :class:`QuoteAnnotation`,
  :class:`MalformedCoachOutputError`, :class:`UnevaluatedTurnFallback`,
  :class:`CoachEvaluation`, :data:`ACCEPTANCE_THRESHOLD`,
  :data:`MIN_QUOTE_LENGTH_WORDS`, :data:`CRITERION_IDS`, :data:`DEFAULT_WEIGHTS`
  — TASK-DTL-002 rubric scoring + quote-fidelity integration.

Per TASK-DTL-004 + Finding F9 of TASK-REV-DTL3, sanitisation of learner-derived
misconception text lives **here** (caller-side), not inside the shared
misconception write helper. The helper is the dispatch surface; the Coach
AsyncSubAgent is the content layer.
"""

from study_tutor.tutoring.coach.factory import (
    REASONING_LONG_WORD_THRESHOLD,
    Coach,
    CoachConfig,
    CoachConfigurationError,
    CoachVerdict,
    CriterionScore,
    MisconceptionObservation,
    PlayerConfig,
    RubricFeedback,
    WriteHelperLike,
    create_coach,
    validate_coach_config,
)
from study_tutor.tutoring.coach.rubric import (
    ACCEPTANCE_THRESHOLD,
    CRITERION_AO_ALIGNMENT,
    CRITERION_CONSTRUCTIVE_FEEDBACK,
    CRITERION_CURRICULUM_ACCURACY,
    CRITERION_GRADE_APPROPRIATE_LANGUAGE,
    CRITERION_IDS,
    CRITERION_QUOTE_FIDELITY,
    CRITERION_SCAFFOLDING_DEPTH,
    DEFAULT_WEIGHTS,
    MIN_QUOTE_LENGTH_WORDS,
    CoachEvaluation,
    CriterionScorer,
    MalformedCoachOutputError,
    QuoteAnnotation,
    QuoteVerificationResult,
    QuoteVerifierLike,
    RubricWeights,
    ScorerMap,
    TurnContext,
    UnevaluatedTurnFallback,
    coach_unevaluated_fallback,
    evaluate_player_turn,
    parse_coach_output,
    score_rubric,
    verify_quotes,
)
from study_tutor.tutoring.coach.sanitise import (
    MAX_MISCONCEPTION_TEXT_LENGTH,
    TRUNCATION_SUFFIX,
    CoachMisconceptionDispatcher,
    sanitise_misconception,
)

__all__ = [
    # TASK-DTL-001: factory + invariants + canonical models
    "REASONING_LONG_WORD_THRESHOLD",
    "Coach",
    "CoachConfig",
    "CoachConfigurationError",
    "CoachVerdict",
    "CriterionScore",
    "MisconceptionObservation",
    "PlayerConfig",
    "RubricFeedback",
    "WriteHelperLike",
    "create_coach",
    "validate_coach_config",
    # TASK-DTL-002: rubric scoring + quote-fidelity integration
    "ACCEPTANCE_THRESHOLD",
    "MIN_QUOTE_LENGTH_WORDS",
    "CRITERION_IDS",
    "CRITERION_CURRICULUM_ACCURACY",
    "CRITERION_AO_ALIGNMENT",
    "CRITERION_SCAFFOLDING_DEPTH",
    "CRITERION_GRADE_APPROPRIATE_LANGUAGE",
    "CRITERION_CONSTRUCTIVE_FEEDBACK",
    "CRITERION_QUOTE_FIDELITY",
    "CoachEvaluation",
    "CriterionScorer",
    "DEFAULT_WEIGHTS",
    "MalformedCoachOutputError",
    "QuoteAnnotation",
    "QuoteVerificationResult",
    "QuoteVerifierLike",
    "RubricWeights",
    "ScorerMap",
    "TurnContext",
    "UnevaluatedTurnFallback",
    "coach_unevaluated_fallback",
    "evaluate_player_turn",
    "parse_coach_output",
    "score_rubric",
    "verify_quotes",
    # TASK-DTL-004: sanitisation + per-observation dispatcher
    "MAX_MISCONCEPTION_TEXT_LENGTH",
    "TRUNCATION_SUFFIX",
    "CoachMisconceptionDispatcher",
    "sanitise_misconception",
]
