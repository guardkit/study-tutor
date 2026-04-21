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
