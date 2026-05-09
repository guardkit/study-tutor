"""Roles package.

Importing this package eagerly imports each role sub-package so its
top-level ``register_role(...)`` call runs and the in-process fleet
registry (:mod:`study_tutor.roles.registry`) is populated. Eager
registration on package import is the primary trigger; the registry's
:func:`_ensure_roles_registered` is a defensive backup for callers that
reach the registry before any role import has happened.

See TASK-NATS-PH1-003 for the registration pattern (mirrors
``specialist_agent.roles``).
"""

from __future__ import annotations

# Side-effect import: registers the "tutor" role with the registry.
# Imported under a private alias to make it clear this is for side
# effects only — nothing inside the package should import this name.
from study_tutor.roles import tutor as _tutor  # noqa: F401
