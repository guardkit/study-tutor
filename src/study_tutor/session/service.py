"""App Access ``SessionService`` (FEAT-SMP-003) — transport-agnostic session
orchestration over the durable ``StudentStore``.

This is the thin layer both transports sit on: the MCP adapter today, the
HTTP/WS adapter for the mobile client later. It composes the ``StudentStore``
session methods (``create_session`` / ``get_session`` / ``list_sessions`` /
``append_turn`` / ``get_turns`` / ``end_session`` / ``record_session_completion``)
and adds the two things the port explicitly delegates upward
(``docs/design/contracts/API-session-cross-device.md`` §5): the **ownership
guard** (``SessionForbidden`` when a session's ``student_id`` ≠ the caller) and
the **status guard** (``SessionEnded``), applied via :meth:`_load_owned_session`
on every verb that takes a ``session_id``.

Two-level injection (mirrors the store): the adapters resolve the shared
``SessionService`` via :mod:`session.provider`; the service resolves the
``StudentStore`` via :mod:`knowledge.store.provider`. The service imports **no**
MCP, FastAPI, or Keycloak types — identity is an already-resolved
``student_id: str`` parameter; the LLM/Coach loop is injected as ``reply_fn``.
Writes are ``await``-ed inline (ADR-ARCH-023 D2), never fire-and-forget.

Open decisions for ``/feature-spec`` (from the adversarial design review) — the
scaffolding is deliberately silent on these so the build resolves them once:

* **#1 identity source (high).** The transport must server-resolve ONE
  ``student_id`` (config now; the Keycloak ``sub`` later) and pass the SAME id to
  ALL verbs as the ownership key. The MCP ``tutor_start_session`` ``student_id``
  arg is the planner *learner slug*, NOT identity — keep them separate so the
  guard is neither tautological nor a break.
* **#2 subject (med).** The MCP adapter supplies ``subject`` internally (preserve
  today's ``subject=student_id`` or a role constant) WITHOUT adding a tool arg.
* **#3 wiring (med).** Wire the service into BOTH ``MCPAdapter`` sites in
  ``cli/main.py`` (``serve`` and ``_build_nats_runtime``) via a shared helper.
* **#4 completion producer (med).** :class:`SessionCompletion` is computed by the
  Coach domain logic and handed to :meth:`end_session`; the confidence/XP delta
  policy (the ``Phase1MinimalDeltaPolicy`` heuristic) resolves ``ConfidenceUpdate``
  values from ``StudentStore`` reads.
* **#5 event payload (med).** ``session.started`` / ``turn_completed`` /
  ``completed`` (§8) belong on the service so both transports share them, but the
  emitted payload must reproduce today's ``perform_session_end`` shape
  (events-schema.yaml). Kept OUT of this scaffolding to avoid divergence; the
  build wires the EventBus with the pinned payload.
* **#6 ratify §9 / #8 F4 in-flight resolution.** Ratify the ``SessionForbidden`` /
  ``Unauthenticated`` closed-set extension via ``/design-refine``; F4 in-flight
  turn resolution is out of scope this wave (acceptable under single-user
  last-writer-wins).
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Literal

from study_tutor.knowledge.store.entities import (
    ConfidenceUpdate,
    SessionRecord,
    SessionStatus,
    SessionTurn,
    StudentState,
)
from study_tutor.knowledge.store.port import (
    DEFAULT_SESSION_LIST_LIMIT,
    StudentStore,
)
from study_tutor.knowledge.store.provider import get_student_store
from study_tutor.knowledge.student_model import Misconception
from study_tutor.gamification.texts import derive_text_name
from study_tutor.planner.pipeline import plan_session
from study_tutor.planner.protocols import (
    SessionCompletion as PlannerSessionCompletion,
)
from study_tutor.planner.types import (
    AssessmentObjectiveCode,
    SessionPlan,
    _baseline_plan,
    load_curriculum_defaults,
)
from study_tutor.session.errors import (
    SessionEnded,
    SessionForbidden,
    SessionNotFoundError,
)
from study_tutor.session.notifier import TurnNotifierPort
from study_tutor.tutoring.adapters.session_state import (
    SessionState,
    TranscriptTurn,
)
from study_tutor.tutoring.session_end import (
    SESSION_COMPLETED_EVENT,
    EventBus,
)

logger = logging.getLogger(__name__)


# The backend's copy of the SUBJECT_DEFAULT contract's one value
# (docs/design/contracts/SUBJECT_DEFAULT.md). ADR-ARCH-032 D4: the
# service normalises an omitted/empty subject to this at the boundary so
# ``(student, subject)`` session keying and subject-scoped retrieval
# always see a real subject. Equal by contract to the app's
# ``defaultSubject``, fleet-gateway's ``DEFAULT_SUBJECT``, and
# ``knowledge.retrieval.DEFAULT_SUBJECT`` (kept as a separate literal
# there — knowledge must not import session); the SUBJECT_DEFAULT seam
# test pins them all to the same string.
SUBJECT_DEFAULT: str = "english"


# ---------------------------------------------------------------------------
# Planner-hoist configuration (S-R3 §2.1 — relocated from mcp/adapter.py)
# ---------------------------------------------------------------------------

#: Env var controlling the *outer* ``plan_session`` budget invoked inside
#: :meth:`SessionService.start_session` (ASSUM-006, signed off 2026-04-29).
#: Default 2.0s. The single graceful-degradation boundary for the planner: any
#: timeout / internal exception / unknown learner degrades to a baseline plan
#: rather than blocking session creation. Relocated here verbatim from the MCP
#: adapter when planning moved into the core (spec §2.1 / D14).
_PLANNER_HANDLER_BUDGET_ENV: str = "PLANNER_HANDLER_BUDGET_SEC"
_PLANNER_HANDLER_BUDGET_DEFAULT: float = 2.0

#: How many recent ended sessions to read as plan facts — the Rule-4
#: revisit inputs (``session_completions``) and the §6.3(c) anti-repetition
#: lookback (``recent_recommendations``). A single-student window is tiny; a
#: generous cap keeps the 4-day London rotation honest without a heavy read.
_RECENT_SESSIONS_WINDOW: int = 20


def _planner_handler_budget_sec() -> float:
    """Return the outer ``plan_session`` budget for ``start_session``.

    Reads :data:`_PLANNER_HANDLER_BUDGET_ENV` at *call* time so test patching of
    ``os.environ`` flows through without a process restart. Falls back to
    :data:`_PLANNER_HANDLER_BUDGET_DEFAULT` when unset or unparseable.
    """
    raw = os.environ.get(_PLANNER_HANDLER_BUDGET_ENV)
    if raw is None:
        return _PLANNER_HANDLER_BUDGET_DEFAULT
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "ignoring unparseable %s=%r; using default %.1fs",
            _PLANNER_HANDLER_BUDGET_ENV,
            raw,
            _PLANNER_HANDLER_BUDGET_DEFAULT,
        )
        return _PLANNER_HANDLER_BUDGET_DEFAULT


def _curriculum_ao_mapping() -> dict[str, list[AssessmentObjectiveCode]]:
    """``topic_name → [AO codes]`` from the curriculum the planner understands.

    S-R3 §2.1: the planner's ``ao_mapping`` input, sourced from
    ``curriculum_defaults.yaml`` (the same AO source :func:`_baseline_plan`
    already reads) so ``focus_aos`` is populated for curriculum topics rather
    than blanked. A malformed/missing YAML degrades to an empty mapping — the
    planner then reports ``ao_mapping_found=False`` rather than raising.
    """
    try:
        entries = load_curriculum_defaults()
    except Exception:  # noqa: BLE001 — degrade to empty mapping, never raise
        logger.warning("event=curriculum_ao_mapping_unavailable", exc_info=True)
        return {}
    return {
        str(entry["topic_name"]): list(entry.get("focus_aos") or [])
        for entry in entries
        if entry.get("topic_name")
    }


# ---------------------------------------------------------------------------
# Player-context assembly (spec §2.5 / §2.6 — populated ONCE, in the service)
# ---------------------------------------------------------------------------

#: GOAL.md §7 default grade target when the student profile has none set.
DEFAULT_GRADE_TARGET: str = "6"

#: design §6.1: Mastered is 80–100; a topic below this counts as "not yet
#: mastered" for weakest-topic selection.
_MASTERED_THRESHOLD: int = 80

#: Caps on the compact typed context lists threaded to the Player (spec §2.5).
_MAX_WEAKEST_TOPICS: int = 3
_MAX_RECENT_MISCONCEPTIONS: int = 3


def _band_for_topic(state: StudentState, topic: str | None) -> str | None:
    """The confidence band for ``topic`` from the student-state snapshot.

    Returns ``None`` when no topic is set or the topic has no confidence row.
    """
    if not topic:
        return None
    for conf in state.topic_confidences:
        if conf.topic_name == topic:
            return conf.band
    return None


def _weakest_topics(state: StudentState) -> tuple[str, ...]:
    """Up to 3 weakest below-Mastered topics (ascending confidence)."""
    below = [
        conf
        for conf in state.topic_confidences
        if conf.percentage < _MASTERED_THRESHOLD
    ]
    below.sort(key=lambda conf: conf.percentage)
    return tuple(conf.topic_name for conf in below[:_MAX_WEAKEST_TOPICS])


def _recent_misconception_texts(
    state: StudentState, topic: str | None
) -> tuple[str, ...]:
    """Up to 3 recent misconception texts, session-topic matches leading.

    Ordered most-recent-first; a stable second sort floats the current
    session topic's misconceptions to the front of the (≤3) window without
    disturbing recency order within each group.
    """
    miscs = list(state.recent_misconceptions)
    miscs.sort(key=lambda misc: misc.observed_at, reverse=True)
    if topic:
        miscs.sort(key=lambda misc: misc.topic_name != topic)
    return tuple(misc.text for misc in miscs[:_MAX_RECENT_MISCONCEPTIONS])


# ---------------------------------------------------------------------------
# Injected domain-loop callables
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TutorReply:
    """One tutor reply from the injected domain loop (``reply_fn``)."""

    response: str
    metadata: Mapping[str, object] | None = None


#: Metadata keys the transport reply carries per-turn capture signals under
#: (S-E4 / scope §4.3–§4.4): the Coach-observed AO scaffolded this turn (R9) and
#: the count of verifier-confirmed corpus-hit quotations (R8). The service reads
#: them generically off ``reply.metadata`` and forwards them to ``append_turn`` —
#: it stays transport-neutral (the orchestrator/adapter populates the keys, D14).
_AO_SCAFFOLDED_KEY = "ao_scaffolded"
_QUOTES_EMBEDDED_KEY = "quotes_embedded"


def _per_turn_signals(
    metadata: Mapping[str, object] | None,
) -> tuple[str | None, int]:
    """Extract ``(ao_scaffolded, quotes_embedded)`` from a tutor reply's metadata.

    Both default to "no signal" (``None`` / ``0``) so a reply that carries no
    capture metadata (the streaming path, a legacy adapter) persists cleanly.
    """
    if not metadata:
        return None, 0
    ao_raw = metadata.get(_AO_SCAFFOLDED_KEY)
    ao_scaffolded = ao_raw if isinstance(ao_raw, str) and ao_raw else None
    quotes_raw = metadata.get(_QUOTES_EMBEDDED_KEY)
    quotes_embedded = quotes_raw if isinstance(quotes_raw, int) else 0
    return ao_scaffolded, max(0, quotes_embedded)


#: The domain tutor/Coach loop, injected into :meth:`SessionService.turn`. Keeps
#: LLM/orchestrator concerns in the adapter; the service only persists + guards.
ReplyFn = Callable[[str], Awaitable[TutorReply]]

#: Streaming variant: yields tutor tokens as they are produced (WS path, §7).
ReplyStreamFn = Callable[[str], AsyncIterator[str]]


# ---------------------------------------------------------------------------
# Input / result DTOs (frozen — in-process bundles, projected by the transport)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionCompletion:
    """Learner-state deltas persisted at session end (design-review #4).

    Computed by the Coach domain logic and handed in; the store only persists.
    ``xp_awarded`` and ``confidence_updates`` carry the RESOLVED post-session
    values (band derived at write time), not deltas — the write is idempotent on
    ``session_id``.
    """

    topic: str | None
    aos_scaffolded: list[str]
    xp_awarded: int
    confidence_updates: list[ConfidenceUpdate]
    misconceptions: list[Misconception]


@dataclass(frozen=True)
class StartSessionResult:
    session_id: str
    student_id: str
    subject: str
    topic: str | None
    resumed: bool
    #: Transcript, populated only on the resumed branch (a device re-attaching).
    turns: tuple[SessionTurn, ...] | None = None
    #: S-R3 §2.1: the plan the service computed at start (planning moved into
    #: the core, D14). Transports project it: HTTP surfaces ``topic`` /
    #: ``opening_prompt`` / ``focus_aos`` (contract §2.3); MCP its
    #: ``plan_summary``. ``None`` only for pre-S-R3/legacy callers that
    #: construct the result directly.
    plan: SessionPlan | None = None


@dataclass(frozen=True)
class ResumeResult:
    session_id: str
    student_id: str
    status: SessionStatus
    turns: tuple[SessionTurn, ...]


@dataclass(frozen=True)
class TurnsSinceResult:
    """The delta slice behind the live robot-session mirror (Stage 1).

    ``turns`` are the SAME ordered rows :class:`ResumeResult` carries, sliced
    from the 0-based row offset ``since``; ``total`` is the RAW row count (never
    the ``// 2`` pairs projection the status/list verbs surface), so a client
    polls with ``since=total`` next time. Unlike resume this reads **ended**
    sessions too, so a poll survives the active→ended transition.
    """

    session_id: str
    student_id: str
    status: SessionStatus
    turns: tuple[SessionTurn, ...]
    total: int


@dataclass(frozen=True)
class TurnResult:
    tutor_response: str
    turn_index: int
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True)
class SessionStatusView:
    session_id: str
    student_id: str
    status: SessionStatus
    turn_count: int
    started_at: datetime
    last_activity: datetime
    resumable: bool


@dataclass(frozen=True)
class EndSessionResult:
    session_id: str
    status: Literal["ended"] = "ended"
    #: The nullable ``gamification`` settlement block (contract Revision 2 /
    #: API-session-cross-device.md §5; the MCP ``tutor_session_end`` addendum).
    #: Built once here from the settlement decision so HTTP and MCP surface the
    #: byte-identical shape (D14); ``None`` when the session ended but did not
    #: settle (savepoint fault → swept later), so transports omit the block.
    gamification: dict[str, Any] | None = None


@dataclass(frozen=True)
class TurnEvent:
    """A WebSocket stream frame (§7 Rev 1): token/done/transcript/audio_ref/error events.

    Contract §7 Rev 1 frozen event types:
    - token: text chunk (has text)
    - done: terminal marker (has turn_index)
    - transcript: STT result (has text)
    - audio_ref: TTS chunk reference (has seq, chunk_id, url)
    - error: generation failure (has error, error_type)
    """

    type: Literal["token", "done", "transcript", "audio_ref", "error"]
    text: str | None = None
    turn_index: int | None = None
    # Audio reference fields (type="audio_ref")
    seq: int | None = None
    chunk_id: str | None = None
    url: str | None = None
    # Error fields (type="error")
    error: str | None = None
    error_type: str | None = None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SessionService:
    """Composes the ``StudentStore`` session methods with the ownership/status
    guards and event responsibilities the App Access layer owns."""

    def __init__(
        self,
        *,
        store: StudentStore | None = None,
        event_bus: EventBus | None = None,
        turn_notifier: TurnNotifierPort | None = None,
    ) -> None:
        """Hold an explicit store (tests) or resolve the wired one per call.

        ``event_bus`` (optional) is where :meth:`end_session` emits the
        post-commit ``session.completed`` notification (spec §4.2(5) / D8 —
        emit-after-commit, notification-only). Populated once, in the core, so
        both transports emit identically (D14); ``None`` ⇒ no emission (the bus
        has zero subscribers today). The MCP adapter shares its bus into the
        service at construction so its subscribers still see the event.

        ``turn_notifier`` (optional, live robot-session mirror Stage 2) is the
        in-process signal the SSE mirror stream parks on: it is pinged after
        **each persisted row** and once after ``end_session``'s finalize commits,
        so a watching phone renders the robot's turn without waiting out a poll
        tick. ``None`` ⇒ no signalling (the stream degrades to timeout ticking).
        It is a notification only — never a write path, never load-bearing.
        """
        self._store = store
        self._event_bus = event_bus
        self._turn_notifier = turn_notifier

    def _notify_turn_change(self, session_id: str) -> None:
        """Ping the mirror's change signal — best-effort, never into the caller.

        A notification is a courtesy to a read-only viewer; a failure here must
        never surface as a failed turn, so everything is swallowed and logged at
        debug. Fires only *after* the row is durably persisted.
        """
        notifier = self._turn_notifier
        if notifier is None:
            return
        try:
            notifier.notify(session_id)
        except Exception:
            logger.debug(
                "event=turn_notify_failed session_id=%s", session_id, exc_info=True
            )

    def _resolve_store(self) -> StudentStore:
        store = self._store if self._store is not None else get_student_store()
        if store is None:
            raise RuntimeError(
                "SessionService has no StudentStore wired — "
                "call knowledge.store.provider.set_student_store at startup",
            )
        return store

    async def _load_owned_session(
        self, student_id: str, session_id: str, *, allow_ended: bool = False
    ) -> SessionRecord:
        """The single ownership+status guard the four ``session_id`` verbs reuse.

        ``None`` from the store → ``SessionNotFoundError``; a ``student_id``
        mismatch → ``SessionForbidden``; an ``ended`` session (unless
        ``allow_ended``) → ``SessionEnded``. Centralising this is what the
        contract §5 / port docstring delegation asks for.
        """
        store = self._resolve_store()
        record = await store.get_session(session_id)
        if record is None:
            raise SessionNotFoundError(session_id)
        if record.student_id != student_id:
            raise SessionForbidden(
                f"session {session_id!r} is not owned by {student_id!r}"
            )
        if not allow_ended and record.status == "ended":
            raise SessionEnded(f"session {session_id!r} has ended")
        return record

    async def start_session(
        self,
        *,
        student_id: str,
        subject: str,
        topic: str | None = None,
        resume_if_active: bool = False,
    ) -> StartSessionResult:
        """Create a session — or, with ``resume_if_active``, return the caller's
        existing active one (with its transcript). No ownership guard: an
        auth-derived ``student_id`` can only create/resume its own session.

        S-R3 §2.1 / D14: planning now lives here. The plan is computed under the
        2.0s budget/degrade boundary keyed by the **ownership** ``student_id``
        (the same identity the confidence writes use — spec §2.1 read-key fix),
        and its facts persist on the created session row: ``topic`` and
        ``focus_aos`` (in the ``aos_scaffolded`` column, S-R3 §2.1). The
        ``opening_prompt`` is NOT persisted — it rides back in the plan on the
        result only. ``topic`` (the learner-supplied value) is the planner's
        override; the persisted/returned topic is the plan's chosen topic.

        ADR-ARCH-032 D4: an omitted/empty ``subject`` normalises to
        :data:`SUBJECT_DEFAULT` at this boundary — the row never persists
        ``''``, so ``(student, subject)`` resume keying and subject-scoped
        retrieval always see a real subject.
        """
        if not subject:
            logger.info(
                "event=subject_normalised student_id=%s subject=%s",
                student_id,
                SUBJECT_DEFAULT,
            )
            subject = SUBJECT_DEFAULT
        store = self._resolve_store()

        # Plan under the outer budget/degrade boundary. Keyed by the ownership
        # student_id so the planner reads the same learner state the confidence
        # writes key on (spec §2.1). ``topic`` is the learner override.
        plan = await self._plan(
            student_id=student_id, topic_override=topic
        )

        # Canonical set-text capture at START (S-E4 / scope §4.2): resolve the
        # plan's topic (and the learner override / subject) to a canonical text
        # slug so the row carries a stable ``text_name`` the W2 Mastery /
        # Exploration signals group by. ``None`` when no known set text.
        text_name = derive_text_name(
            topic=plan.topic_name, subject=subject, text_hint=topic
        )

        # Persist the plan facts on the row at start (spec §2.1). On a resume the
        # store returns the existing row and ignores these; the freshly-computed
        # plan still rides back on the result for the start response.
        record, created = await store.create_session(
            student_id=student_id,
            subject=subject,
            topic=plan.topic_name,
            aos_scaffolded=list(plan.focus_aos),
            text_name=text_name,
            resume_if_active=resume_if_active,
        )
        turns: tuple[SessionTurn, ...] | None = None
        if not created:
            turns = tuple(await store.get_turns(record.session_id))
        return StartSessionResult(
            session_id=record.session_id,
            student_id=record.student_id,
            subject=record.subject,
            topic=record.topic,
            resumed=not created,
            turns=turns,
            plan=plan,
        )

    async def _plan(
        self, *, student_id: str, topic_override: str | None
    ) -> SessionPlan:
        """Run ``plan_session`` under the 2.0s budget/degrade boundary.

        Relocated from ``mcp/adapter.py`` (spec §2.1). Feeds the planner its two
        previously-blanked inputs: the curriculum ``ao_mapping`` (so
        ``focus_aos`` is populated) and the learner's recent ended sessions as
        both Rule-4 ``session_completions`` (revisit signal) and the §6.3(c)
        ``recent_recommendations`` anti-repetition lookback. Any failure mode
        (timeout / internal exception / unknown learner) degrades to
        :func:`_baseline_plan(False)` rather than propagating — session creation
        must never be blocked by the planner.
        """
        store = self._resolve_store()

        # Recent ended sessions = the plan facts the two planner inputs need.
        recent = await store.list_sessions(
            student_id, status="ended", limit=_RECENT_SESSIONS_WINDOW
        )
        session_completions = [
            PlannerSessionCompletion(
                topics_covered=[r.topic] if r.topic else [],
                ended_at=r.last_activity,
            )
            for r in recent
        ]
        recent_recommendations = tuple(
            (r.topic, r.last_activity) for r in recent if r.topic
        )

        budget = _planner_handler_budget_sec()
        try:
            return await asyncio.wait_for(
                plan_session(
                    student_id,
                    topic_override,
                    ao_mapping=_curriculum_ao_mapping(),
                    session_completions=session_completions,
                    recent_recommendations=recent_recommendations,
                ),
                timeout=budget,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "planner exceeded %.2fs handler budget — degrading to "
                "baseline plan",
                budget,
                extra={
                    "event": "planner_handler_budget_exceeded",
                    "student_id": student_id,
                    "budget_sec": budget,
                },
            )
            return _baseline_plan(learner_state_available=False)
        except Exception as exc:  # noqa: BLE001 — boundary catch, never re-raise
            logger.exception(
                "planner internal error — degrading to baseline plan",
                extra={
                    "event": "planner_internal_error",
                    "student_id": student_id,
                    "error": str(exc),
                },
            )
            return _baseline_plan(learner_state_available=False)

    async def list_sessions(
        self,
        *,
        student_id: str,
        status: SessionStatus | None = None,
        limit: int = DEFAULT_SESSION_LIST_LIMIT,
    ) -> list[SessionRecord]:
        """The caller's recent sessions (ownership-scoped by the partition key —
        no ``session_id``, so no guard is possible or needed)."""
        store = self._resolve_store()
        return await store.list_sessions(student_id, status=status, limit=limit)

    async def resume_session(
        self, *, student_id: str, session_id: str
    ) -> ResumeResult:
        """Rehydrate an owned active session's transcript for a new device."""
        record = await self._load_owned_session(
            student_id, session_id, allow_ended=False
        )
        store = self._resolve_store()
        turns = tuple(await store.get_turns(session_id))
        return ResumeResult(
            session_id=record.session_id,
            student_id=record.student_id,
            status=record.status,
            turns=turns,
        )

    async def turns_since(
        self, *, student_id: str, session_id: str, since: int
    ) -> TurnsSinceResult:
        """Owned session's transcript rows at index ≥ ``since`` (Stage 1 delta read).

        ``allow_ended=True`` — the mirror keeps reading after the robot ends the
        session (unlike :meth:`resume_session`, so ``SessionEnded`` is impossible
        here). ``since`` is a plain 0-based row offset into the same ordered rows
        :meth:`resume_session` returns, never a timestamp; a ``since`` at or past
        the end yields an empty slice (not an error). Service-level slice only —
        the store port is untouched.
        """
        record = await self._load_owned_session(
            student_id, session_id, allow_ended=True
        )
        store = self._resolve_store()
        rows = tuple(await store.get_turns(session_id))
        return TurnsSinceResult(
            session_id=record.session_id,
            student_id=record.student_id,
            status=record.status,
            turns=rows[since:],
            total=len(rows),
        )

    async def turn(
        self,
        *,
        student_id: str,
        session_id: str,
        user_message: str,
        reply_fn: ReplyFn,
    ) -> TurnResult:
        """Persist the user turn, run the injected tutor loop, persist the tutor
        turn — two durable rows per §6 (lossless mid-session device switch)."""
        await self._load_owned_session(student_id, session_id, allow_ended=False)
        store = self._resolve_store()
        # User turns scaffold nothing and embed no quotes — pass the capture
        # kwargs explicitly (S-E4 item 3: all four append_turn sites pass them).
        await store.append_turn(
            session_id=session_id,
            role="user",
            content=user_message,
            ao_scaffolded=None,
            quotes_embedded=0,
        )
        # Mirror signal after EACH persisted row (Stage 2) — the watching phone
        # sees the learner's question land before the tutor has answered it.
        self._notify_turn_change(session_id)
        reply = await reply_fn(user_message)
        # Per-turn capture signals ride the reply metadata (S-E4 §4.3/§4.4).
        ao_scaffolded, quotes_embedded = _per_turn_signals(reply.metadata)
        tutor_turn = await store.append_turn(
            session_id=session_id,
            role="tutor",
            content=reply.response,
            ao_scaffolded=ao_scaffolded,
            quotes_embedded=quotes_embedded,
        )
        self._notify_turn_change(session_id)
        return TurnResult(
            tutor_response=reply.response,
            turn_index=tutor_turn.turn_index,
            metadata=reply.metadata,
        )

    async def turn_stream(
        self,
        *,
        student_id: str,
        session_id: str,
        user_message: str,
        reply_stream_fn: ReplyStreamFn,
    ) -> AsyncIterator[TurnEvent]:
        """WS streaming variant (§7 Rev 1): stream tokens with durability.

        Pipeline (TASK-VS2-003):
        1. Guard session ownership/status
        2. Persist user turn
        3. Stream reply tokens, accumulating response
        4. On success: persist tutor turn, yield done
        5. On failure: yield error, persist no tutor turn (ASSUM-004)

        Cancellation safety (ASSUM-005): caller cancellation doesn't prevent
        persistence of complete response. The generation/persistence runs
        detached from the consuming task's lifetime.
        """
        await self._load_owned_session(student_id, session_id, allow_ended=False)
        store = self._resolve_store()

        # Persist user turn before streaming (capture kwargs passed explicitly —
        # S-E4 item 3: all four append_turn sites pass them; a user turn carries
        # no AO / quote signal).
        await store.append_turn(
            session_id=session_id,
            role="user",
            content=user_message,
            ao_scaffolded=None,
            quotes_embedded=0,
        )
        # Same per-row mirror signal as the non-streaming path (Stage 2).
        self._notify_turn_change(session_id)

        # Accumulate response while streaming tokens
        accumulated_response = []
        generation_failed = False
        failure_reason = None

        try:
            async for token in reply_stream_fn(user_message):
                accumulated_response.append(token)
                yield TurnEvent(type="token", text=token)
        except Exception as exc:
            # ASSUM-004: generation failure mid-stream
            generation_failed = True
            failure_reason = f"{type(exc).__name__}: {exc}"
            yield TurnEvent(
                type="error",
                error=failure_reason,
                error_type="generation_failed",
            )
            # Don't persist tutor turn on failure
            return

        # Generation succeeded - persist full response. The token stream carries
        # no per-turn capture metadata, so the AO / quote signals are absent here
        # (passed explicitly for the fourth append_turn site — S-E4 item 3).
        if not generation_failed:
            full_response = "".join(accumulated_response)
            tutor_turn = await store.append_turn(
                session_id=session_id,
                role="tutor",
                content=full_response,
                ao_scaffolded=None,
                quotes_embedded=0,
            )
            self._notify_turn_change(session_id)
            yield TurnEvent(type="done", turn_index=tutor_turn.turn_index)

    async def build_turn_session_state(
        self, *, student_id: str, session_id: str
    ) -> SessionState:
        """Assemble the per-turn :class:`SessionState` the Player reads.

        Spec §2.5/§2.6 / D14: the player-context fields and the in-session
        memory window are populated **here, in the core** — never in a
        transport adapter — so HTTP, MCP and the voice/WS paths all feed the
        Player identical context. Both transports call this and hand the
        result straight to the orchestrator; neither reads the store for
        context itself.

        Reads, per turn:

        * the persisted session row → ``topic`` + ``focus_aos`` + ``text_name``
          plan facts (``text_name`` captured at start, S-E4 / scope §4.2);
        * one student-state snapshot → confidence band for the topic, the
          weakest below-Mastered topics, recent misconceptions, grade target
          (GOAL.md §7 default Grade 6);
        * the durable transcript → the prior-turn window (§2.6). The current
          user turn has already been persisted by ``turn`` / ``turn_stream``
          before the reply loop runs, so the trailing ``user`` row is the
          message being answered and is dropped from the *prior* window (the
          Player receives it as ``learner_message``).
        """
        store = self._resolve_store()

        record = await store.get_session(session_id)
        topic = record.topic if record is not None else None
        focus_aos = tuple(record.aos_scaffolded) if record is not None else ()
        # Canonical set-text slug captured at start (S-E4 / scope §4.2); reaches
        # the Player + the retrieval/quote-verifier path via SessionState.
        text_name = record.text_name if record is not None else None

        # Single student-state read for the four §2.5 context fields.
        state = await store.get_student_state(student_id)

        # Transcript rehydration (§2.6). Drop the trailing current user turn.
        turns = await store.get_turns(session_id)
        prior = turns[:-1] if (turns and turns[-1].role == "user") else turns
        transcript = tuple(
            TranscriptTurn(role=turn.role, content=turn.content)
            for turn in prior
        )

        grade_target = state.target_grade or DEFAULT_GRADE_TARGET

        return SessionState(
            session_id=session_id,
            student_id=student_id,
            text_name=text_name,
            topic=topic,
            focus_aos=focus_aos,
            mode="tutor",
            topic_confidence_band=_band_for_topic(state, topic),
            weakest_topics=_weakest_topics(state),
            recent_misconceptions=_recent_misconception_texts(state, topic),
            grade_target=grade_target,
            transcript=transcript,
        )

    async def session_status(
        self, *, student_id: str, session_id: str
    ) -> SessionStatusView:
        """Owned session status — the one verb that reads ``ended`` sessions too
        (``allow_ended=True``, the §9 carve-out)."""
        record = await self._load_owned_session(
            student_id, session_id, allow_ended=True
        )
        return SessionStatusView(
            session_id=record.session_id,
            student_id=record.student_id,
            status=record.status,
            turn_count=record.turn_count,
            started_at=record.started_at,
            last_activity=record.last_activity,
            resumable=(record.status == "active"),
        )

    async def end_session(
        self,
        *,
        student_id: str,
        session_id: str,
        completion: SessionCompletion | None = None,
        topic_hint: str | None = None,
    ) -> EndSessionResult:
        """Transition ``active → ended`` and commit the learner-state deltas —
        awaited inline (ADR-ARCH-023 D2).

        Spec §4.2 / ADR-ARCH-030 / D14: settlement is ONE ``store.finalize_session``
        transaction — the status UPDATE is the sole gate, the pure engine computes
        XP + achievements, and everything banks in a single savepoint (a fault
        leaves ``settled_at`` NULL for the sweep). This **replaces** the S-R3
        two-call ``record_session_completion`` + ``end_session`` sequence.

        Completion assembly still lives here, for ALL transports: the confidence
        and misconception deltas are derived from the **persisted** row plus store
        reads (HTTP and MCP produce byte-identical writes) and handed to
        ``finalize_session``, which writes them inside the settlement transaction.
        The MCP adapter passes only a ``topic_hint`` (a weak fallback if the row
        has no ``topic``); HTTP passes neither. An explicit ``completion`` is
        honoured for its confidence/misconception/aos/topic content (the
        store-ordering regression pin); XP is always engine-derived now.

        I-T6 zero-turn rule: a session with no turns still settles (at 0 XP) but
        assembles no completion and emits no ``session.completed`` event.

        §4.2(5) / D8: after ``finalize_session`` commits, the service emits the
        ``events-schema.yaml``-conforming ``session.completed`` (emit-after-commit,
        ``subject`` carries the actual subject) — never before the write, never
        from a transport adapter (D14).
        """
        record = await self._load_owned_session(
            student_id, session_id, allow_ended=False
        )
        store = self._resolve_store()
        now = datetime.now(timezone.utc)

        # Assemble the completion deltas in the core (spec §2.4). Explicit
        # completion wins its confidence/misconception content; otherwise derive
        # from the persisted row + store reads. I-T6: skip for zero-turn sessions.
        confidence_updates: list[ConfidenceUpdate] = []
        misconceptions: list[Misconception] = []
        aos_scaffolded = list(record.aos_scaffolded)
        topic = record.topic or topic_hint or record.subject

        if completion is not None:
            confidence_updates = list(completion.confidence_updates)
            misconceptions = list(completion.misconceptions)
            aos_scaffolded = list(completion.aos_scaffolded)
            topic = completion.topic
        elif record.turn_count > 0:
            # Local import avoids the completion↔service module import cycle.
            from study_tutor.session.completion import build_session_completion

            assembled = await build_session_completion(
                store=store,
                student_id=student_id,
                topic=topic,
                # Store rows are (user, tutor) turns; student turns are half.
                student_turn_count=record.turn_count // 2,
                aos_scaffolded=aos_scaffolded,
                misconceptions_per_topic={},
            )
            confidence_updates = list(assembled.confidence_updates)
            misconceptions = list(assembled.misconceptions)
            aos_scaffolded = list(assembled.aos_scaffolded)
            topic = assembled.topic

        result = await store.finalize_session(
            student_id=student_id,
            session_id=session_id,
            now=now,
            confidence_updates=confidence_updates,
            misconceptions=misconceptions,
            aos_scaffolded=aos_scaffolded,
            topic=topic,
        )

        # One mirror signal after the finalize transaction commits (Stage 2), so
        # a watching stream reads ``status="ended"`` immediately and closes,
        # rather than sitting out a poll tick on a session that is over.
        self._notify_turn_change(session_id)

        # Emit-after-commit (D8). Zero-turn sessions settle but do not emit.
        if self._event_bus is not None and result.had_turns:
            await self._event_bus.emit(
                SESSION_COMPLETED_EVENT,
                {
                    "session_id": result.session_id,
                    "subject": result.subject,
                    "duration_seconds": result.duration_seconds,
                    "topic": result.topic,
                    "aos_touched": list(result.aos_touched),
                    "quality_score": None,
                    "ended_at": result.ended_at.isoformat(),
                },
            )

        # Nullable gamification block (contract Revision 2 / MCP addendum). Built
        # once here from the settlement decision — the SAME block HTTP and MCP
        # surface (D14). Absent when settlement faulted (decision is None): the
        # session ended, the sweep will settle it later.
        from study_tutor.gamification.engine import gamification_end_block

        gamification = (
            gamification_end_block(result.decision)
            if result.decision is not None
            else None
        )

        return EndSessionResult(
            session_id=result.session_id, gamification=gamification
        )


__all__ = [
    "EndSessionResult",
    "ReplyFn",
    "ReplyStreamFn",
    "ResumeResult",
    "SessionCompletion",
    "SessionService",
    "SessionStatusView",
    "StartSessionResult",
    "TurnEvent",
    "TurnResult",
    "TurnsSinceResult",
    "TutorReply",
]
