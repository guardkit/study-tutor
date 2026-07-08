"""In-memory tutor session state (Phase 0).

Session data are plain dataclasses so Phase 1 can serialise them to the store
without re-shaping a stateful engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

Role = Literal["user", "tutor"]
Status = Literal["active", "ended"]


@dataclass
class TutorTurn:
    role: Role
    content: str
    timestamp: datetime


@dataclass
class TutorSession:
    session_id: str
    subject: str
    topic: str | None
    started_at: datetime
    turns: list[TutorTurn] = field(default_factory=list)
    status: Status = "active"


class SessionNotFoundError(KeyError):
    """Raised when a session_id is not present in the store."""


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, TutorSession] = {}

    def create(self, subject: str, topic: str | None = None) -> TutorSession:
        session = TutorSession(
            session_id=str(uuid.uuid4()),
            subject=subject,
            topic=topic,
            started_at=datetime.now(timezone.utc),
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> TutorSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc

    def append_turn(self, session_id: str, role: Role, content: str) -> None:
        session = self.get(session_id)
        session.turns.append(
            TutorTurn(role=role, content=content, timestamp=datetime.now(timezone.utc))
        )

    def end(self, session_id: str) -> None:
        self.get(session_id).status = "ended"

    def list_active(self) -> list[str]:
        return [sid for sid, s in self._sessions.items() if s.status == "active"]


_store = SessionStore()


def get_default_store() -> SessionStore:
    return _store
