# study-tutor

Fine-tuned English tutoring runtime — an MCP server that Claude Desktop calls
into for an interactive Player/Coach loop over GCSE English literature.

## Claude Desktop setup

Install the package into the repo's venv, then add the wrapper to your
`claude_desktop_config.json`:

```bash
cd /absolute/path/to/study-tutor
python -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env   # edit values
chmod +x scripts/mcp-wrapper.sh
```

```json
{
  "mcpServers": {
    "study-tutor": {
      "command": "/absolute/path/to/study-tutor/scripts/mcp-wrapper.sh"
    }
  }
}
```

Restart Claude Desktop. The `study-tutor` server should appear with
exactly four tools: `tutor_start_session`, `tutor_turn`,
`tutor_session_status`, `tutor_session_end`.

## Why the wrapper?

Claude Desktop spawns MCP servers with an unpredictable working directory.
`scripts/mcp-wrapper.sh` (SR-02):

1. `cd`'s to the absolute repo root so `roles/tutor/role.yaml`'s relative
   paths resolve.
2. Sources `.env` for provider credentials.
3. Defaults `AGENT_MODELS__REASONING_MODEL=local` (the GB10 fine-tune via
   Ollama) so the operator's shell environment isn't required.
4. `exec`'s `.venv/bin/study-tutor serve --role tutor --transport stdio`.

Stdout is reserved for MCP JSON-RPC (SR-01); all banners and logs go to
stderr.

## Pinning policy

When changing `requires-python` or any LangChain ecosystem pin in
`pyproject.toml`, see:

- **`docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`**
  — the verified-versions table and the rationale for each cap, with
  empirical evidence from a Python 3.14 install + test run.
- **`appmilla_github/guardkit/docs/guides/portfolio-python-pinning.md`**
  — the portfolio-wide guidance on why `requires-python` should not have a
  closed upper bound (origin incident: TASK-REV-FA04, the 33-minute
  autobuild stall caused by a stale `<3.13` cap excluding the active
  `/usr/local/bin/python3` 3.14).

Short version: open upper bound on Python; coherent same-major caps on
the LangChain ecosystem; verified versions table lives in the ADR and
gets updated when floors are lifted.
