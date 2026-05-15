"""CommandRouter — translates ``CommandPayload`` envelopes into MCPAdapter calls.

Built for TASK-NATS-PH1-004 and hand-recovered in TASK-NATS-FIX-004 after
FEAT-39E1 autobuild run-3 silently lost the prior implementation to a
``.gitignore`` mismatch (root cause analysis: TASK-REV-F30A).

Two load-bearing fixes ship from day one:

1. **Bug #2 — alias resolution.** Incoming command names like
   ``tutor_start_session`` (the MCP tool name) resolve to canonical commands
   like ``start_session`` via ``self.tool_to_command.get(c, c)`` *before* the
   dispatch table lookup. Canonical names absent from ``tool_to_command`` fall
   through unchanged (passthrough).
2. **Bug #1 — reply_to honouring.** When the inbound envelope carries a
   ``reply_to`` inbox, the result is raw-published to that inbox via
   ``client.publish_raw`` *in addition to* the canonical envelope publish on
   ``agents.result.<agent_id>``. Without this, ``jarvis``'s ``client.request()``
   future resolves with the JetStream PubAck instead of the actual result.

The ``tool_to_command`` map is the **single source of truth** held in
:mod:`study_tutor.roles.tutor` and read out via
``get_role("tutor").tool_to_command``; the router never inlines its own copy.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Mapping, Optional

from nats_core.envelope import EventType, MessageEnvelope
from nats_core.events._agent import CommandPayload, ResultPayload
from nats_core.topics import Topics

from study_tutor.mcp.adapter import MCPAdapter

logger = logging.getLogger(__name__)


class UnsupportedCommandError(KeyError):
    """Raised by :meth:`CommandRouter._dispatch_command` for unknown commands.

    Subclasses :class:`KeyError` so callers using ``except KeyError`` still
    catch it. The error message lists the sorted set of supported canonical
    command names so the operator can see at a glance which dispatch keys
    exist and what was actually requested.
    """

    def __init__(self, command: str, supported: list[str]) -> None:
        self.command = command
        self.supported = supported
        super().__init__(
            f"Unsupported command {command!r}. Supported commands: {supported}"
        )


class CommandRouter:
    """Dispatch ``CommandPayload`` envelopes to ``MCPAdapter`` business logic.

    Args:
        mcp_adapter: The role-bound MCP adapter that owns the actual tutor
            session methods (``tutor_start_session`` etc.).
        tool_to_command: Read-only mapping from MCP tool names to canonical
            internal command names. Sourced from
            ``study_tutor.roles.registry.get_role("tutor").tool_to_command``.
        agent_id: Fleet-unique agent identifier (e.g. ``"gcse-tutor"``).
            Used to resolve the canonical result topic
            (``agents.result.<agent_id>``) and as ``source_id`` on outbound
            envelopes.
        client: NATS client exposing ``publish`` (envelope-wrapped) and
            ``publish_raw`` (bytes only).
        adapter_ready: Optional readiness gate (TASK-NATS-PH2-001). When
            supplied and not set, ``on_command`` returns
            ``ResultPayload(success=False, error_type="AdapterNotReady")``
            without invoking the MCP handler — and still publishes the reply
            so a ``client.request()`` future never hangs. The adapter passes
            its own ``_ready`` event here. Pass ``None`` (default) to disable
            gating in tests / pre-PH2-001 callers.
    """

    def __init__(
        self,
        mcp_adapter: MCPAdapter,
        tool_to_command: Mapping[str, str],
        agent_id: str,
        client: Any,
        adapter_ready: Optional[asyncio.Event] = None,
    ) -> None:
        self.mcp_adapter = mcp_adapter
        self.tool_to_command = tool_to_command
        self.agent_id = agent_id
        self.client = client
        self._adapter_ready = adapter_ready

        # Dispatch table keyed by canonical internal command names.
        # Bug #2 alias resolution (``tool_to_command.get(c, c)``) runs
        # *before* this lookup, so the keys here are the post-resolution
        # canonical names — never the MCP tool names.
        self._command_map: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
            "start_session": self.mcp_adapter.tutor_start_session,
            "tutor_turn": self.mcp_adapter.tutor_turn,
            "session_status": self.mcp_adapter.tutor_session_status,
            "end_session": self.mcp_adapter.tutor_session_end,
        }

        # Argument-name aliasing — companion to Bug #2's command-name
        # aliasing. Small local supervisor models (e.g. qwen36-workhorse)
        # occasionally emit a shortened parameter name despite the
        # advertised tool schema: ``topic`` for ``topic_override``. Without
        # this fold, a single dropped suffix raises ``TypeError: got an
        # unexpected keyword argument`` and collapses the whole dispatch.
        # Keyed by canonical (post-Bug-#2-resolution) command name;
        # ``{alias: canonical_kwarg}``.
        self._arg_aliases: dict[str, dict[str, str]] = {
            "start_session": {"topic": "topic_override"},
        }

    async def on_command(
        self,
        envelope: MessageEnvelope,
        reply_to: str | None = None,
    ) -> None:
        """Handle one inbound command envelope.

        Parses the envelope payload as a :class:`CommandPayload`, dispatches
        it via :meth:`_dispatch_command` (with Bug #2 alias resolution),
        wraps the outcome in a :class:`ResultPayload`, and hands it to
        :meth:`_publish_result` for the dual-publish (Bug #1).

        Never raises: handler exceptions and unknown commands are caught at
        the dispatch boundary and surfaced as ``ResultPayload(success=False,
        ...)`` so the request/reply future on the requester side always
        resolves.
        """
        try:
            command = CommandPayload.model_validate(envelope.payload)
        except Exception:  # noqa: BLE001 — envelope source is untrusted wire data
            logger.exception(
                "Failed to parse CommandPayload from envelope %s", envelope.message_id
            )
            return

        # TASK-NATS-PH2-001 readiness gating: fail fast with a clear error
        # rather than queuing commands while the adapter is starting up. The
        # reply path (Bug #1 dual-publish) is still honoured so the requester's
        # ``client.request()`` future never hangs.
        if self._adapter_ready is not None and not self._adapter_ready.is_set():
            not_ready_payload = ResultPayload(
                command=command.command,
                result={
                    "error": (
                        f"Adapter not ready: {self.agent_id} is starting up; "
                        "retry once readiness is signalled."
                    ),
                    "error_type": "AdapterNotReady",
                },
                correlation_id=command.correlation_id,
                success=False,
            )
            await self._publish_result(
                reply_to=reply_to,
                result_payload=not_ready_payload,
                correlation_id=command.correlation_id or envelope.correlation_id,
            )
            return

        result_payload = await self._safe_invoke(command)
        await self._publish_result(
            reply_to=reply_to,
            result_payload=result_payload,
            correlation_id=command.correlation_id or envelope.correlation_id,
        )

    async def _safe_invoke(self, command: CommandPayload) -> ResultPayload:
        """Dispatch and convert exceptions into a failure ``ResultPayload``.

        AC-005 (unknown command) and AC-006 (handler exception) both flow
        through here: ``_dispatch_command`` may raise
        :class:`UnsupportedCommandError` (an unknown command) or any
        exception the underlying MCP method raises. Both become a structured
        failure result with ``error`` text and ``error_type`` so the requester
        can distinguish protocol errors from tutor-logic errors without
        reading a free-form string.
        """
        try:
            result_dict = await self._dispatch_command(command.command, command.args)
        except Exception as exc:  # noqa: BLE001 — boundary catch for AC-005/AC-006
            logger.exception(
                "Command %r raised; surfacing as failure ResultPayload", command.command
            )
            return ResultPayload(
                command=command.command,
                result={"error": str(exc), "error_type": type(exc).__name__},
                correlation_id=command.correlation_id,
                success=False,
            )

        return ResultPayload(
            command=command.command,
            result=result_dict,
            correlation_id=command.correlation_id,
            success=True,
        )

    async def _dispatch_command(
        self, command: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve aliases (Bug #2) and invoke the MCP method.

        Implements the Bug #2 fix — ``self.tool_to_command.get(command,
        command)`` runs *before* the ``_command_map`` lookup so MCP tool
        names like ``tutor_start_session`` are folded onto canonical
        ``start_session`` while canonical names pass through unchanged.

        Raises:
            UnsupportedCommandError: When the resolved command name has no
                entry in ``_command_map``. The error lists the sorted set of
                supported canonical commands.
        """
        resolved_command = self.tool_to_command.get(command, command)
        handler = self._command_map.get(resolved_command)
        if handler is None:
            raise UnsupportedCommandError(
                command=command,
                supported=sorted(self._command_map),
            )

        return await handler(**self._normalise_args(resolved_command, args))

    def _normalise_args(
        self, resolved_command: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Fold known argument-name aliases onto canonical handler kwargs.

        See :attr:`_arg_aliases`. When both the alias and the canonical
        key are present (a model that emits both), the canonical key
        wins — the alias value is discarded rather than clobbering it.
        Commands with no alias table pass through untouched.
        """
        aliases = self._arg_aliases.get(resolved_command)
        if not aliases:
            return args
        normalised = dict(args)
        for alias, canonical in aliases.items():
            if alias in normalised:
                alias_value = normalised.pop(alias)
                normalised.setdefault(canonical, alias_value)
        return normalised

    async def _publish_result(
        self,
        reply_to: str | None,
        result_payload: ResultPayload,
        correlation_id: str | None = None,
    ) -> None:
        """Dual-publish the result (Bug #1).

        When ``reply_to`` is set, the raw ``ResultPayload`` JSON is published
        to that inbox via ``client.publish_raw`` so jarvis's
        ``client.request()`` future resolves with the actual result rather
        than the JetStream PubAck. The canonical envelope path on
        ``agents.result.<agent_id>`` is *always* taken regardless of
        ``reply_to``, so event-stream consumers see every result.
        """
        if reply_to is not None:
            await self.client.publish_raw(
                reply_to,
                result_payload.model_dump_json().encode(),
            )

        canonical_subject = Topics.resolve(
            Topics.Agents.RESULT, agent_id=self.agent_id
        )
        await self.client.publish(
            canonical_subject,
            payload=result_payload,
            event_type=EventType.RESULT,
            source_id=self.agent_id,
            correlation_id=correlation_id,
        )


__all__ = ["CommandRouter", "UnsupportedCommandError"]
