"""Session state and its storage boundary.

``SessionRepository`` is the persistence protocol; ``InMemorySessionRepository``
is the MVP implementation (single-process dict). A database-backed
implementation can be swapped in later without touching the service layer.

Privacy: deleting a session is a full wipe — observations, decisions and
transcript all disappear. With ``transcript_retention="none"`` transcript
entries are never stored at all.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from obiai.core.models import Decision, Observation, TranscriptEntry, new_id, utcnow

__all__ = ["InMemorySessionRepository", "Session", "SessionRepository"]


class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: new_id("session"))
    created_at: datetime = Field(default_factory=utcnow)
    observations: list[Observation] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    transcript: list[TranscriptEntry] = Field(default_factory=list)


@runtime_checkable
class SessionRepository(Protocol):
    def create(self) -> Session: ...

    def get(self, session_id: str) -> Session | None: ...

    def delete(self, session_id: str) -> bool: ...

    def add_observation(self, session_id: str, observation: Observation) -> None: ...

    def add_decision(self, session_id: str, decision: Decision) -> None: ...

    def append_transcript(self, session_id: str, entry: TranscriptEntry) -> None: ...


class InMemorySessionRepository:
    def __init__(self, transcript_retention: Literal["session", "none"] = "session") -> None:
        self.transcript_retention = transcript_retention
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        session = Session()
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def add_observation(self, session_id: str, observation: Observation) -> None:
        self._require(session_id).observations.append(observation)

    def add_decision(self, session_id: str, decision: Decision) -> None:
        self._require(session_id).decisions.append(decision)

    def append_transcript(self, session_id: str, entry: TranscriptEntry) -> None:
        if self.transcript_retention == "none":
            return
        self._require(session_id).transcript.append(entry)

    def _require(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            from obiai.core.errors import SessionNotFoundError

            raise SessionNotFoundError(session_id)
        return session
