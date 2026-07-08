"""Knowledge layer for the student model — schema plus the Postgres store.

This package holds the Pydantic entity/relationship schema and the record
types that describe a learner's state, plus the Postgres-backed
:mod:`~study_tutor.knowledge.store` that persists it ([ADR-ARCH-023]).

The schema types are stack-agnostic: they import no database driver. The store
layer is responsible for adapting them to Postgres rows.
"""

from __future__ import annotations
