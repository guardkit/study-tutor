"""``study-tutor`` CLI entrypoint.

SR-01: stdout is reserved for MCP JSON-RPC traffic. Every banner, log line,
and diagnostic goes to stderr. The root logger is configured against
``sys.stderr`` and ``click.echo(..., err=True)`` is the only user-facing
output channel.

TASK-GR-WIRE BLOCK-3a: ``serve`` now constructs the Phase-1 session-end
dependencies (``GraphitiClient`` via ``get_client``, ``GraphitiWriteHelper``
wrapping the inner client, in-process ``EventBus``) and injects them into
the :class:`MCPAdapter`. The graceful-degradation envelope is preserved:
when ``get_client`` returns ``None`` (FalkorDB unreachable, graphiti-core
import failure, etc.) the write helper is constructed with ``client=None``
and every dispatch becomes a no-op — the tutor still serves Phase-0
``tutor_turn`` traffic without a knowledge graph behind it.

The runtime shutdown hook
(:func:`study_tutor.tutoring.session_end.runtime_shutdown`) is run after
``server.run`` exits so in-flight F3 fire-and-forget writes get the
configured drain window (ASSUM-011, default 5 s) before process exit.
"""
from __future__ import annotations

import asyncio
import logging
import sys

import click

from study_tutor.knowledge.async_write import GraphitiWriteHelper
from study_tutor.knowledge.graphiti_client import (
    get_client,
    load_graphiti_config_from_yaml,
)
from study_tutor.mcp.adapter import MCPAdapter
from study_tutor.mcp.server import create_mcp_server
from study_tutor.roles.loader import load_role
from study_tutor.tutoring.session_end import EventBus, runtime_shutdown


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

    # Graphiti client construction is async (it does a healthcheck), but
    # the FastMCP server.run loop is sync. We use a one-shot asyncio.run
    # for setup, then enter the sync server loop. The underlying
    # graphiti-core driver is loop-agnostic at construction time;
    # GraphitiWriteHelper.schedule_write picks up whatever loop is
    # running when the MCP handler dispatches.
    config = load_graphiti_config_from_yaml()
    wrapper = asyncio.run(get_client(config))
    inner = wrapper.client_or_none if wrapper is not None else None
    write_helper = GraphitiWriteHelper(client=inner)
    event_bus = EventBus()

    adapter = MCPAdapter(
        role_config=role_config,
        write_helper=write_helper,
        event_bus=event_bus,
        graphiti_client=wrapper,
    )
    server = create_mcp_server(role_config, adapter)

    click.echo(
        f"[study-tutor] Serving role '{role_config.id}' over {transport} "
        f"(provider resolved per-request via AGENT_MODELS__REASONING_MODEL; "
        f"graphiti={'connected' if wrapper is not None else 'degraded'}).",
        err=True,
    )

    try:
        server.run(transport=transport)
    finally:
        # Drain in-flight F3 writes (ASSUM-011 / GRAPHITI_DRAIN_WINDOW).
        # runtime_shutdown swallows its own exceptions — process exit
        # never blocks on a drain failure.
        asyncio.run(runtime_shutdown(write_helper))


if __name__ == "__main__":
    cli()
