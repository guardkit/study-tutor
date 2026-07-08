"""Store-backed read helpers (FEAT-SMP-002) — the replacement for the prior
graph-backed reads.

These are drop-ins for the two read surfaces the prior graph path exposed:

- ``get_student_state`` — the aggregate snapshot the MCP/HTTP handlers read
  (was ``get_student_state`` → ``_read_student_partition`` over the graph backend).
- ``load_planner_inputs`` — the **planner wiring**: the per-topic confidence
  entities + recent misconceptions the session planner ranks over
  (``PlannerContext.create(topic_confidences=…, misconceptions=…,
  learner_state_available=…)``, FEAT-PH1-002).

Both resolve the injected store via :mod:`provider` and **preserve the
graceful-degradation contract** the graph path guaranteed: no store wired, or a
read that raises, yields an empty result and a structured log line — never an
exception to the caller. That is what lets the planner fall back to a baseline
plan (``learner_state_available=False``) and the handler branch on
``StudentState.empty`` without special-casing "the store is down".

**Layering:** this module stays in the ``knowledge`` layer and returns domain
entities (``TopicConfidence`` / ``Misconception``); it does **not** import the
planner. The orchestrator maps :class:`PlannerInputs` onto ``PlannerContext.create``
at the call site, so ``knowledge`` never depends on ``planner``.

Not yet here (FEAT-SMP-002 build): the ``recommend_topics`` ranking
(``queries.recommend_topics`` → ``TopicRecommendation``) is **pure logic over
these reads** — lift it verbatim; it does not touch the store.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from study_tutor.knowledge.store.entities import StudentState
from study_tutor.knowledge.store.port import (
    DEFAULT_MISCONCEPTION_WINDOW_DAYS,
    StudentStore,
)
from study_tutor.knowledge.store.provider import get_student_store
from study_tutor.knowledge.student_model import Misconception, TopicConfidence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlannerInputs:
    """The learner-state inputs the planner needs, in one bundle.

    Frozen so a resolved read cannot be quietly mutated before it reaches
    ``PlannerContext.create``. ``learner_state_available`` distinguishes
    "store reachable, learner simply has no records yet" (``True`` with empty
    lists — the planner offers a seeded-baseline plan) from "store unreachable /
    read failed" (``False`` — the planner offers the unseeded-baseline plan),
    matching the flag ``PlannerContext.create`` already accepts (TASK-DSP-006).
    """

    topic_confidences: list[TopicConfidence]
    misconceptions: list[Misconception]
    learner_state_available: bool


def _resolve(store: StudentStore | None) -> StudentStore | None:
    """Prefer an explicitly-passed store (tests), else the wired one."""
    return store if store is not None else get_student_store()


async def get_student_state(
    student_id: str, *, store: StudentStore | None = None
) -> StudentState:
    """Aggregate learner snapshot; ``StudentState(empty=True)`` on no-store or
    read failure (never raises — graceful degradation)."""
    resolved = _resolve(store)
    if resolved is None:
        return StudentState(empty=True)
    try:
        return await resolved.get_student_state(student_id)
    except Exception as exc:  # noqa: BLE001 — degrade, don't propagate (as the graph path did)
        logger.warning(
            "student_state_read_failed",
            extra={"detail": f"{type(exc).__name__}: {exc}", "student_id": student_id},
        )
        return StudentState(empty=True)


async def load_planner_inputs(
    student_id: str,
    *,
    store: StudentStore | None = None,
    window_days: int = DEFAULT_MISCONCEPTION_WINDOW_DAYS,
) -> PlannerInputs:
    """Read the planner's inputs from the store.

    Returns ``PlannerInputs([], [], learner_state_available=False)`` when no
    store is wired or a read raises, so the planner takes its unseeded-baseline
    path rather than seeing a spurious empty-but-available learner.
    """
    resolved = _resolve(store)
    if resolved is None:
        return PlannerInputs([], [], learner_state_available=False)
    try:
        topic_confidences = await resolved.get_topic_confidences(student_id)
        misconceptions = await resolved.get_recent_misconceptions(
            student_id, window_days=window_days
        )
    except Exception as exc:  # noqa: BLE001 — degrade, don't propagate
        logger.warning(
            "planner_inputs_read_failed",
            extra={"detail": f"{type(exc).__name__}: {exc}", "student_id": student_id},
        )
        return PlannerInputs([], [], learner_state_available=False)
    return PlannerInputs(
        topic_confidences,
        misconceptions,
        learner_state_available=True,
    )


__all__ = ["PlannerInputs", "get_student_state", "load_planner_inputs"]
