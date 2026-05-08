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

TASK-LCA-005: ``serve`` constructs the Phase-1 ``orchestrator_factory``
closure via :func:`_build_orchestrator_factory` and injects it into the
:class:`MCPAdapter`. The closure is invoked **once** at the end of
``MCPAdapter.__init__`` (the TASK-LCA-004 boot smoke check) so any
structural misconfiguration — most importantly the D3 same-provider
rejection enforced by :func:`validate_coach_config` and the
unset-env-var rejection enforced by :func:`_default_coach_model` —
surfaces at server boot rather than at first user turn. Subsequent
``tutor_turn`` calls invoke the closure once per turn, which is the
**per-turn factory isolation invariant** (AC-LCA-01): each tutor turn
gets a fresh :class:`PlayerCoachOrchestrator` so two concurrent sessions
cannot contaminate each other's Coach observations.

The runtime shutdown hook
(:func:`study_tutor.tutoring.session_end.runtime_shutdown`) is run after
``server.run`` exits so in-flight F3 fire-and-forget writes get the
configured drain window (ASSUM-011, default 5 s) before process exit.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any, Callable

import click

from study_tutor.cli.rag_wiring import build_rag_providers
from study_tutor.knowledge.async_write import GraphitiWriteHelper
from study_tutor.knowledge.coach_handover import apply_quote_verification
from study_tutor.knowledge.graphiti_client import (
    get_client,
    load_graphiti_config_from_yaml,
)
from study_tutor.knowledge.quote_verifier import VerifierMetadata
from study_tutor.knowledge.retrieval import (
    decide_retrieval,
    get_last_retrieval_mode,
    retrieve,
)
from study_tutor.llm.client import _default_coach_model, _default_player_model
from study_tutor.mcp.adapter import MCPAdapter
from study_tutor.mcp.server import create_mcp_server
from study_tutor.roles.loader import RoleConfig, load_role
from study_tutor.tutoring.adapters.llm_coach_adapter import LLMCoachAdapter
from study_tutor.tutoring.adapters.llm_player_adapter import LLMPlayerAdapter
from study_tutor.tutoring.coach.factory import (
    CoachConfig,
    PlayerConfig,
    validate_coach_config,
)
from study_tutor.tutoring.orchestrator import (
    CoachHandover,
    PlayerCoachOrchestrator,
)
from study_tutor.tutoring.session_end import EventBus, runtime_shutdown

logger = logging.getLogger(__name__)


def _build_coach_handover() -> CoachHandover:
    """Construct the production coach-handover closure (TASK-RAG-002).

    The closure routes the four-branch retrieval decision into the
    verifier seam (:func:`apply_quote_verification`) on every Player
    turn:

    * No ``text_name`` on the session_state (baseline-degraded plan) —
      verifier runs against an empty corpus with
      ``retrieval_skipped_reason=None``; ``quote_fidelity`` defaults
      because there's nothing to ground against and no skip-reason to
      surface to the Coach.
    * ``decide_retrieval`` says skip (AO3-only / AnalysisMode /
      embedder-timeout) — verifier runs with empty chunks and the
      decision's ``reason`` forwarded to
      :class:`VerifierMetadata.retrieval_skipped_reason` so the Coach
      suppresses its ``quote_fidelity`` down-rank.
    * Decision says retrieve — :func:`retrieve` is called with the
      learner message as the query (matches the @key-example fixtures
      in TASK-PRV-004), the resulting chunks are passed to
      :func:`apply_quote_verification`, and the rewritten response goes
      to the Coach.

    Every branch emits a single structured ``event=orchestrator_turn_completed``
    log line so the demo log pane has a single filter for retrieval
    state (per plan AD-6).

    The closure is process-scoped (built once at boot) — same lifecycle
    as ``coach_system_prompt`` in :func:`_build_orchestrator_factory`.

    Returns
    -------
    CoachHandover
        A callable matching the widened :class:`CoachHandover` signature
        ``(raw_response, learner_message, session_state) -> (rewritten,
        metadata)``.
    """

    def coach_handover(
        raw_response: str,
        learner_message: str,
        session_state: Any,
    ) -> tuple[str, VerifierMetadata]:
        text_name = getattr(session_state, "text_name", None)
        focus_aos_raw = getattr(session_state, "focus_aos", ()) or ()
        focus_aos = set(focus_aos_raw)

        if not text_name:
            # Baseline-degraded plan with no text_name — verifier still
            # runs against empty chunks so quote_fidelity defaults
            # appropriately.
            logger.info(
                "event=orchestrator_turn_completed text_name=%s "
                "retrieval_mode=skipped reason=no_text_name",
                "",
            )
            return apply_quote_verification(
                raw_response, [], "", retrieval_skipped_reason=None
            )

        decision = decide_retrieval(text_name, focus_aos)
        if not decision.retrieve:
            logger.info(
                "event=orchestrator_turn_completed text_name=%s "
                "retrieval_mode=skipped reason=%s",
                text_name,
                decision.reason,
            )
            return apply_quote_verification(
                raw_response,
                [],
                text_name,
                retrieval_skipped_reason=decision.reason,
            )

        # TODO (TASK-RAG-002 / Phase 2 — AD-6): thread retrieval_mode
        # into TurnResult so consumers can read it without parsing logs.
        # Phase 1 demo signal is the structured log line below.
        chunks = retrieve(
            query=learner_message, text_name=text_name, focus_aos=focus_aos
        )
        retrieval_mode = get_last_retrieval_mode()
        logger.info(
            "event=orchestrator_turn_completed text_name=%s "
            "retrieval_mode=%s chunks=%d",
            text_name,
            retrieval_mode,
            len(chunks),
        )
        return apply_quote_verification(
            raw_response,
            chunks,
            text_name,
            retrieval_skipped_reason=None,
        )

    return coach_handover


def _build_orchestrator_factory(
    role_config: RoleConfig,
) -> Callable[[], PlayerCoachOrchestrator]:
    """Construct the per-turn ``orchestrator_factory`` closure (TASK-LCA-005).

    The returned closure builds a **fresh** :class:`PlayerCoachOrchestrator`
    on every call, with **freshly-constructed** :class:`LLMPlayerAdapter`
    and :class:`LLMCoachAdapter` instances. This is the load-bearing
    per-turn factory isolation invariant (AC-LCA-01): two concurrent
    ``tutor_turn`` invocations receive distinct orchestrator instances and
    cannot contaminate each other's Coach observations.

    The closure also enforces the D3 two-provider invariant (AC-LCA-08) at
    every invocation by calling :func:`validate_coach_config` with
    provider strings resolved at call time via
    :func:`_default_player_model` / :func:`_default_coach_model` (SR-03).
    Same-provider misconfiguration therefore surfaces at the boot smoke
    check inside :class:`MCPAdapter.__init__` (per TASK-LCA-004), not at
    first user turn.

    The ``coach_system_prompt`` is read **once at closure construction**
    rather than per call: the prompt is static for the lifetime of the
    process and reading the file on every turn would burn I/O for no
    runtime benefit. The closure still enforces the D2 non-empty-prompt
    invariant per turn because the cached prompt is forwarded into
    :func:`validate_coach_config` on every call.

    Args:
        role_config: Resolved role manifest (typically ``load_role("tutor")``).
            The coach prompt file referenced by the manifest is read
            here; a missing file surfaces as ``FileNotFoundError`` at
            closure-build time, before any session starts.

    Returns:
        A no-arg callable producing a fresh
        :class:`PlayerCoachOrchestrator` on each invocation.

    Raises:
        FileNotFoundError: If the coach prompt file referenced by
            ``role_config`` is missing or unreadable. Surfaces at
            closure-build time so a malformed role manifest fails fast.
    """
    # Read the coach system prompt once at boot so the per-turn closure
    # doesn't repeat disk I/O on every invocation. The prompt is static
    # for the lifetime of the process; rotation requires a server restart.
    coach_system_prompt = role_config.load_coach_prompt()

    # TASK-RAG-002 — build the coach-handover closure once at boot.
    # Same lifecycle as ``coach_system_prompt``: process-scoped, no
    # per-turn construction cost. The closure reads module-level state
    # in ``study_tutor.knowledge.retrieval`` (collection provider,
    # primary-text index) which is wired by ``build_rag_providers`` in
    # ``serve`` *before* this factory is constructed.
    coach_handover_closure = _build_coach_handover()

    def _on_flag(reason: str, extra: dict[str, Any]) -> None:
        """Logger-only flag callback (D-COACH-07).

        Emits a structured log line ``event=orchestrator_turn_flagged``
        to stderr (the configured log stream — see ``serve`` below) when
        a turn warrants session-end review. Per D-COACH-07 this Phase-1
        callback is observability-only: no DB write, no metric backend.
        Phase-2 may swap in a richer sink without changing the
        orchestrator's emit contract.
        """
        logger.warning(
            "event=orchestrator_turn_flagged reason=%s extra=%s",
            reason,
            extra,
        )

    def orchestrator_factory() -> PlayerCoachOrchestrator:
        """Build a fresh orchestrator per turn (per-turn isolation invariant)."""
        # SR-03 — resolve providers at call time so an operator who
        # rotates AGENT_MODELS__* and bounces the server picks up the
        # new value without code changes. ``_default_coach_model``
        # raises ``LLMProviderError`` if the env var is unset.
        player_provider = _default_player_model()
        coach_provider = _default_coach_model()
        # AC-LCA-08 — D3 same-provider rejection. Co-located validator
        # also enforces D1 (no tools) and D2 (non-empty system prompt).
        validate_coach_config(
            player_config=PlayerConfig(provider=player_provider),
            coach_config=CoachConfig(provider=coach_provider),
            system_prompt=coach_system_prompt,
            tools=None,
        )
        return PlayerCoachOrchestrator(
            player=LLMPlayerAdapter(role_config),
            coach=LLMCoachAdapter(role_config),
            quote_verifier=None,  # ASSUM-LCA-015 — follow-up subtask
            coach_handover=coach_handover_closure,
            on_flag=_on_flag,
        )

    return orchestrator_factory


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
    """Run the MCP server for the given role.

    \b
    Environment variables (DECISION-RAG-001 §3.1 — fleet-shared):

    \b
      CHROMA_PERSIST_DIR        Persistent ChromaDB directory.
                                Default: data/chroma
      CHROMA_COLLECTION         Collection name to open.
                                Default: gcse-english-v1
      LLM_EMBEDDINGS_BASE_URL   llama-swap OpenAI-compat endpoint.
                                Default: http://localhost:9000/v1
      LLM_EMBEDDINGS_API_KEY    API key (load-bearing magic string —
                                llama-swap ignores auth but the EF
                                rejects empty strings).
                                Default: not-needed
      LLM_EMBEDDINGS_MODEL      Embedding model name (llama-swap alias
                                for nomic-ai/nomic-embed-text-v1.5).
                                Default: nomic-embed
    """
    logging.basicConfig(
        level=log_level.upper(),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    role_config = load_role(role)

    # TASK-RAG-002 — wire the persistent ChromaDB collection into the
    # retrieval module's collection-provider seam *before* the
    # orchestrator factory is built. The boot-smoke check inside
    # ``MCPAdapter.__init__`` reads the wired provider via
    # ``get_collection_provider`` to verify wiring; that check would
    # see ``None`` if we wired RAG after adapter construction. On any
    # failure mode (chromadb missing / persist dir missing / EF
    # construction failure) the helper logs ``event=rag_disabled`` and
    # returns — the runtime continues with the verifier-against-empty
    # corpus fallback per the graceful-degradation envelope.
    build_rag_providers(role_config)

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

    # TASK-LCA-005 — orchestrator_factory closure. Built before adapter
    # construction so any closure-level wiring failure (missing coach
    # prompt file, etc.) surfaces here rather than from inside
    # MCPAdapter.__init__. The factory is invoked once at the end of
    # MCPAdapter.__init__ as the boot smoke check (TASK-LCA-004 /
    # AC-LCA-02 / AC-LCA-08), then once per ``tutor_turn`` for per-turn
    # isolation (AC-LCA-01).
    orchestrator_factory = _build_orchestrator_factory(role_config)

    adapter = MCPAdapter(
        role_config=role_config,
        orchestrator_factory=orchestrator_factory,
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
