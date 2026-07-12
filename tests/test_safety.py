import pytest
from pydantic import ValidationError

from obiai.core.config import Settings
from obiai.core.models import Evidence, MappedEvidence, Observation, Provenance
from obiai.safety import SafetyAuditor


def _auditor() -> SafetyAuditor:
    settings = Settings()
    return SafetyAuditor(
        allowed_event_types=settings.u.vision.allowed_event_types,
        forbidden_categories=settings.u.safety.forbidden_inference_categories,
    )


def _observation(event_type: str) -> Observation:
    return Observation(
        session_id="session-001",
        modality="vision",
        event_type=event_type,
        value=True,
        confidence=0.9,
        source="browser_hand_classifier",
    )


def _mapping(proposition: str, concepts: list[str]) -> MappedEvidence:
    return MappedEvidence(
        bn_variable="x",
        proposition=proposition,
        concepts=concepts,
        evidence=Evidence(
            proposition=proposition,
            value=True,
            confidence=0.9,
            provenance=Provenance(module="test", version="0"),
        ),
    )


def test_allowed_observable_event_passes() -> None:
    audit = _auditor().audit(
        _observation("participant_raised_hand"),
        _mapping("participant_requests_turn", ["vision.hand_raise"]),
    )
    assert audit.passed
    assert audit.policy_flags == []


def test_disallowed_event_type_flagged() -> None:
    audit = _auditor().audit(
        _observation("participant_is_deceptive"),
        _mapping("participant_requests_turn", ["vision.hand_raise"]),
    )
    assert not audit.passed
    assert "event_type_not_allowed:participant_is_deceptive" in audit.policy_flags


def test_forbidden_inference_category_flagged() -> None:
    audit = _auditor().audit(
        _observation("participant_raised_hand"),
        _mapping("medical.diagnosis", ["emotion.distress"]),
    )
    assert not audit.passed
    assert any(f.startswith("forbidden_inference_category:emotion") for f in audit.policy_flags)
    assert any(f.startswith("forbidden_inference_category:medical") for f in audit.policy_flags)


def test_oversized_text_value_rejected_at_model_boundary() -> None:
    with pytest.raises(ValidationError, match="short scalar"):
        Observation(
            session_id="session-001",
            modality="vision",
            event_type="participant_raised_hand",
            value="x" * 100_000,  # a smuggled frame would look like this
            confidence=0.9,
            source="browser_hand_classifier",
        )
