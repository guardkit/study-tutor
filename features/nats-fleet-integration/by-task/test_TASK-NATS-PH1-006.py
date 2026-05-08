"""Focused per-task glue for ``TASK-NATS-PH1-006.feature`` (TASK-NATS-FIX-001).

Why this module exists
======================

The Coach's BDD oracle invokes ``pytest`` against the master glue
``features/nats-fleet-integration/test_nats_fleet_integration.py``,
which calls :func:`pytest_bdd.scenarios` against the master feature.
That binds every scenario in ``nats-fleet-integration.feature`` (30+
across nine downstream tasks). pytest-bdd v8 emits scenarios whose
steps are unbound (the peer tasks haven't landed yet) as **FAILED**,
making Coach's gate ``bdd_results.scenarios_failed == 0``
deterministically unsatisfiable for any single-task autobuild run.

This module sidesteps that by binding **only** the focused subset
``TASK-NATS-PH1-006.feature``, which contains the single
``@task:TASK-NATS-PH1-006`` scenario. With this in place,
``pytest features/nats-fleet-integration/by-task/test_TASK-NATS-PH1-006.py``
collects exactly one scenario and the gate is satisfiable.

How it reuses the master step definitions
=========================================

The step bindings (``@given``/``@when``/``@then``) for the SIGTERM
scenario already live in the master glue. The master glue's directory
has a hyphen (``nats-fleet-integration``) so it is not importable via
normal dotted-name syntax — :mod:`importlib.util` is used to load it
by file path. After loading, the public step-bound functions, the
``_BddContext`` dataclass, and the ``context`` fixture are promoted
into this module's globals so pytest-bdd's scope-based step lookup
and pytest's fixture discovery both find them. The dynamically
generated master ``test_*`` scenario functions are filtered out so
pytest does not collect peer-task scenarios via this file.

Removal
=======

When upstream GuardKit task ``TASK-FIX-CC-BDD`` lands the proper fix
(scoped pytest invocation), this entire ``by-task/`` directory can be
deleted.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from pytest_bdd import scenarios

_HERE = Path(__file__).resolve().parent
_MASTER_GLUE_PATH = _HERE.parent / "test_nats_fleet_integration.py"

# Load the master glue module via importlib because its parent directory
# (``nats-fleet-integration``) is not a valid Python package name.
_spec = importlib.util.spec_from_file_location(
    "nats_fleet_master_glue",
    _MASTER_GLUE_PATH,
)
if _spec is None or _spec.loader is None:  # pragma: no cover - defensive
    raise ImportError(f"Could not load master glue from {_MASTER_GLUE_PATH}")

_master = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("nats_fleet_master_glue", _master)
_spec.loader.exec_module(_master)

# Promote the master glue's public names into this module so pytest-bdd's
# scope-based step lookup and pytest's fixture discovery both see them.
# Skip:
#   * dunder names — internal Python machinery
#   * names starting with ``test_`` — pytest_bdd.scenarios() injected those
#     into the master module when it bound the master feature; collecting
#     them here would defeat the focused-subset purpose of this file.
#   * private names other than the two we deliberately need (_BddContext,
#     _FakeNATSAdapter — used by the typed step signatures).
_KEEP_PRIVATE = {"_BddContext", "_FakeNATSAdapter"}
for _name in dir(_master):
    if _name.startswith("__"):
        continue
    if _name.startswith("test_"):
        continue
    if _name.startswith("_") and _name not in _KEEP_PRIVATE:
        continue
    globals()[_name] = getattr(_master, _name)

# Bind the focused feature. pytest collects exactly the one scenario it
# contains; peer-task scenarios live in the master feature only.
scenarios("TASK-NATS-PH1-006.feature")
