"""FastMCP server for the tutor role.

Registers exactly four tools whose descriptions encode their classification
(long-running vs sync) per the Phase-0 scope (SR-07).
"""
from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from study_tutor.mcp.adapter import MCPAdapter
from study_tutor.roles.loader import RoleConfig

logger = logging.getLogger(__name__)


def create_mcp_server(role_config: RoleConfig, adapter: MCPAdapter) -> FastMCP:
    """Build a FastMCP server with the four tutor tools registered."""
    server = FastMCP(
        name=f"{role_config.id}-agent",
        instructions=f"{role_config.name}: {role_config.description}",
    )

    server.add_tool(
        adapter.tutor_start_session,
        name="tutor_start_session",
        description=(
            "Start a new tutoring session for the given subject/topic. "
            "Long-running, returns session_id immediately; LLM model is "
            "warmed up in the background."
        ),
    )
    server.add_tool(
        adapter.tutor_turn,
        name="tutor_turn",
        description=(
            "Submit a user message for the given session_id and receive a "
            "tutor response. Sync, typically returns within 15s."
        ),
    )
    server.add_tool(
        adapter.tutor_session_status,
        name="tutor_session_status",
        description="Sync, returns current session state.",
    )
    server.add_tool(
        adapter.tutor_session_end,
        name="tutor_session_end",
        description="Marks session ended.",
    )

    logger.info(
        "MCP server '%s-agent' ready with 4 tools: "
        "tutor_start_session, tutor_turn, tutor_session_status, tutor_session_end",
        role_config.id,
    )
    return server
