from __future__ import annotations

from collections.abc import Mapping
from .bayes import BayesianNetwork
from .bias import BiasAuditor
from .ontology import Ontology
from .planner import Planner
from .types import Decision, Evidence, TruthState


class OBIAgent:
    def __init__(
        self,
        network: BayesianNetwork,
        ontology: Ontology,
        auditor: BiasAuditor,
        planner: Planner | None = None,
        decision_threshold: float = 0.60,
        uncertainty_threshold: float = 0.45,
    ) -> None:
        self.network = network
        self.ontology = ontology
        self.auditor = auditor
        self.planner = planner or Planner()
        self.decision_threshold = decision_threshold
        self.uncertainty_threshold = uncertainty_threshold

    def reason(self, proposition: str, evidence: Mapping[str, bool]) -> Decision:
        probability = self.network.query(proposition, evidence)
        uncertainty = 1.0 - abs(probability - 0.5) * 2.0
        if uncertainty > self.uncertainty_threshold:
            state = TruthState.MAYBE
        elif probability >= self.decision_threshold:
            state = TruthState.YES
        else:
            state = TruthState.NO

        bias = self.auditor.audit_paths(self.ontology, proposition)
        explanation = [
            f"Posterior P({proposition}=true | evidence) = {probability:.4f}",
            f"Uncertainty score = {uncertainty:.4f}",
        ]
        explanation.extend(self.ontology.explain_relation(next(iter(evidence), proposition), proposition))
        evidence_models = [Evidence(variable=k, value=v) for k, v in evidence.items()]
        actions = self.planner.plan(proposition, probability, uncertainty)
        return Decision(
            proposition=proposition,
            probability=probability,
            uncertainty=uncertainty,
            state=state,
            explanation=explanation,
            evidence=evidence_models,
            bias=bias,
            actions=actions,
        )
