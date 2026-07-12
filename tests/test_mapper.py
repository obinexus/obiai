import pytest

from obiai.core.errors import UnknownEventTypeError
from obiai.core.models import Observation
from obiai.ontology.mapper import EventOntologyMapper


def _observation(event_type: str = "participant_raised_hand") -> Observation:
    return Observation(
        session_id="session-001",
        modality="vision",
        event_type=event_type,
        value=True,
        confidence=0.9,
        source="browser_hand_classifier",
    )


def test_hand_raise_mapping() -> None:
    mapper = EventOntologyMapper()
    mapped = mapper.map(_observation())
    assert mapped.bn_variable == "participant_raised_hand"
    assert mapped.proposition == "participant_requests_turn"
    assert mapped.concepts == ["vision.hand_raise", "communication.request_turn"]
    assert mapped.evidence.value is True
    assert mapped.evidence.confidence == 0.9
    assert mapped.evidence.source_observation_id == mapped.evidence.source_observation_id
    assert mapped.evidence.provenance.module == "vision.hand_raise"


def test_evidence_traceable_to_observation() -> None:
    mapper = EventOntologyMapper()
    observation = _observation()
    mapped = mapper.map(observation)
    assert mapped.evidence.source_observation_id == observation.observation_id


def test_unknown_event_type_raises() -> None:
    mapper = EventOntologyMapper()
    with pytest.raises(UnknownEventTypeError):
        mapper.map(_observation("participant_is_deceptive"))
