"""UReasoningEngine: the observation-to-decision pipeline.

    Observation -> ontology mapping -> phi-marginalized Bayesian update
    -> epistemic DAG traversal -> bias audit -> safety audit
    -> YES / NO / MAYBE -> planned action -> auditable Decision

Every collaborator is injected behind a protocol from
:mod:`obiai.core.protocols`, so the engine never touches FastAPI, MediaPipe,
or any provider directly.
"""

from __future__ import annotations

from obiai.core.config import Settings, ThresholdSettings
from obiai.core.models import Decision, Observation, TruthState
from obiai.core.protocols import (
    AgentPlanner,
    BayesianReasoner,
    BiasAuditorProtocol,
    OntologyMapperProtocol,
    SafetyAuditorProtocol,
)
from obiai.epistemic import build_semantic_dag, traverse_semantic_path
from obiai.ontology import Ontology

__all__ = ["UReasoningEngine", "truth_state"]


def truth_state(
    probability: float, uncertainty: float, thresholds: ThresholdSettings
) -> TruthState:
    """YES / NO / MAYBE decision rule.

    YES and NO both require the uncertainty to be low enough to act on;
    anything else is MAYBE.
    """
    actionable = uncertainty <= thresholds.max_uncertainty_for_action
    if actionable and probability >= thresholds.yes_threshold:
        return TruthState.YES
    if actionable and probability <= thresholds.no_threshold:
        return TruthState.NO
    return TruthState.MAYBE


class UReasoningEngine:
    def __init__(
        self,
        reasoner: BayesianReasoner,
        ontology: Ontology,
        mapper: OntologyMapperProtocol,
        bias_auditor: BiasAuditorProtocol,
        safety_auditor: SafetyAuditorProtocol,
        planner: AgentPlanner,
        settings: Settings,
    ) -> None:
        self.reasoner = reasoner
        self.ontology = ontology
        self.mapper = mapper
        self.bias_auditor = bias_auditor
        self.safety_auditor = safety_auditor
        self.planner = planner
        self.settings = settings

    def reason(self, session_id: str, observation: Observation) -> Decision:
        thresholds = self.settings.u.thresholds
        explanation: list[str] = []

        # 1. Ontology mapping
        mapping = self.mapper.map(observation)
        explanation.append(
            f"Observation '{observation.event_type}' from {observation.source} "
            f"with confidence {observation.confidence:.2f}."
        )

        # 2. Bayesian update (phi-marginalized when the reasoner supports it)
        evidence_assignment = {mapping.bn_variable: bool(observation.value)}
        probability = self.reasoner.query(mapping.proposition, evidence_assignment)
        explanation.append(
            f"Posterior P({mapping.proposition} | {mapping.bn_variable}="
            f"{bool(observation.value)}) = {probability:.4f}."
        )
        phi_posterior = getattr(self.reasoner, "phi_posterior", None)
        if callable(phi_posterior):
            phi_weights = phi_posterior(evidence_assignment)
            rendered = ", ".join(f"{phi}={weight:.4f}" for phi, weight in phi_weights.items())
            explanation.append(f"Bias parameter posterior P(phi | evidence): {rendered}.")

        # 3. Uncertainty and truth state
        uncertainty = 1.0 - abs(probability - 0.5) * 2.0
        state = self._truth_state(probability, uncertainty)
        explanation.append(
            f"Uncertainty {uncertainty:.4f} "
            f"(max for action {thresholds.max_uncertainty_for_action:.2f}); state {state.value}."
        )

        # 4. Epistemic DAG traversal
        source, intermediate, target = mapping.semantic_chain
        dag = build_semantic_dag(
            probability,
            self.settings.u.epistemic,
            source=source,
            intermediate=intermediate,
            target=target,
            source_belief=observation.confidence,
        )
        path_result = traverse_semantic_path(dag, source, target, self.settings.u.epistemic)
        semantic_path = path_result.path if path_result else []
        if path_result:
            for flash in path_result.flash_events:
                explanation.append(
                    f"Flash: {flash.transition} (delta_H={flash.entropy_gradient:.2f})."
                )
        else:
            explanation.append(
                "No semantic path passed the epistemic filter; the semantic jump was rejected."
            )

        # 5. Bias audit (protected-attribute paths in the ontology)
        bias = self.bias_auditor.audit_paths(self.ontology, mapping.proposition)
        explanation.append(
            "Bias audit passed: no protected attribute reaches the proposition."
            if bias.passed
            else "Bias audit FAILED: a protected attribute has a semantic path to the proposition."
        )

        # 6. Safety audit (observable-events-only policy)
        safety = self.safety_auditor.audit(observation, mapping)
        if not safety.passed:
            explanation.append(f"Safety audit FAILED: {', '.join(safety.policy_flags)}.")

        # 7. Action selection
        action = self.planner.plan(
            state, mapping.proposition, probability, uncertainty, bias, safety
        )
        explanation.append(f"Selected action: {action.name}.")

        return Decision(
            session_id=session_id,
            proposition=mapping.proposition,
            probability=probability,
            uncertainty=uncertainty,
            state=state,
            evidence=[mapping.evidence],
            ontological_concepts=list(mapping.concepts),
            semantic_path=semantic_path,
            bias_audit=bias,
            safety_audit=safety,
            action=action,
            explanation=explanation,
        )

    def _truth_state(self, probability: float, uncertainty: float) -> TruthState:
        return truth_state(probability, uncertainty, self.settings.u.thresholds)
