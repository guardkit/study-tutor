"""Boundary adapters between the MCP layer and the tutoring core (FEAT-6CC5).

This package owns the typed boundary objects threaded through
``Player.respond``, ``Player.revise``, and ``Coach.evaluate`` and the LLM
adapters that consume them. The MCP layer constructs the typed
``SessionState`` here and hands it to ``PlayerCoachOrchestrator.run_turn``;
adapters narrow the type internally so the orchestrator's
``session_state: Any`` signature stays stable across the FEAT-6CC5 wave.
"""
