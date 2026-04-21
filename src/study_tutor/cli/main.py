"""``study-tutor`` CLI entrypoint.

SR-01: stdout is reserved for MCP JSON-RPC traffic. Every banner, log line,
and diagnostic goes to stderr. The root logger is configured against
``sys.stderr`` and ``click.echo(..., err=True)`` is the only user-facing
output channel.
"""
from __future__ import annotations

import logging
import sys

import click

from study_tutor.mcp.adapter import MCPAdapter
from study_tutor.mcp.server import create_mcp_server
from study_tutor.roles.loader import load_role


@click.group()
def cli() -> None:
    """study-tutor — fine-tuned English tutoring MCP runtime."""


@cli.command()
@click.option(
    "--role",
    default="tutor",
    show_default=True,
    help="Role manifest under roles/<role>/role.yaml",
)
@click.option(
    "--transport",
    type=click.Choice(["stdio"]),
    default="stdio",
    show_default=True,
    help="MCP transport. Phase 0 supports stdio only.",
)
@click.option(
    "--log-level",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False
    ),
    default="INFO",
    show_default=True,
)
def serve(role: str, transport: str, log_level: str) -> None:
    """Run the MCP server for the given role."""
    logging.basicConfig(
        level=log_level.upper(),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    role_config = load_role(role)
    adapter = MCPAdapter(role_config=role_config)
    server = create_mcp_server(role_config, adapter)

    click.echo(
        f"[study-tutor] Serving role '{role_config.id}' over {transport} "
        f"(provider resolved per-request via AGENT_MODELS__REASONING_MODEL).",
        err=True,
    )

    server.run(transport=transport)


if __name__ == "__main__":
    cli()
