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
import os
import signal
import sys
from typing import Any, Callable

import click

from study_tutor.cli.rag_wiring import build_rag_providers
from study_tutor.knowledge.store.wiring import build_student_store
from study_tutor.session.provider import get_session_service
from study_tutor.session.wiring import build_session_service
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
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
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

    # TASK-SMP2-04 — wire the Postgres student store into the runtime
    # *before* the orchestrator starts, so learner-state reads are live
    # when STUDY_TUTOR_PG_DSN is set. When the DSN is absent, skip wiring
    # (reads degrade to empty — same posture as the graph-read graceful
    # fallback). The guard belongs here (not inside build_student_store)
    # so the write path can still demand a hard failure elsewhere if
    # needed.
    logger = logging.getLogger(__name__)
    if os.environ.get("STUDY_TUTOR_PG_DSN"):
        build_student_store()
        logger.info("event=student_store_wired")
        # TASK-SMP3-04 — wire the SessionService after the store is wired
        build_session_service()
        logger.info("event=session_service_wired")
    else:
        logger.info("event=student_store_skipped reason=no_dsn")
        logger.info("event=session_service_skipped reason=no_dsn")

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
        session_service=get_session_service(),
        orchestrator_factory=orchestrator_factory,
        event_bus=event_bus,
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


# ---------------------------------------------------------------------------
# serve-nats subcommand (TASK-NATS-PH1-006)
# ---------------------------------------------------------------------------
#
# Wires the existing tutor stack into a long-running NATS fleet service.
# Mirrors specialist-agent's ``serve-nats`` subcommand
# (``specialist-agent/src/specialist_agent/cli/main.py:1515-1769``).
#
# Architecture: command envelope arrives on ``agents.command.<agent_id>``
# → :class:`NATSAdapter` (lifecycle + subscription) hands it to
# :class:`CommandRouter` (alias resolution, dispatch, reply_to honouring)
# which calls into the existing :class:`MCPAdapter` business logic.
#
# Lazy imports: TASK-NATS-PH1-004 (CommandRouter) and TASK-NATS-PH1-005
# (NATSAdapter) ship after this CLI lands. The runtime imports inside
# :func:`_build_nats_runtime` keep the module-load path clean so
# ``study-tutor serve`` (the existing stdio MCP path) is unaffected if
# either downstream module is in flight.


class _AgentConfigValidationError(RuntimeError):
    """Wraps a failure constructing :class:`nats_core.AgentConfig`.

    Carries the original pydantic / pydantic-settings validation error
    so the CLI can surface a single, prefixed error line that includes
    the underlying field names (e.g. ``AGENT_MODELS__REASONING_MODEL``)
    without leaking the entire pydantic stack trace into stderr.
    """

    def __init__(self, cause: BaseException) -> None:
        self.cause = cause
        super().__init__(str(cause))


def _load_agent_config() -> Any:
    """Load :class:`nats_core.AgentConfig` from the process environment.

    Wraps any construction failure in :class:`_AgentConfigValidationError`
    so the CLI can convert a missing-env-var or invalid-URL error into a
    non-zero exit with a single ``except`` arm. The lazy import keeps
    the module-load path of ``study_tutor.cli.main`` independent of
    nats-core's import-time side effects (pydantic-settings reads the
    environment eagerly when ``AgentConfig()`` is instantiated).

    Returns:
        A populated ``AgentConfig`` instance.

    Raises:
        _AgentConfigValidationError: If construction fails for any
            reason (missing required fields, invalid types, invalid
            ``NATS_URL`` shape, etc.).
    """
    from nats_core.agent_config import AgentConfig

    try:
        return AgentConfig()
    except Exception as exc:  # noqa: BLE001 — re-raised as a typed wrapper
        raise _AgentConfigValidationError(exc) from exc


def _build_nats_runtime(config: Any, agent_id: str) -> tuple[Any, Any]:
    """Wire MCPAdapter → CommandRouter → NATSAdapter for the tutor role.

    Mirrors :func:`serve` for the tutor-side wiring (RAG providers,
    Graphiti client, write helper, event bus, orchestrator factory,
    :class:`MCPAdapter`) and then layers the NATS plumbing on top:

    1. :func:`_tutor_manifest_factory` — produces the manifest published
       to ``agent-registry`` at adapter start.
    2. :class:`NATSClient` — typed publish/subscribe channel reused by
       the router for ``reply_to`` raw publishes (Bug #1 fix).
    3. :class:`CommandRouter` — translates incoming
       :class:`CommandPayload` envelopes into ``MCPAdapter.tutor_*``
       calls; reads ``tool_to_command`` from the role registry so the
       Bug #2 alias map stays single-sourced.
    4. :class:`NATSAdapter` — owns the lifecycle (connect, register,
       heartbeat, subscribe, drain, deregister, disconnect).

    Args:
        config: Validated :class:`AgentConfig` (caller is responsible
            for any CLI-flag overrides like ``config.nats.url``).
        agent_id: Manifest agent identifier (kebab-case;
            :func:`_tutor_manifest_factory` enforces the format).

    Returns:
        Tuple of ``(adapter, write_helper)``. The write helper is
        returned so :func:`_serve_adapter` can hand it to
        :func:`runtime_shutdown` for the F3 drain on the way out.

    Raises:
        ImportError: If TASK-NATS-PH1-004 / TASK-NATS-PH1-005 modules
            have not been merged yet — the lazy import surfaces a
            clear failure mode rather than a cryptic ``AttributeError``.
    """
    from nats_core.client import NATSClient

    from study_tutor.adapters.command_router import CommandRouter
    from study_tutor.adapters.manifest import _tutor_manifest_factory
    from study_tutor.adapters.nats_adapter import NATSAdapter
    from study_tutor.roles.registry import get_role

    manifest = _tutor_manifest_factory(agent_id)
    role_config = load_role("tutor")

    # RAG wiring must happen before MCPAdapter construction — the boot
    # smoke check inside ``MCPAdapter.__init__`` reads the wired
    # collection provider via ``get_collection_provider`` (see ``serve``
    # above for the same ordering invariant).
    build_rag_providers(role_config)

    # TASK-SMP3-04 — wire the Postgres student store and SessionService
    # into the NATS runtime path (same conditional posture as ``serve``).
    # The SessionService needs the store wired first, so build_student_store
    # is called before build_session_service.
    logger = logging.getLogger(__name__)
    if os.environ.get("STUDY_TUTOR_PG_DSN"):
        build_student_store()
        logger.info("event=student_store_wired path=nats")
        build_session_service()
        logger.info("event=session_service_wired path=nats")
    else:
        logger.info("event=student_store_skipped reason=no_dsn path=nats")
        logger.info("event=session_service_skipped reason=no_dsn path=nats")

    # Graphiti client construction is async (it does a healthcheck); we
    # use a one-shot ``asyncio.run`` here because :func:`_build_nats_runtime`
    # itself is sync and ``serve`` uses the same pattern.
    graphiti_cfg = load_graphiti_config_from_yaml()
    wrapper = asyncio.run(get_client(graphiti_cfg))
    inner = wrapper.client_or_none if wrapper is not None else None
    write_helper = GraphitiWriteHelper(client=inner)
    event_bus = EventBus()
    orchestrator_factory = _build_orchestrator_factory(role_config)

    mcp_adapter = MCPAdapter(
        role_config=role_config,
        session_service=get_session_service(),
        orchestrator_factory=orchestrator_factory,
        event_bus=event_bus,
    )

    role_entry = get_role("tutor")
    nats_client = NATSClient(config.nats, source_id=agent_id)
    router = CommandRouter(
        mcp_adapter=mcp_adapter,
        tool_to_command=role_entry.tool_to_command,
        agent_id=agent_id,
        client=nats_client,
    )
    adapter = NATSAdapter(config, manifest, command_router=router)
    return adapter, write_helper


async def _serve_adapter(
    adapter: Any,
    write_helper: Any,
    *,
    agent_id: str,
    nats_url: str,
    shutdown_event: asyncio.Event | None = None,
) -> None:
    """Run the NATS adapter lifecycle until SIGTERM / SIGINT.

    Implements the run-forever loop described in the task scope:

    1. ``await adapter.start()`` — connect, register, subscribe,
       heartbeat, set ``_ready``. If start fails the process exits 1
       and ``stop()`` is still attempted (best effort) so any partial
       connection is released.
    2. Install signal handlers for ``SIGTERM`` (supervisor shutdown,
       Docker SIGTERM, systemd ``TERM``) and ``SIGINT`` (Ctrl-C). Both
       set the shared ``shutdown_event``. The ``NotImplementedError``
       fallback matches Windows / non-default-loop platforms — the
       caller can still drive shutdown via the injected event in tests.
    3. ``await shutdown_event.wait()`` — block here until a signal
       arrives.
    4. ``await adapter.stop()`` — drain in-flight, cancel heartbeat,
       deregister, disconnect (TASK-NATS-PH1-005 owns the 30 s drain
       window so AC-003 holds without timing logic in this layer).
    5. ``await runtime_shutdown(write_helper)`` — drain in-flight F3
       graphiti writes (mirrors ``serve``'s shutdown path).

    Args:
        adapter: The :class:`NATSAdapter` instance.
        write_helper: The :class:`GraphitiWriteHelper` to drain on exit.
        agent_id: For the human-facing banner only.
        nats_url: For the banner only.
        shutdown_event: Optional pre-built event. Tests pass one in so
            they can drive shutdown without sending real signals; the
            CLI path leaves it as ``None`` and we build a fresh event
            here.

    Raises:
        SystemExit: With code 1 on a start failure (after attempting a
            clean ``stop()``).
    """
    if shutdown_event is None:
        shutdown_event = asyncio.Event()

    def _request_shutdown() -> None:
        """Signal handler — set the event so the wait returns."""
        shutdown_event.set()

    try:
        await adapter.start()
    except Exception as exc:
        click.echo(
            f"[study-tutor] Error: failed to start NATSAdapter: {exc}",
            err=True,
        )
        try:
            await adapter.stop()
        except Exception:
            # Best-effort cleanup — the start failure is the load-bearing
            # error to surface; a stop failure on a half-started adapter
            # is noise compared to the real cause.
            logger.exception("event=nats_serve_stop_after_start_failure")
        raise SystemExit(1) from exc

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            # Windows / non-default loops: tests still set the event
            # directly so this branch does not affect the AC-003 path.
            pass

    click.echo(
        f"[study-tutor] Serving via NATS as agent_id={agent_id} "
        f"url={nats_url}. Press Ctrl+C to stop.",
        err=True,
    )

    # TASK-NATS-FIX-006: race the shutdown signal against the adapter's
    # terminal-close event so a prolonged broker outage (nats-py exhausts
    # its reconnect budget) drives a non-zero exit. Without this, a
    # broken broker leaves the container ``Up`` but absent from the
    # ``agent-registry`` KV — fleet orchestration silently fails.
    terminal_close_triggered = False
    try:
        shutdown_task = asyncio.create_task(
            shutdown_event.wait(), name="serve-shutdown-wait"
        )
        terminal_close_task = asyncio.create_task(
            adapter.terminal_close_event.wait(), name="serve-terminal-close-wait"
        )
        try:
            _done, pending = await asyncio.wait(
                {shutdown_task, terminal_close_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            for pending_task in (shutdown_task, terminal_close_task):
                if not pending_task.done():
                    pending_task.cancel()
                    try:
                        await pending_task
                    except (asyncio.CancelledError, Exception):
                        pass
        terminal_close_triggered = adapter.terminal_close_event.is_set()
    finally:
        try:
            await adapter.stop()
        finally:
            try:
                await runtime_shutdown(write_helper)
            except Exception:
                # ``runtime_shutdown`` already swallows its own errors
                # in production code; the outer guard is here so a
                # MagicMock in unit tests cannot break the shutdown path.
                logger.exception("event=nats_serve_runtime_shutdown_error")

    if terminal_close_triggered:
        # Exit non-zero so Docker's restart policy (or systemd's
        # `Restart=` directive) recovers the container. AC-07 of
        # TASK-NATS-FIX-006: prolonged broker outage must surface as a
        # process exit, not a stuck-but-running container.
        raise SystemExit(1)


@cli.command("serve-nats")
@click.option(
    "--nats",
    "nats_url",
    default=None,
    show_default=False,
    help=(
        "NATS server URL (e.g. nats://localhost:4222). When provided, "
        "overrides the AGENT_NATS__URL environment variable."
    ),
)
@click.option(
    "--agent-id",
    default="gcse-tutor",
    show_default=True,
    help=(
        "Agent ID published in the manifest. Must be kebab-case "
        "(regex ^[a-z][a-z0-9-]*$)."
    ),
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    show_default=True,
    help="Root logger level.",
)
def serve_nats(nats_url: str | None, agent_id: str, log_level: str) -> None:
    """Run the tutor as a NATS fleet service.

    \b
    Loads ``AgentConfig`` from the environment, builds the manifest via
    ``_tutor_manifest_factory``, instantiates ``MCPAdapter`` →
    ``CommandRouter`` → ``NATSAdapter``, and blocks on the run-forever
    loop until ``SIGTERM`` / ``SIGINT`` arrives.

    \b
    Environment variables (a non-exhaustive selection — see
    ``nats_core.AgentConfig`` for the full surface):

    \b
      AGENT_MODELS__REASONING_MODEL  Required. LLM provider for the
                                     reasoning / orchestration model.
      AGENT_NATS__URL                NATS server URL (overridden by
                                     ``--nats`` when provided).
      AGENT_HEARTBEAT_INTERVAL_SECONDS
                                     Heartbeat cadence; default 30.
    """
    logging.basicConfig(
        level=log_level.upper(),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        config = _load_agent_config()
    except _AgentConfigValidationError as exc:
        click.echo(
            f"[study-tutor] Error: AgentConfig validation failed: {exc.cause}",
            err=True,
        )
        raise SystemExit(1) from exc

    if nats_url is not None:
        # CLI flag wins over the env-var-sourced default. Mutating the
        # validated config in-place mirrors specialist-agent's pattern
        # (cli/main.py:1578) and keeps the config object as the single
        # source of truth handed downstream.
        config.nats.url = nats_url

    adapter, write_helper = _build_nats_runtime(config, agent_id)
    asyncio.run(
        _serve_adapter(
            adapter,
            write_helper,
            agent_id=agent_id,
            nats_url=config.nats.url,
        )
    )


@cli.command("serve-http")
@click.option(
    "--port",
    default=8100,
    show_default=True,
    type=int,
    help="HTTP port to bind on",
)
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Host interface to bind on",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    show_default=True,
    help="Root logger level.",
)
def serve_http(port: int, host: str, log_level: str) -> None:
    """Run the HTTP session API server (TASK-APP1-04).

    \b
    Boots the TASK-APP1-03 Starlette app on uvicorn with production wiring:
    - Postgres store (STUDY_TUTOR_PG_DSN required — fail fast if missing)
    - Shared tutor loop (reuses _build_orchestrator_factory)
    - EventBus for session lifecycle events
    - /healthz READY endpoint

    \b
    Environment variables:

    \b
      STUDY_TUTOR_PG_DSN        Required. PostgreSQL connection string.
      STUDY_TUTOR_HTTP_TOKENS   Required. JSON token→student_id mapping.
      STUDY_TUTOR_HTTP_DEV_RESET
                                Dev reset flag (true/false).
      AGENT_MODELS__REASONING_MODEL
                                Required. LLM provider for reasoning model.
    """
    import uvicorn

    logging.basicConfig(
        level=log_level.upper(),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # AC-002: Fail fast if STUDY_TUTOR_PG_DSN is missing
    dsn = os.environ.get("STUDY_TUTOR_PG_DSN")
    if not dsn:
        click.echo(
            "[study-tutor] Error: STUDY_TUTOR_PG_DSN environment variable is required "
            "for serve-http. The Postgres store must be available before serving "
            "HTTP traffic.",
            err=True,
        )
        raise SystemExit(1)

    # AC-002: Fail fast if store is unreachable
    # Wire the Postgres store and SessionService (same pattern as serve/serve-nats)
    try:
        build_student_store()
        logger.info("event=student_store_wired path=http")
        build_session_service()
        logger.info("event=session_service_wired path=http")
    except Exception as exc:
        click.echo(
            f"[study-tutor] Error: Failed to connect to Postgres store: {exc}",
            err=True,
        )
        raise SystemExit(1) from exc

    # Wire RAG providers (same pattern as serve)
    role_config = load_role("tutor")
    build_rag_providers(role_config)

    # AC-003: Build the shared orchestrator factory (no duplication)
    orchestrator_factory = _build_orchestrator_factory(role_config)

    # AC-005: EventBus available for future session lifecycle event wiring
    # (following serve/serve-nats pattern; not yet integrated with HTTP adapter)
    _event_bus = EventBus()  # noqa: F841 - Reserved for future wiring

    # Build reply_fn closure that uses the shared orchestrator
    async def reply_fn(user_message: str) -> Any:
        """Tutor reply function using shared orchestrator factory.

        This closure is injected into SessionService.turn and uses the
        exact same orchestrator construction as the MCP adapter (AC-003).

        Args:
            user_message: Learner input message.

        Returns:
            TutorReply with tutor response.

        Raises:
            Any exception from the orchestrator (caught by HTTP layer).
        """
        from study_tutor.session.service import TutorReply

        orchestrator = orchestrator_factory()
        # TODO: Wire actual session state when available
        session_state = None
        result = await orchestrator.orchestrate(
            learner_message=user_message,
            session_state=session_state,
        )
        return TutorReply(response=result.response)

    # Wire HTTP auth config
    from study_tutor.http.auth import HTTPAuthConfig

    tokens_json = os.environ.get("STUDY_TUTOR_HTTP_TOKENS", "{}")
    dev_reset_str = os.environ.get("STUDY_TUTOR_HTTP_DEV_RESET", "false")

    try:
        auth_config = HTTPAuthConfig.from_env(
            tokens_json=tokens_json,
            dev_reset=dev_reset_str,
        )
    except ValueError as exc:
        click.echo(
            f"[study-tutor] Error: HTTP auth configuration failed: {exc}",
            err=True,
        )
        raise SystemExit(1) from exc

    # Get student store provider
    from study_tutor.knowledge.store.provider import get_student_store

    student_store = get_student_store()
    if student_store is None:
        click.echo(
            "[study-tutor] Error: Student store not available. "
            "Ensure build_student_store() succeeded.",
            err=True,
        )
        raise SystemExit(1)

    # Create the Starlette app with all production dependencies
    from study_tutor.http.app import create_app

    app = create_app(
        service=get_session_service(),
        reply_fn=reply_fn,
        auth_config=auth_config,
        student_store=student_store,
    )

    click.echo(
        f"[study-tutor] Serving HTTP API on {host}:{port} "
        f"(health check at /healthz). Press Ctrl+C to stop.",
        err=True,
    )

    # AC-001: Run uvicorn with the production-wired app
    uvicorn.run(app, host=host, port=port, log_level=log_level.lower())


@cli.command("seed-students")
@click.option(
    "--student-ids",
    default=None,
    help="Comma-separated student IDs to seed (default: from token table)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    show_default=True,
)
def seed_students(student_ids: str | None, log_level: str) -> None:
    """Seed student identity rows idempotently (TASK-APP1-05).

    Inserts student rows with ON CONFLICT DO NOTHING semantics. Identity rows
    ONLY — does not touch topic_confidence or other learner state (baseline
    seeding stays with FEAT-SMP-004).

    \b
    Environment variables:

    \b
      STUDY_TUTOR_PG_DSN        Required. PostgreSQL connection string.
      STUDY_TUTOR_HTTP_TOKENS   Optional. JSON token→student_id mapping.
                                Used as default student ID list when --student-ids is omitted.

    \b
    Examples:
      # Seed students from token table (default)
      study-tutor seed-students

      # Seed specific students
      study-tutor seed-students --student-ids=lilymay,bobsmith
    """
    import asyncio
    import json

    logging.basicConfig(
        level=log_level.upper(),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # AC-002: Fail fast if STUDY_TUTOR_PG_DSN is missing
    dsn = os.environ.get("STUDY_TUTOR_PG_DSN")
    if not dsn:
        click.echo(
            "[study-tutor] Error: STUDY_TUTOR_PG_DSN environment variable is required "
            "for seed-students. Set the PostgreSQL connection string first.",
            err=True,
        )
        raise SystemExit(1)

    # Determine student IDs to seed
    if student_ids:
        # Use explicit CLI argument
        ids_to_seed = [sid.strip() for sid in student_ids.split(",")]
    else:
        # Default: extract from token table
        tokens_json = os.environ.get("STUDY_TUTOR_HTTP_TOKENS", "{}")
        try:
            token_map = json.loads(tokens_json)
            if not isinstance(token_map, dict):
                click.echo(
                    "[study-tutor] Error: STUDY_TUTOR_HTTP_TOKENS must be a JSON object.",
                    err=True,
                )
                raise SystemExit(1)
            ids_to_seed = list(set(token_map.values()))  # Unique student IDs
        except json.JSONDecodeError as exc:
            click.echo(
                f"[study-tutor] Error: Failed to parse STUDY_TUTOR_HTTP_TOKENS: {exc}",
                err=True,
            )
            raise SystemExit(1)

    if not ids_to_seed:
        click.echo(
            "[study-tutor] Error: No student IDs to seed. "
            "Provide --student-ids or set STUDY_TUTOR_HTTP_TOKENS.",
            err=True,
        )
        raise SystemExit(1)

    # Wire the student store
    try:
        build_student_store()
        logger.info("event=student_store_wired path=seed")
    except Exception as exc:
        click.echo(
            f"[study-tutor] Error: Failed to connect to Postgres store: {exc}",
            err=True,
        )
        raise SystemExit(1) from exc

    # Get the store instance
    from study_tutor.knowledge.store.provider import get_student_store

    store = get_student_store()
    if store is None:
        click.echo(
            "[study-tutor] Error: Student store not available after wiring.",
            err=True,
        )
        raise SystemExit(1)

    # Seed each student (idempotent)
    async def _seed_all() -> tuple[int, int]:
        """Seed all students and return (inserted_count, skipped_count)."""
        inserted = 0
        skipped = 0

        for student_id in ids_to_seed:
            # Default profile values (production should load from config)
            was_inserted = await store.seed_student(
                student_id,
                name=student_id.title(),  # Default: capitalize ID as name
                year_group=10,
                target_grade="7",
            )

            if was_inserted:
                inserted += 1
                logger.info("event=student_seeded student_id=%s", student_id)
            else:
                skipped += 1
                logger.info("event=student_already_exists student_id=%s", student_id)

        return inserted, skipped

    # Run async seeding
    inserted_count, skipped_count = asyncio.run(_seed_all())

    click.echo(
        f"[study-tutor] Seeded {inserted_count} students, "
        f"{skipped_count} already existed (idempotent).",
        err=True,
    )


if __name__ == "__main__":
    cli()
