"""pytest-bdd collection bridge for ``features/`` (FEAT-1773 / TASK-GSM-003).

Two responsibilities — both are infrastructure required to make GuardKit's
``bdd_runner.run_bdd_for_task`` (TASK-OPS-BDDM-9) succeed when it points
``pytest`` at a literal ``.feature`` path:

1. **Collection bridge** — pytest-bdd v8 does NOT register a
   ``pytest_collect_file`` hook for ``.feature`` files. The bdd_runner
   subprocess invocation is::

       pytest --gherkin-terminal-reporter --junitxml=... \\
              -m <sanitised_tag> features/<slug>/<slug>.feature

   Without a bridge, pytest exits 4 ("ERROR: not found") because the
   ``.feature`` extension has no registered collector and pytest's argv
   resolver bails before pytest-bdd's machinery runs. The
   :func:`pytest_collect_file` hook below redirects ``.feature`` argv to
   the sibling ``test_<slug>.py`` glue module, which calls
   :func:`pytest_bdd.scenarios` to actually bind the feature file.

2. **Tag → marker sanitisation** — pytest-bdd's default
   :func:`pytest_bdd_apply_tag` registers a marker with the literal tag
   string (``@task:TASK-GSM-003`` → marker ``task:TASK-GSM-003``).
   GuardKit's ``bdd_runner._build_pytest_argv`` sanitises the same tag to
   ``task_TASK_GSM_003`` for the ``-m`` filter (``:`` and ``-`` are not
   valid identifier chars in pytest marker expressions). The override
   below applies the same sanitisation so the ``-m`` filter actually
   matches the registered markers.

Pattern adapted from the canonical jarvis implementation in
``jarvis/features/conftest.py`` (TASK-OPS-J002-BDD).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest

T = TypeVar("T", bound=Callable[..., object])


def _sanitise_tag(tag: str) -> str:
    """Mirror ``bdd_runner._build_pytest_argv``'s tag normalisation.

    Strips the leading ``@`` (Gherkin tags carry it; pytest markers do
    not), then replaces ``:`` and ``-`` with ``_`` so the result is a
    valid pytest marker identifier.
    """
    return tag.lstrip("@").replace(":", "_").replace("-", "_")


def pytest_bdd_apply_tag(tag: str, function: T) -> T:
    """Register Gherkin tags as sanitised pytest markers.

    Returning a non-``None`` value short-circuits pytest-bdd's default
    implementation (which uses the literal tag string as the marker
    name). See module docstring for why sanitisation is required.
    """
    mark = getattr(pytest.mark, _sanitise_tag(tag))
    return cast(T, mark(function))


class _FeatureFile(pytest.File):
    """Collector whose ``path`` matches the ``.feature`` argv.

    pytest's args resolver matches positional argv against collector
    ``path`` attributes. Returning a :class:`pytest.Module` whose path
    is the sibling ``.py`` glue makes pytest report "not found" for the
    original ``.feature`` arg even though the hook fired. Subclassing
    :class:`pytest.File` keeps the ``.feature`` path on the collector
    while delegating actual item collection to the glue module via
    :class:`pytest.Module`'s normal import machinery.
    """

    def collect(self) -> Iterator[Any]:
        glue = self.path.with_name(f"test_{self.path.stem.replace('-', '_')}.py")
        if not glue.is_file():
            return
        module_collector = pytest.Module.from_parent(self.parent, path=glue)
        yield from module_collector.collect()


def pytest_collect_file(
    parent: pytest.Collector, file_path: Path
) -> pytest.Collector | None:
    """Bridge ``.feature`` argv to the sibling ``test_<slug>.py`` glue.

    Returning ``None`` for paths without a sibling glue lets pytest fall
    through to its default handling (and surface the original "not
    found" error), so missing-glue cases are not silently swallowed.
    """
    if file_path.suffix != ".feature":
        return None
    glue = file_path.with_name(f"test_{file_path.stem.replace('-', '_')}.py")
    if not glue.is_file():
        return None
    return _FeatureFile.from_parent(parent, path=file_path)
