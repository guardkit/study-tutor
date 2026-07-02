"""Injection seam for the ``StudentStore`` (FEAT-SMP-002).

Mirrors ``knowledge.retrieval.set_collection_provider`` exactly: the concrete
store (``PostgresStudentStore``) is wired **once at orchestrator startup**; the
read helpers resolve it here rather than constructing a connection on the hot
path. Keeping the wiring in one module-level slot (rather than threading a store
handle through every call site) matches the retrieval module's pattern and lets
tests install a fake store per case.

``None`` means "no store wired" — the read helpers degrade to an empty result
(``StudentState(empty=True)`` / empty planner inputs), exactly as the graph read
path degraded when handed ``client=None``. This is the property FEAT-SMP-004
relies on to delete the graph plumbing without a flag day: an un-wired store
reads as "no learner state yet", never a crash.
"""
from __future__ import annotations

from study_tutor.knowledge.store.port import StudentStore

# Module-level single slot. Read once per turn within a single thread; the
# orchestrator owns startup wiring, so racing readers/writers are not a concern
# at this layer (same posture as ``retrieval._collection_provider``).
_student_store: StudentStore | None = None


def set_student_store(store: StudentStore) -> None:
    """Install the process-wide ``StudentStore``. Called once at startup;
    tests rebind per case."""
    global _student_store
    _student_store = store


def get_student_store() -> StudentStore | None:
    """Return the wired store, or ``None`` if none is installed."""
    return _student_store


def reset_student_store() -> None:
    """Remove the installed store (test teardown helper)."""
    global _student_store
    _student_store = None


__all__ = ["get_student_store", "reset_student_store", "set_student_store"]
