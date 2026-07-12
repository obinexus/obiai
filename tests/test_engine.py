"""End-to-end (in-process) tests of the raised-hand MVP scenario."""

import pytest

from obiai.agents import HIGH_IMPACT_ACTIONS, build_u_engine, render_agent_message
from obiai.core.config import Settings
from obiai.core.models import Observation, TruthState

POSTERIOR_TRUE = 943 / 1010
POSTERIOR_FALSE = 19 / 330


@pytest.fixture()
def engine():
    return build_u_engine(Settings())


def _observation(value: bool = True, confidence: float = 0.9) -> Observation:
    return Observation(
        session_id="session-001",
        modality="vision",
        event_type="participant_raised_hand",
        value=value,
        confidence=confidence,
        source="browser_hand_classifier",
    )


def test_raised_hand_yields_yes_announcement(engine) -> None:
    decision = engine.reason("session-001", _observation())
    assert decision.probability == pytest.approx(POSTERIOR_TRUE, abs=1e-12)
    assert round(decision.probability, 2) == 0.93
    assert decision.state is TruthState.YES
    assert decision.action is not None
    assert decision.action.name == "announce_hand_raise"
    assert decision.bias_audit.passed
    assert decision.safety_audit.passed
    assert decision.semantic_path == [
        "observation.hand_raised",
        "communication.request_turn",
        "decision.announce_hand_raise",
    ]
    assert decision.ontological_concepts == [
        "vision.hand_raise",
        "communication.request_turn",
    ]
    assert decision.evidence[0].provenance.module == "vision.hand_raise"
    assert render_agent_message(decision) == (
        "A participant appears to be requesting a turn to speak."
    )


def test_lowered_hand_yields_no(engine) -> None:
    decision = engine.reason("session-001", _observation(value=False))
    assert decision.probability == pytest.approx(POSTERIOR_FALSE, abs=1e-12)
    assert decision.state is TruthState.NO
    assert decision.action is not None
    assert decision.action.name == "withhold"


def test_maybe_asks_for_clarification() -> None:
    # Widen the MAYBE band so the 0.9337 posterior is no longer actionable.
    settings = Settings()
    settings.u.thresholds.max_uncertainty_for_action = 0.05
    engine = build_u_engine(settings)
    decision = engine.reason("session-001", _observation())
    assert decision.state is TruthState.MAYBE
    assert decision.action is not None
    assert decision.action.name == "ask_for_clarification"
    assert decision.action.name not in HIGH_IMPACT_ACTIONS


def test_bias_failure_withholds() -> None:
    settings = Settings()
    engine = build_u_engine(settings)
    # Poison the ontology: create a semantic path from a protected attribute
    # to the proposition. The audit must fail and the planner must withhold.
    engine.ontology.relate("ethnicity", "influences", "participant_requests_turn")
    decision = engine.reason("session-001", _observation())
    assert not decision.bias_audit.passed
    assert ["ethnicity", "participant_requests_turn"] in decision.bias_audit.protected_paths
    assert decision.action is not None
    assert decision.action.name == "withhold_and_flag"
    assert decision.action.name not in HIGH_IMPACT_ACTIONS


def test_explanation_traces_phi_and_flash(engine) -> None:
    decision = engine.reason("session-001", _observation())
    text = " ".join(decision.explanation)
    assert "P(phi | evidence)" in text
    assert "Flash: observation.hand_raised -> communication.request_turn" in text
    assert "Selected action: announce_hand_raise." in text
