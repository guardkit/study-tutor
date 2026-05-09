#!/usr/bin/env bash
# Build the study-tutor Docker image (TASK-NATS-PH3-003 / FEAT-NATS).
#
# Mirrors specialist-agent/scripts/docker-build.sh: resolves the script's
# own location, sets the build context to the parent directory (which must
# contain study-tutor/ and nats-core/ as siblings), and wires up the
# BuildKit named context that study-tutor's Dockerfile expects.
#
# Run from anywhere — the script normalises to absolute paths:
#
#   ./scripts/docker-build.sh                # study-tutor:latest
#   TAG=dev ./scripts/docker-build.sh        # study-tutor:dev
#   ./scripts/docker-build.sh --no-cache     # extra args forwarded to docker
#
# Environment variables:
#   TAG  Image tag suffix after ``study-tutor:``. Default: ``latest``.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PARENT_DIR="$(cd "${REPO_DIR}/.." && pwd)"
NATS_CORE_DIR="${PARENT_DIR}/nats-core"

# Verify sibling nats-core exists. The Dockerfile uses BuildKit named
# contexts (``COPY --from=nats-core``), so the path must resolve before
# we hand off to docker build — otherwise the failure surfaces deep in
# layer 0 with a confusing message.
if [[ ! -d "${NATS_CORE_DIR}" ]]; then
  echo "ERROR: sibling nats-core/ not found at ${NATS_CORE_DIR}" >&2
  echo "       Both study-tutor/ and nats-core/ must be cloned under the same parent." >&2
  exit 1
fi

TAG="${TAG:-latest}"
IMAGE="study-tutor:${TAG}"

echo "Building ${IMAGE}"
echo "  Build context : ${PARENT_DIR}"
echo "  Dockerfile    : ${REPO_DIR}/Dockerfile"
echo "  nats-core ctx : ${NATS_CORE_DIR}"

DOCKER_BUILDKIT=1 docker build \
  -t "${IMAGE}" \
  -f "${REPO_DIR}/Dockerfile" \
  --build-context "nats-core=${NATS_CORE_DIR}" \
  "$@" \
  "${PARENT_DIR}"
