"""Structural validation of the study-tutor Dockerfile.

TASK-NATS-PH3-001 / FEAT-NATS — Build study-tutor Dockerfile mirroring
specialist-agent pattern.

Why structural-only?
--------------------
The acceptance criteria for TASK-NATS-PH3-001 are framed around running
``docker build`` / ``docker run`` from a host with a Docker daemon and
the sibling ``nats-core`` repository checked out next to ``study-tutor``.
That environment is operator-territory (GB10, the runbook in
TASK-NATS-PH3-004) and not reproducible inside the unit test suite,
which has no Docker daemon and no sibling repo on disk.

What we verify here is the structural contract that the runbook depends
on: the Dockerfile exists at the project root, its build pipeline is
ordered for cache locality (deps before source), and the directives the
acceptance-criteria docker invocations rely on are present and correct
(BuildKit named context for ``nats-core``, ``uv sync --frozen --no-dev``
in two layers, ``study-tutor serve-nats`` as the default command).

The end-to-end ``docker build`` / ``docker run`` evidence lives in the
Phase-3 runbook (TASK-NATS-PH3-004) and the GB10 e2e smoke
(TASK-NATS-PH3-005) — those tasks are the right home for runtime
validation. This module guards the file-level invariants so a regression
in the Dockerfile (e.g. someone adds a third uv-sync layer or drops the
named context) is caught fast and locally.
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
    surfacing as a confusing AttributeError further down the test body.
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
# Existence and base-image
# ---------------------------------------------------------------------------


def test_dockerfile_exists() -> None:
    """The Dockerfile must live at the project root.

    The acceptance-criteria invocation uses ``-f study-tutor/Dockerfile``
    relative to a parent build context, so the file MUST be at the
    project root (not in scripts/ or docker/).
    """
    assert DOCKERFILE_PATH.is_file(), (
        f"Expected Dockerfile at {DOCKERFILE_PATH}; not found."
    )


def test_uses_python_slim_base_image(dockerfile_text: str) -> None:
    """Base image is python:3.x-slim, matching specialist-agent's pattern.

    ``slim`` keeps the image under the 800MB ceiling spelled out in the
    acceptance criteria. The pyproject.toml requires Python >=3.11, so a
    3.11+ tag is the floor; we accept any patched 3.x-slim variant
    (3.11/3.12/3.13) so future Python upgrades don't trip this test.
    """
    pattern = re.compile(
        r"^FROM\s+python:3\.\d+(?:\.\d+)?-slim\b",
        re.MULTILINE,
    )
    assert pattern.search(dockerfile_text), (
        "FROM directive must use a python:3.x-slim base image. "
        "specialist-agent/Dockerfile uses python:3.11-slim; the "
        "acceptance criteria require image size < 800MB."
    )


# ---------------------------------------------------------------------------
# BuildKit named context for nats-core
# ---------------------------------------------------------------------------


def test_copies_nats_core_via_named_build_context(dockerfile_text: str) -> None:
    """nats-core must come from the BuildKit named context, not the build context.

    The acceptance-criteria docker invocation passes
    ``--build-context nats-core=../nats-core``; the Dockerfile MUST
    consume that with ``COPY --from=nats-core ...``. Falling back to a
    plain ``COPY nats-core/`` would couple the build to the parent
    directory layout and break the wrapper script (TASK-NATS-PH3-003).
    """
    pattern = re.compile(
        r"^COPY\s+--from=nats-core\s+\S+\s+/\S+",
        re.MULTILINE,
    )
    assert pattern.search(dockerfile_text), (
        "Dockerfile must contain a `COPY --from=nats-core <src> <dst>` "
        "directive that consumes the BuildKit named context defined by "
        "`--build-context nats-core=../nats-core`."
    )


def test_nats_core_lands_at_sibling_path(dockerfile_text: str) -> None:
    """nats-core must be placed as a sibling of the study-tutor workdir.

    pyproject.toml declares ``nats-core = { path = "../nats-core",
    editable = true }``. uv resolves that path relative to the
    pyproject.toml's directory, so the image layout MUST mirror the
    host:

        /workspace/nats-core/      <- copied from named context
        /workspace/study-tutor/    <- WORKDIR for uv sync
    """
    sibling_pattern = re.compile(
        r"COPY\s+--from=nats-core\s+\S+\s+(/\S*nats-core/?)",
    )
    match = sibling_pattern.search(dockerfile_text)
    assert match, (
        "Could not parse the destination of the `COPY --from=nats-core` "
        "directive."
    )
    destination = match.group(1).rstrip("/")
    parent = destination.rsplit("/", 1)[0]
    assert (
        f"WORKDIR {parent}/study-tutor" in dockerfile_text
    ), (
        f"nats-core is copied to {destination!r} but no matching "
        f"`WORKDIR {parent}/study-tutor` directive was found. The two "
        "must be siblings so [tool.uv.sources] path = '../nats-core' "
        "resolves correctly."
    )


# ---------------------------------------------------------------------------
# uv layering — deps before source
# ---------------------------------------------------------------------------


def test_uv_is_installed_before_sync(dockerfile_text: str) -> None:
    """uv must be installed before any `uv sync` invocation.

    pip install is the bootstrap path; once uv is present, all dependency
    resolution flows through it because pyproject.toml's path source for
    nats-core is a uv-only feature.
    """
    pip_install_uv = dockerfile_text.find("pip install --no-cache-dir uv")
    first_uv_sync = dockerfile_text.find("uv sync")
    assert pip_install_uv != -1, (
        "Expected `pip install --no-cache-dir uv` to bootstrap uv before "
        "the first `uv sync` invocation."
    )
    assert first_uv_sync != -1, "Expected at least one `uv sync` directive."
    assert pip_install_uv < first_uv_sync, (
        "`pip install ... uv` must appear before the first `uv sync`."
    )


def test_dependency_layer_precedes_source_layer(dockerfile_lines: list[str]) -> None:
    """COPY pyproject.toml + uv.lock must precede COPY src/.

    The acceptance criteria call out "deps before source so cache
    invalidation is minimal". A regression that copies src/ first would
    bust the dep-install layer on every code change.
    """

    def _line_index(predicate: object) -> int:
        for idx, line in enumerate(dockerfile_lines):
            if predicate(line):  # type: ignore[operator]
                return idx
        return -1

    pyproject_idx = _line_index(
        lambda line: line.startswith("COPY")
        and "pyproject.toml" in line
        and "uv.lock" in line
    )
    src_idx = _line_index(
        lambda line: line.startswith("COPY")
        and ("study-tutor/src/" in line or "/src/" in line or " src/" in line)
        and "pyproject.toml" not in line
    )

    assert pyproject_idx != -1, (
        "Expected a `COPY ... pyproject.toml ... uv.lock ...` directive "
        "to seed the dependency layer."
    )
    assert src_idx != -1, "Expected a `COPY ... src/ ...` directive."
    assert pyproject_idx < src_idx, (
        "Dependency layer (pyproject.toml + uv.lock) must be copied "
        "BEFORE application source so the deps layer is cached across "
        "source-only changes."
    )


def test_uv_sync_uses_frozen_no_dev(dockerfile_text: str) -> None:
    """`uv sync` invocations must use --frozen --no-dev.

    --frozen forbids resolving against PyPI (use the locked versions
    only); --no-dev keeps test-only deps out of the runtime image. The
    task body explicitly mandates these flags.
    """
    sync_lines = re.findall(r"uv sync[^\n]*", dockerfile_text)
    assert sync_lines, "Expected at least one `uv sync` directive."
    for line in sync_lines:
        assert "--frozen" in line, (
            f"`uv sync` invocation missing --frozen flag: {line!r}"
        )
        assert "--no-dev" in line, (
            f"`uv sync` invocation missing --no-dev flag: {line!r}"
        )


def test_first_uv_sync_skips_project_install(dockerfile_text: str) -> None:
    """The first uv sync (deps-only layer) must use --no-install-project.

    Without --no-install-project, uv tries to install the study-tutor
    package itself, but src/ isn't in the image yet at that point and
    the build fails. This is the standard uv-in-Docker layering pattern.
    """
    sync_lines = re.findall(r"uv sync[^\n]*", dockerfile_text)
    assert sync_lines, "Expected at least one `uv sync` directive."
    first = sync_lines[0]
    assert "--no-install-project" in first, (
        "The first `uv sync` (before src/ is copied) must use "
        "--no-install-project to skip installing the project itself. "
        f"Got: {first!r}"
    )


# ---------------------------------------------------------------------------
# Editable install + entrypoint
# ---------------------------------------------------------------------------


def test_editable_install_after_source_copy(dockerfile_lines: list[str]) -> None:
    """`uv pip install -e .` (or equivalent) must follow the src copy.

    The CLI entrypoint declared in pyproject.toml's [project.scripts]
    only resolves once the package is installed. Editable install keeps
    image size minimal (no duplicated source) and matches specialist-
    agent's pattern.
    """
    src_copy_idx = next(
        (
            idx
            for idx, line in enumerate(dockerfile_lines)
            if line.startswith("COPY")
            and ("study-tutor/src/" in line or "/src/" in line or " src/" in line)
            and "pyproject.toml" not in line
        ),
        -1,
    )
    editable_idx = next(
        (
            idx
            for idx, line in enumerate(dockerfile_lines)
            if "uv pip install" in line and " -e ." in line
        ),
        -1,
    )

    assert src_copy_idx != -1, "Expected a `COPY ... src/ ...` directive."
    assert editable_idx != -1, (
        "Expected `uv pip install ... -e .` to install the project in "
        "editable mode after src/ is copied."
    )
    assert editable_idx > src_copy_idx, (
        "Editable install must come AFTER src/ is copied; otherwise the "
        "package directory is empty when uv tries to register it."
    )


def test_path_includes_venv_bin(dockerfile_text: str) -> None:
    """The image's PATH must include the uv-managed venv's bin directory.

    Without this, ``docker run image study-tutor ...`` (the form used by
    the acceptance criteria) cannot find the console_script and fails
    with "command not found". `uv sync` creates ``.venv/`` inside the
    project directory by default.
    """
    assert re.search(
        r'ENV\s+PATH="?[^"\n]*\.venv/bin',
        dockerfile_text,
    ), (
        "Expected `ENV PATH=\"...venv/bin:...\"` so the study-tutor "
        "console_script is discoverable on PATH."
    )


def test_default_command_runs_serve_nats(dockerfile_text: str) -> None:
    """Default CMD must invoke ``study-tutor serve-nats``.

    The task body specifies this default. Using CMD (rather than
    ENTRYPOINT) keeps the form ``docker run image study-tutor serve-nats
    --help`` from the acceptance criteria working: the user-supplied
    args fully override CMD, so click sees a clean argv.
    """
    cmd_pattern = re.compile(
        r'^CMD\s+\[\s*"study-tutor"\s*,\s*"serve-nats"\s*\]',
        re.MULTILINE,
    )
    assert cmd_pattern.search(dockerfile_text), (
        'Expected `CMD ["study-tutor", "serve-nats"]` so the default '
        "container invocation runs the NATS subscriber. Using ENTRYPOINT "
        "would break the form `docker run image study-tutor serve-nats "
        "--help` exercised by the acceptance criteria."
    )


# ---------------------------------------------------------------------------
# Negative assertions — guard against regressions
# ---------------------------------------------------------------------------


def test_no_exposed_ports(dockerfile_text: str) -> None:
    """study-tutor is a NATS subscriber; it must not EXPOSE any ports.

    Spec: "Expose nothing (it's a NATS subscriber, not an HTTP service)."
    A stray EXPOSE directive would mislead operators reading docker
    inspect output.
    """
    assert not re.search(
        r"^EXPOSE\b",
        dockerfile_text,
        re.MULTILINE,
    ), (
        "Dockerfile must not contain an EXPOSE directive — study-tutor "
        "is a NATS subscriber, not an HTTP service."
    )


def test_no_baked_credentials(dockerfile_text: str) -> None:
    """No ENV directive may bake a real-looking secret into the image.

    Spec: "Do NOT bake credentials. Env vars come from runtime via
    docker-compose or --env-file." We guard against the obvious slip-ups
    (API keys, tokens, NATS creds set to a non-empty value).
    """
    forbidden_patterns = [
        # ENV KEY=value where value looks credential-shaped.
        re.compile(
            r"^ENV\s+\S*(?:API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)\S*\s*=\s*\S",
            re.MULTILINE | re.IGNORECASE,
        ),
        # ENV AGENT_NATS__URL=nats://user:pass@... — i.e. anything with
        # an embedded credential in a NATS URL.
        re.compile(
            r"^ENV\s+\S*NATS\S*\s*=\s*nats://[^\s@]+@",
            re.MULTILINE | re.IGNORECASE,
        ),
    ]
    for pattern in forbidden_patterns:
        match = pattern.search(dockerfile_text)
        assert match is None, (
            f"Dockerfile contains a baked credential-shaped ENV: "
            f"{match.group(0)!r}. Credentials must come from runtime "
            "via docker-compose or --env-file."
        )
