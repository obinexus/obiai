import pytest

from obiai.core.errors import SessionNotFoundError
from obiai.core.models import Observation, TranscriptEntry
from obiai.memory import InMemorySessionRepository


def _observation(session_id: str) -> Observation:
    return Observation(
        session_id=session_id,
        modality="vision",
        event_type="participant_raised_hand",
        value=True,
        confidence=0.9,
        source="browser_hand_classifier",
    )


def test_create_and_get() -> None:
    repo = InMemorySessionRepository()
    session = repo.create()
    assert repo.get(session.session_id) is session
    assert repo.get("nope") is None


def test_delete_wipes_everything() -> None:
    repo = InMemorySessionRepository()
    session = repo.create()
    repo.add_observation(session.session_id, _observation(session.session_id))
    repo.append_transcript(session.session_id, TranscriptEntry(role="user", text="hello"))
    assert repo.delete(session.session_id) is True
    assert repo.get(session.session_id) is None
    assert repo.delete(session.session_id) is False


def test_transcript_retention_none_stores_nothing() -> None:
    repo = InMemorySessionRepository(transcript_retention="none")
    session = repo.create()
    repo.append_transcript(session.session_id, TranscriptEntry(role="user", text="hello"))
    assert repo.get(session.session_id).transcript == []


def test_unknown_session_raises() -> None:
    repo = InMemorySessionRepository()
    with pytest.raises(SessionNotFoundError):
        repo.add_observation("ghost", _observation("ghost"))
