#!/usr/bin/env bash
# study-tutor MCP wrapper (SR-02 locus).
#
# Claude Desktop spawns MCP servers with an unpredictable CWD. This wrapper:
#   1. cd's to the absolute repo root so role.yaml's relative paths resolve.
#   2. Sources .env for provider credentials/config (Ollama host, API keys).
#   3. Defaults AGENT_MODELS__REASONING_MODEL=local so Phase 0 stays on
#      the GB10 fine-tune even if the operator's shell doesn't export it.
#   4. exec's the venv-installed ``study-tutor serve`` so the process tree
#      stays flat and signals propagate cleanly.
set -euo pipefail

# SR-02: absolute path, not $PWD. Edit this to your local checkout.
REPO_ROOT="/Users/richardwoollcott/Projects/appmilla_github/study-tutor"

cd "$REPO_ROOT"

if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "$REPO_ROOT/.env"
  set +a
fi

export AGENT_MODELS__REASONING_MODEL="${AGENT_MODELS__REASONING_MODEL:-local}"

exec "$REPO_ROOT/.venv/bin/study-tutor" serve --role tutor --transport stdio
