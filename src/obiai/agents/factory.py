"""Wires the concrete U engine for the raised-hand vertical slice."""

from __future__ import annotations

from obiai.bayes import BayesianNetwork, BinaryNode
from obiai.bayesian import PhiMarginalizedNetwork
from obiai.bias import BiasAuditor
from obiai.core.config import Settings, load_settings
from obiai.agents.engine import UReasoningEngine
from obiai.agents.planner import UPlanner
from obiai.ontology import Ontology
from obiai.ontology.mapper import EventOntologyMapper
from obiai.safety import SafetyAuditor

__all__ = ["build_u_engine", "build_u_ontology", "build_hand_raise_reasoner"]

PROPOSITION = "participant_requests_turn"
OBSERVABLE = "participant_raised_hand"

# Sensor-model CPTs per phi value (paper section 6: phi is the modeled
# bias/miscalibration factor marginalized out of the posterior).
_PHI_CPTS: dict[str, tuple[float, float]] = {
    # phi -> (P(raised | requests_turn), P(raised | not requests_turn))
    "calibrated": (0.97, 0.03),
    "miscalibrated": (0.70, 0.40),
}


def build_hand_raise_reasoner(settings: Settings) -> PhiMarginalizedNetwork:
    prior = settings.u.phi.prior
    unknown = set(prior) - set(_PHI_CPTS)
    if unknown:
        raise ValueError(
            f"No sensor model defined for phi values {sorted(unknown)}; "
            f"known values: {sorted(_PHI_CPTS)}"
        )
    networks: dict[str, BayesianNetwork] = {}
    for phi in prior:
        p_true, p_false = _PHI_CPTS[phi]
        network = BayesianNetwork()
        network.add(BinaryNode(PROPOSITION, cpt={(): 0.5}))
        network.add(
            BinaryNode(
                OBSERVABLE,
                parents=(PROPOSITION,),
                cpt={(True,): p_true, (False,): p_false},
            )
        )
        networks[phi] = network
    return PhiMarginalizedNetwork(phi_prior=prior, networks=networks)


def build_u_ontology(settings: Settings) -> Ontology:
    ontology = Ontology()
    ontology.relate("vision.hand_raise", "indicates", "communication.request_turn")
    ontology.relate("communication.request_turn", "supports", PROPOSITION)
    # Protected attributes are present as isolated concepts: the bias audit
    # proves no semantic path connects them to any proposition.
    for attribute in settings.bias.protected_attributes:
        ontology.add_concept(attribute, protected=True)
    return ontology


def build_u_engine(settings: Settings | None = None) -> UReasoningEngine:
    settings = settings if settings is not None else load_settings()
    ontology = build_u_ontology(settings)
    return UReasoningEngine(
        reasoner=build_hand_raise_reasoner(settings),
        ontology=ontology,
        mapper=EventOntologyMapper(),
        bias_auditor=BiasAuditor(
            settings.bias.protected_attributes,
            max_gap=settings.bias.maximum_demographic_parity_gap,
        ),
        safety_auditor=SafetyAuditor(
            allowed_event_types=settings.u.vision.allowed_event_types,
            forbidden_categories=settings.u.safety.forbidden_inference_categories,
        ),
        planner=UPlanner(),
        settings=settings,
    )
