"""Structural validation of runtime-asset COPY directives in the Dockerfile.

TASK-NATS-PH3-006 / FEAT-NATS — Bug #5: Dockerfile missing COPY for
``roles/``, ``data/``, and ``.guardkit/graphiti.yaml``.

Why this test exists
--------------------
The 2026-05-10 dress-rehearsal of the NATS fleet demo runbook
(RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md) caught the
container crash-looping at boot because three runtime asset trees were
absent from the image:

* ``/workspace/study-tutor/roles/tutor/role.yaml`` — read by the role-
  manifest loader (``cli/main.py:491``); DECISION-DF-001 / AC-LOAD-06
  forbid silent fall-back to defaults.
* ``/workspace/study-tutor/data/`` — read by the data-layer bootstrap.
* ``/workspace/study-tutor/.guardkit/graphiti.yaml`` — read by the
  graphiti-config loader (``cli/main.py:502``); same no-fallback policy.

The fix is three COPY directives in ``Dockerfile``. This module guards
those directives so a future edit (e.g. someone refactors the Dockerfile
and drops a line) cannot regress Bug #5 silently.

Why structural-only?
--------------------
Same rationale as ``tests/unit/test_dockerfile_structure.py`` and
``tests/unit/test_compose_structure.py``: the unit test suite has no
Docker daemon and no sibling ``nats-core`` checkout, so we cannot
``docker build`` the image inside the test process. The runtime
verification that the assets actually land in the image lives in the
Phase-3 runbook (TASK-NATS-PH3-004) and the GB10 e2e smoke
(TASK-NATS-PH3-005); see the "Coach validation" block in the task body
for the exact ``docker run --rm --entrypoint sh`` invocations.

What we validate here is the file-level contract those runtime checks
depend on: the three COPY directives are present, point at the right
sources and destinations, and sit in a position that preserves the
deps-before-source cache-locality contract from TASK-NATS-PH3-001 (AC #7).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE_PATH = PROJECT_ROOT / "Dockerfile"


@pytest.fixture(scope="module")
def dockerfile_text() -> str:
    """Load the Dockerfile once per module.

    Raises a clear ``FileNotFoundError`` if the file is missing so the
    failure points at the actual problem (Dockerfile absent) rather than
    surfacing as a confusing AttributeError further down.
    """
    if not DOCKERFILE_PATH.is_file():
        raise FileNotFoundError(
            f"Dockerfile not found at {DOCKERFILE_PATH}. "
            "TASK-NATS-PH3-001 requires a Dockerfile at the project root."
        )
    return DOCKERFILE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dockerfile_lines(dockerfile_text: str) -> list[str]:
    """Pre-split the Dockerfile into lines for index-based ordering checks."""
    return dockerfile_text.splitlines()


# ---------------------------------------------------------------------------
# Asset COPY directives — one test per asset
# ---------------------------------------------------------------------------


def test_copies_roles_directory(dockerfile_text: str) -> None:
    """``roles/`` must be COPY-d into the image at the project workdir.

    Source path is ``study-tutor/roles/`` (the BuildKit context root is
    the repo parent), destination is ``./roles/`` resolved against
    ``WORKDIR /workspace/study-tutor``. Without this directive, the
    role-manifest loader raises ``FileNotFoundError: Role manifest not
    found: /workspace/study-tutor/roles/tutor/role.yaml`` at boot — the
    pre-patch first crash from the 2026-05-10 runbook.
    """
    pattern = re.compile(
        r"^COPY\s+study-tutor/roles/\s+\./roles/\s*$",
        re.MULTILINE,
    )
    assert pattern.search(dockerfile_text), (
        "Dockerfile must contain a `COPY study-tutor/roles/ ./roles/` "
        "directive. Bug #5 (TASK-NATS-PH3-006): without this, the "
        "role-manifest loader (cli/main.py) crashes the container at "
        "boot because DECISION-DF-001 / AC-LOAD-06 forbid silent "
        "fall-back to defaults."
    )


def test_copies_data_directory(dockerfile_text: str) -> None:
    """``data/`` must be COPY-d into the image at the project workdir.

    The data-layer bootstrap expects ``/workspace/study-tutor/data/`` to
    exist. Without this directive, the bootstrap fails at boot the same
    way the role-manifest loader does.
    """
    pattern = re.compile(
        r"^COPY\s+study-tutor/data/\s+\./data/\s*$",
        re.MULTILINE,
    )
    assert pattern.search(dockerfile_text), (
        "Dockerfile must contain a `COPY study-tutor/data/ ./data/` "
        "directive. Bug #5 (TASK-NATS-PH3-006): without this, the "
        "data-layer bootstrap cannot locate /workspace/study-tutor/data/ "
        "and the container crash-loops before reaching its NATS connect."
    )


def test_copies_graphiti_config_file(dockerfile_text: str) -> None:
    """``.guardkit/graphiti.yaml`` must be COPY-d as a single file.

    Note the file-level COPY (not a directory COPY) — we deliberately
    ship only ``graphiti.yaml`` from ``.guardkit/`` rather than the
    whole directory (which contains worktree / autobuild scratch state
    that has no place in a runtime image).

    Without this directive the graphiti-config loader (cli/main.py:502)
    raises ``FileNotFoundError: graphiti config not found at
    .guardkit/graphiti.yaml`` at boot — the second crash from the
    2026-05-10 runbook, surfaced after the roles/ + data/ COPY lines
    were already in place. DECISION-DF-001 / AC-LOAD-06 forbid silent
    fall-back here too.
    """
    pattern = re.compile(
        r"^COPY\s+study-tutor/\.guardkit/graphiti\.yaml\s+\./\.guardkit/graphiti\.yaml\s*$",
        re.MULTILINE,
    )
    assert pattern.search(dockerfile_text), (
        "Dockerfile must contain a "
        "`COPY study-tutor/.guardkit/graphiti.yaml ./.guardkit/graphiti.yaml` "
        "directive (note: single-file COPY, not a directory COPY — see the "
        "test docstring for why). Bug #5 (TASK-NATS-PH3-006): without this, "
        "the graphiti-config loader crashes the container at boot."
    )


# ---------------------------------------------------------------------------
# Cache layering — asset COPYs must sit in the application-source layer
# ---------------------------------------------------------------------------


def test_asset_copies_follow_source_copy(dockerfile_lines: list[str]) -> None:
    """The three asset COPYs must come AFTER ``COPY study-tutor/src/ ./src/``.

    AC #7 of TASK-NATS-PH3-006 mandates "Dockerfile cache layering is
    preserved: uv sync (deps) must remain cached across rebuilds that
    touch only src/, roles/, data/, or .guardkit/graphiti.yaml".

    The way that contract is satisfied is by placing the asset COPYs
    inside Layer 2 (application-source layer, after ``COPY .../src/
    ./src/``) and NOT between the lockfile copy and ``uv sync``. If the
    asset COPYs leaked above the source copy they would bust the deps
    layer cache on every role/data/graphiti edit.
    """
    src_idx = next(
        (
            idx
            for idx, line in enumerate(dockerfile_lines)
            if line.startswith("COPY study-tutor/src/")
        ),
        -1,
    )
    assert src_idx != -1, (
        "Expected `COPY study-tutor/src/ ./src/` directive (deps-before-"
        "source layering established in TASK-NATS-PH3-001)."
    )

    asset_prefixes = (
        "COPY study-tutor/roles/",
        "COPY study-tutor/data/",
        "COPY study-tutor/.guardkit/graphiti.yaml",
    )
    for prefix in asset_prefixes:
        asset_idx = next(
            (
                idx
                for idx, line in enumerate(dockerfile_lines)
                if line.startswith(prefix)
            ),
            -1,
        )
        assert asset_idx != -1, (
            f"Expected a `{prefix}...` directive (Bug #5 regression guard)."
        )
        assert asset_idx > src_idx, (
            f"`{prefix}...` must come AFTER `COPY study-tutor/src/ "
            "./src/` so it sits inside the application-source layer. "
            "Placing it above the source copy would bust the uv-sync "
            "deps-layer cache on every asset edit (AC #7 cache "
            "layering)."
        )


def test_lockfile_copy_precedes_asset_copies(dockerfile_lines: list[str]) -> None:
    """``COPY pyproject.toml uv.lock`` must precede every asset COPY.

    Reinforces the inverse direction of the cache-layering contract:
    even if the asset COPYs were re-ordered relative to the source COPY
    by a future edit, they must still sit below the lockfile copy so
    the deps layer (``uv sync --frozen --no-dev --no-install-project``)
    remains cached across asset-only edits.
    """
    lockfile_idx = next(
        (
            idx
            for idx, line in enumerate(dockerfile_lines)
            if line.startswith("COPY")
            and "pyproject.toml" in line
            and "uv.lock" in line
        ),
        -1,
    )
    assert lockfile_idx != -1, (
        "Expected `COPY study-tutor/pyproject.toml study-tutor/uv.lock` "
        "to seed the dependency layer."
    )

    asset_prefixes = (
        "COPY study-tutor/roles/",
        "COPY study-tutor/data/",
        "COPY study-tutor/.guardkit/graphiti.yaml",
    )
    for prefix in asset_prefixes:
        asset_idx = next(
            (
                idx
                for idx, line in enumerate(dockerfile_lines)
                if line.startswith(prefix)
            ),
            -1,
        )
        assert asset_idx != -1, (
            f"Expected a `{prefix}...` directive (Bug #5 regression guard)."
        )
        assert asset_idx > lockfile_idx, (
            f"`{prefix}...` must come AFTER the "
            "`COPY ... pyproject.toml ... uv.lock ...` directive so the "
            "uv-sync deps layer remains cached across asset-only edits "
            "(AC #7 cache layering)."
        )


# ---------------------------------------------------------------------------
# Negative assertion — guard against directory-scope drift on .guardkit/
# ---------------------------------------------------------------------------


def test_does_not_copy_whole_guardkit_directory(dockerfile_text: str) -> None:
    """The Dockerfile must NOT COPY the entire ``.guardkit/`` directory.

    ``.guardkit/`` on the host contains worktree scratch state
    (``autobuild/``, ``worktrees/``) generated by the GuardKit
    autobuild player. None of that belongs in a runtime image — it
    would bloat the image, leak workflow artefacts, and bust cache on
    every autobuild run. Only the single ``graphiti.yaml`` file is
    needed at runtime, and the test above
    (``test_copies_graphiti_config_file``) pins that file-level COPY.

    This negative guard catches the obvious "simplification" mistake of
    a future contributor replacing the file-level COPY with a directory
    COPY because they think it's cleaner.
    """
    bad_pattern = re.compile(
        r"^COPY\s+study-tutor/\.guardkit/\s+\./\.guardkit/\s*$",
        re.MULTILINE,
    )
    assert not bad_pattern.search(dockerfile_text), (
        "Dockerfile must NOT contain "
        "`COPY study-tutor/.guardkit/ ./.guardkit/`. Only the single "
        "file `graphiti.yaml` is needed at runtime; copying the whole "
        "directory would ship autobuild / worktree scratch state into "
        "the image. Use the file-level COPY guarded by "
        "test_copies_graphiti_config_file instead."
    )
