"""pytest-bdd glue module for ``graphiti-student-model.feature``.

Binds the sibling ``.feature`` file's scenarios into pytest's collection
tree via :func:`pytest_bdd.scenarios`. No ``@given/@when/@then``
step-definitions are implemented yet — every scenario will therefore
surface as ``scenarios_pending`` in
:class:`guardkit.orchestrator.quality_gates.bdd_runner.BDDResult`
(pytest-bdd raises ``StepDefinitionNotFoundError`` for an un-bound step,
which the runner classifies as *pending*, not *failed*). Coach's approval
rule is ``scenarios_failed == 0`` — pending scenarios are tolerated as a
scaffolding state.

This module's sole job is to make the runner subprocess

    pytest --gherkin-terminal-reporter --junitxml=... \\
           -m task_TASK_GSM_003 \\
           features/graphiti-student-model/graphiti-student-model.feature

actually collect items rather than exit 4 ("not found"). The collection
bridge in the parent ``features/conftest.py`` redirects pytest's argv
resolver to this file so :func:`pytest_bdd.scenarios` can run.

Implementing step-definitions for the per-task scenarios (e.g.
TASK-GSM-003 ``@module-load`` scenario) is intentionally out of scope
here; per FEAT-BDDM follow-up convention, scenarios that need real
implementation get filed as their own follow-up tasks rather than being
folded into the producer task that owns the ``.feature`` tag.
"""

from __future__ import annotations

from pytest_bdd import scenarios

scenarios("./graphiti-student-model.feature")
