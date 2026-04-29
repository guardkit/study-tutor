"""Knowledge layer for student-model writes into Graphiti.

This package holds the Pydantic episode types that flow through the shared
async write helper into Graphiti, plus (in adjacent tasks) the entity and
relationship schema and the helper itself.

Episode types are stack-agnostic: they do not import anything from
``graphiti-core``. The helper layer is responsible for adapting them.
"""

from __future__ import annotations
