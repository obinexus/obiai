"""Domain errors for the U pipeline (mapped to transport errors in the API layer)."""

from __future__ import annotations

__all__ = [
    "DisallowedEventTypeError",
    "NoObservationsError",
    "SessionNotFoundError",
    "UError",
    "UnknownEventTypeError",
]


class UError(Exception):
    """Base class for U domain errors."""


class UnknownEventTypeError(UError):
    def __init__(self, event_type: str) -> None:
        super().__init__(f"No ontology mapping registered for event type '{event_type}'")
        self.event_type = event_type


class DisallowedEventTypeError(UError):
    def __init__(self, event_type: str) -> None:
        super().__init__(
            f"Event type '{event_type}' is not in the observable-events allowlist"
        )
        self.event_type = event_type


class SessionNotFoundError(UError):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id


class NoObservationsError(UError):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session {session_id} has no observations to reason over")
        self.session_id = session_id
