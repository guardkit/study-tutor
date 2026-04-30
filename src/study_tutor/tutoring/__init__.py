"""Tutoring runtime — Coach AsyncSubAgent and Player-Coach orchestration.

This package houses the deepagents-based tutoring loop (FEAT-PH1-003). The
Coach AsyncSubAgent is the per-turn evaluator that observes misconceptions
and dispatches them through the shared Graphiti write helper (TASK-GSM-004)
per DDR-002 (per-observation ownership).

TASK-DTL-003 adds the per-turn :class:`PlayerCoachOrchestrator` that wires
the quote-verifier → Player → Coach pipeline together with the bounded
revision loop and fallback policies.
"""

from study_tutor.tutoring.orchestrator import (
    LATENCY_BUDGET_SECONDS,
    MAX_REVISION_ATTEMPTS,
    CoachLike,
    CoachUnavailableError,
    OrchestratorConfigurationError,
    PlayerCoachOrchestrator,
    PlayerLike,
    PlayerUnavailableError,
    QuoteVerifierLike,
    TurnDecision,
    TurnResult,
    validate_loop_configuration,
)

__all__ = [
    "LATENCY_BUDGET_SECONDS",
    "MAX_REVISION_ATTEMPTS",
    "CoachLike",
    "CoachUnavailableError",
    "OrchestratorConfigurationError",
    "PlayerCoachOrchestrator",
    "PlayerLike",
    "PlayerUnavailableError",
    "QuoteVerifierLike",
    "TurnDecision",
    "TurnResult",
    "validate_loop_configuration",
]
