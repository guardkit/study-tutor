# syntax=docker/dockerfile:1.7
#
# study-tutor container image (TASK-NATS-PH3-001 / FEAT-NATS).
#
# Mirrors the layering pattern of specialist-agent/Dockerfile so the two
# fleet members run side-by-side on GB10 with predictable cache behaviour.
# The notable divergence is that this Dockerfile uses BuildKit *named
# contexts* to source the sibling ``nats-core`` repository: the editable
# path source declared in ``[tool.uv.sources]`` (``../nats-core``) means
# uv expects to find ``nats-core`` next to ``study-tutor`` inside the
# image.
#
# Build (from a parent directory containing both study-tutor/ and
# nats-core/ as siblings):
#
#   docker build \
#     -f study-tutor/Dockerfile \
#     --build-context nats-core=../nats-core \
#     -t study-tutor:dev \
#     ..
#
# The wrapper at ``study-tutor/scripts/docker-build.sh`` (TASK-NATS-PH3-003)
# encapsulates the named-context wiring so callers don't need to remember
# the flag layout.
#
# Run (default CMD invokes ``study-tutor serve-nats``):
#
#   docker run --rm study-tutor:dev                       # serve-nats (default)
#   docker run --rm study-tutor:dev study-tutor --help    # CLI help
#   docker run --rm study-tutor:dev study-tutor serve-nats --help
#
# This image is a NATS subscriber, not an HTTP service — no ports are
# exposed. Credentials (NATS URL, model API keys, etc.) come from runtime
# env vars supplied via ``docker-compose`` (TASK-NATS-PH3-002) or
# ``--env-file``.
#
FROM python:3.11-slim AS base

# Standard Python container hygiene plus a uv hint that avoids hardlink
# warnings when the build cache lives on a different filesystem from
# /workspace (common on GB10 where the project directory is a bind mount).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

# Install uv. The pyproject.toml uses ``[tool.uv.sources]`` for the
# editable nats-core path source, so the dependency resolver MUST be uv —
# plain ``pip install`` would silently resolve ``nats-core`` from PyPI
# (the namespace conflict documented in pyproject.toml).
RUN pip install --no-cache-dir uv

# Place sibling nats-core at /workspace/nats-core so that uv's path
# source (``path = "../nats-core"``) resolves when uv runs from
# /workspace/study-tutor. The ``--from=nats-core`` segment is satisfied
# by ``--build-context nats-core=../nats-core`` on the docker build CLI.
WORKDIR /workspace
COPY --from=nats-core . /workspace/nats-core/

WORKDIR /workspace/study-tutor

# ---------------------------------------------------------------------------
# Layer 1 — dependency resolution
# ---------------------------------------------------------------------------
# Copy ONLY the lockfile and project metadata first so this layer is
# cached unless dependencies change. ``--no-install-project`` skips
# installing study-tutor itself (its src/ isn't in the image yet) but
# still installs nats-core via the path source above.
COPY study-tutor/pyproject.toml study-tutor/uv.lock ./
# Lane 2 step 1a (plan of record): include the [rag] extra (chromadb +
# sentence-transformers + openai) so build_rag_providers can wire the
# shipped data/chroma corpus instead of degrading with
# ``rag_disabled reason=chromadb_missing``.
RUN uv sync --frozen --no-dev --no-install-project --extra rag

# ---------------------------------------------------------------------------
# Layer 2 — application source + editable install
# ---------------------------------------------------------------------------
# Copy the package source and re-run sync so study-tutor itself is
# installed in editable mode. The ``study-tutor`` console_script declared
# in pyproject.toml resolves to the venv's bin/ directory after this
# step.
COPY study-tutor/src/ ./src/
COPY study-tutor/roles/ ./roles/
COPY study-tutor/data/ ./data/
RUN uv pip install --no-deps -e .

# Make the venv's bin/ first on PATH so callers can invoke
# ``study-tutor`` without going through ``uv run``.
ENV PATH="/workspace/study-tutor/.venv/bin:${PATH}"

# Default command: run the NATS service. Using CMD (rather than
# ENTRYPOINT) keeps the container ergonomic for ad-hoc invocations like
# ``docker run image which study-tutor`` or ``docker run image study-tutor
# serve-nats --help``, both of which the acceptance criteria exercise.
CMD ["study-tutor", "serve-nats"]
