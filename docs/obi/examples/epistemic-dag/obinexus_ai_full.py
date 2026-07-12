from __future__ import annotations 
from pathlib import Path

"""
OBINexus AI Prototype
---------------------
A minimal implementation of the Actor-vs-Agent architecture described by
Nnamdi Michael Okpala / OBINexus.

This prototype includes:
- Fixed Agent action space
- Actor-generated CustomAct proposals
- Cost-function governance
- Governance zones
- Dynamic-to-static reduction
- Verification pipeline
- Epistemic certainty checks
- Lightweight DBFT-style weighted consensus
- Demo execution
- Unit tests

This is a research prototype, not a safety-certified production system.
"""

from dataclasses import dataclass, field
from enum import Enum
from math import exp, log
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import hashlib
import json
import time
import unittest


# ============================================================
# Core enums
# ============================================================

class DecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_GOVERNANCE = "NEEDS_GOVERNANCE"


class GovernanceZone(str, Enum):
    AUTONOMOUS = "AUTONOMOUS"
    WARNING = "WARNING"
    GOVERNANCE = "GOVERNANCE"


# ============================================================
# Core data structures
# ============================================================

@dataclass(frozen=True)
class Evidence:
    """
    A single evidence item used to estimate epistemic certainty.

    reliability and relevance are normalized to [0, 1].
    """

    name: str
    reliability: float
    relevance: float

    def score(self) -> float:
        return _clamp01(self.reliability) * _clamp01(self.relevance)


@dataclass
class ActionResult:
    action_name: str
    output: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """
    A verified Agent-level action.
    """

    name: str
    execute: Callable[[Mapping[str, Any]], ActionResult]
    safety_tags: Tuple[str, ...] = ()
    version: int = 1


@dataclass
class CustomAct:
    """
    A dynamically proposed Actor-level action.
    """

    name: str
    description: str
    execute: Callable[[Mapping[str, Any]], ActionResult]

    # Governance cost terms, normalized to [0, 1].
    epistemic_divergence: float
    entropy_delta: float
    semantic_risk: float
    dimensionality_cost: float

    evidence: Sequence[Evidence] = ()
    safety_tags: Tuple[str, ...] = ()
    created_at: float = field(default_factory=time.time)
    proposer_id: str = "actor-unknown"

    def certainty(self) -> float:
        """
        Combine multiple evidence items using complement-product aggregation.

        certainty = 1 - product(1 - evidence_score)
        """
        if not self.evidence:
            return 0.0

        remaining_uncertainty = 1.0

        for item in self.evidence:
            remaining_uncertainty *= 1.0 - item.score()

        return _clamp01(1.0 - remaining_uncertainty)


@dataclass(frozen=True)
class GovernanceWeights:
    alpha: float = 0.25
    beta: float = 0.20
    gamma: float = 0.20
    delta: float = 0.15
    epsilon: float = 0.20

    def normalized(self) -> "GovernanceWeights":
        values = [
            self.alpha,
            self.beta,
            self.gamma,
            self.delta,
            self.epsilon,
        ]

        total = sum(values)

        if total <= 0:
            raise ValueError("Governance weights must have a positive total.")

        return GovernanceWeights(*(value / total for value in values))


@dataclass
class VerificationReport:
    action_name: str
    status: DecisionStatus
    zone: GovernanceZone
    total_cost: float
    certainty: float
    checks: Dict[str, bool]
    reasons: List[str]
    signature: str
    reduced_action: Optional[Action] = None


@dataclass
class GovernancePolicy:
    autonomous_max: float = 0.50
    warning_max: float = 0.60
    minimum_certainty: float = 0.70
    maximum_semantic_risk: float = 0.75
    maximum_dimensionality_cost: float = 0.80
    weights: GovernanceWeights = field(default_factory=GovernanceWeights)

    def __post_init__(self) -> None:
        if not 0.0 <= self.autonomous_max <= 1.0:
            raise ValueError("autonomous_max must be in [0, 1].")

        if not 0.0 <= self.warning_max <= 1.0:
            raise ValueError("warning_max must be in [0, 1].")

        if self.autonomous_max > self.warning_max:
            raise ValueError("autonomous_max cannot exceed warning_max.")

        if not 0.0 <= self.minimum_certainty <= 1.0:
            raise ValueError("minimum_certainty must be in [0, 1].")

    def zone_for(self, cost: float) -> GovernanceZone:
        if cost <= self.autonomous_max:
            return GovernanceZone.AUTONOMOUS

        if cost <= self.warning_max:
            return GovernanceZone.WARNING

        return GovernanceZone.GOVERNANCE


# ============================================================
# Governance and verification
# ============================================================

class CostFunctionGovernance:
    def __init__(self, policy: Optional[GovernancePolicy] = None) -> None:
        self.policy = policy or GovernancePolicy()

    def compute_cost(self, act: CustomAct) -> float:
        """
        Compute the OBINexus-style traversal cost.

        C =
            alpha   * epistemic_divergence
          + beta    * entropy_delta
          + gamma   * semantic_risk
          + delta   * dimensionality_cost
          + epsilon * certainty_penalty
        """
        weights = self.policy.weights.normalized()
        certainty_penalty = 1.0 - act.certainty()

        cost = (
            weights.alpha * _clamp01(act.epistemic_divergence)
            + weights.beta * _clamp01(act.entropy_delta)
            + weights.gamma * _clamp01(act.semantic_risk)
            + weights.delta * _clamp01(act.dimensionality_cost)
            + weights.epsilon * certainty_penalty
        )

        return _clamp01(cost)

    def verify(self, act: CustomAct) -> VerificationReport:
        certainty = act.certainty()
        cost = self.compute_cost(act)
        zone = self.policy.zone_for(cost)

        checks = {
            "name_present": bool(act.name.strip()),
            "description_present": bool(act.description.strip()),
            "callable_present": callable(act.execute),
            "certainty_threshold_reached": (
                certainty >= self.policy.minimum_certainty
            ),
            "semantic_risk_bounded": (
                act.semantic_risk <= self.policy.maximum_semantic_risk
            ),
            "dimensionality_bounded": (
                act.dimensionality_cost
                <= self.policy.maximum_dimensionality_cost
            ),
            "cost_not_governance_zone": (
                zone != GovernanceZone.GOVERNANCE
            ),
        }

        reasons: List[str] = []

        if not checks["certainty_threshold_reached"]:
            reasons.append(
                f"Epistemic certainty {certainty:.3f} is below "
                f"{self.policy.minimum_certainty:.3f}."
            )

        if not checks["semantic_risk_bounded"]:
            reasons.append("Semantic risk exceeds the allowed bound.")

        if not checks["dimensionality_bounded"]:
            reasons.append("Dimensional expansion exceeds the allowed bound.")

        if zone == GovernanceZone.GOVERNANCE:
            reasons.append(
                "Traversal cost requires human or external governance."
            )

        if not checks["name_present"]:
            reasons.append("Action name is missing.")

        if not checks["description_present"]:
            reasons.append("Action description is missing.")

        if not checks["callable_present"]:
            reasons.append("Action implementation is not callable.")

        required_checks = [
            checks["name_present"],
            checks["description_present"],
            checks["callable_present"],
            checks["certainty_threshold_reached"],
            checks["semantic_risk_bounded"],
            checks["dimensionality_bounded"],
        ]

        if not all(required_checks):
            status = DecisionStatus.REJECTED
        elif zone == GovernanceZone.GOVERNANCE:
            status = DecisionStatus.NEEDS_GOVERNANCE
        else:
            status = DecisionStatus.APPROVED

        reduced_action = (
            self.reduce_to_static(act)
            if status == DecisionStatus.APPROVED
            else None
        )

        signature = self._sign_report(
            act=act,
            cost=cost,
            certainty=certainty,
            zone=zone,
            checks=checks,
        )

        return VerificationReport(
            action_name=act.name,
            status=status,
            zone=zone,
            total_cost=cost,
            certainty=certainty,
            checks=checks,
            reasons=reasons,
            signature=signature,
            reduced_action=reduced_action,
        )

    def reduce_to_static(self, act: CustomAct) -> Action:
        """
        Dynamic-to-static reduction.

        The Actor proposal becomes a normal Agent-level Action.
        """
        version_seed = json.dumps(
            {
                "name": act.name,
                "description": act.description,
                "tags": act.safety_tags,
                "proposer": act.proposer_id,
            },
            sort_keys=True,
        ).encode("utf-8")

        version = int(
            hashlib.sha256(version_seed).hexdigest()[:8],
            16,
        )

        return Action(
            name=act.name,
            execute=act.execute,
            safety_tags=tuple(
                sorted(
                    set(
                        act.safety_tags
                        + ("verified-custom-act",)
                    )
                )
            ),
            version=version,
        )

    @staticmethod
    def _sign_report(
        act: CustomAct,
        cost: float,
        certainty: float,
        zone: GovernanceZone,
        checks: Mapping[str, bool],
    ) -> str:
        payload = {
            "name": act.name,
            "description": act.description,
            "proposer": act.proposer_id,
            "cost": round(cost, 8),
            "certainty": round(certainty, 8),
            "zone": zone.value,
            "checks": dict(sorted(checks.items())),
        }

        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(raw).hexdigest()


# ============================================================
# Agent and Actor
# ============================================================

class Agent:
    """
    Operates only inside a fixed, verified action space.
    """

    def __init__(self) -> None:
        self._actions: Dict[str, Action] = {}

    def register(self, action: Action) -> None:
        if action.name in self._actions:
            raise ValueError(
                f"Action already registered: {action.name}"
            )

        self._actions[action.name] = action

    def has_action(self, name: str) -> bool:
        return name in self._actions

    def act(
        self,
        name: str,
        context: Mapping[str, Any],
    ) -> ActionResult:
        try:
            action = self._actions[name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown Agent action: {name}"
            ) from exc

        return action.execute(context)

    def action_names(self) -> List[str]:
        return sorted(self._actions)


class Actor:
    """
    Proposes novel actions, but cannot directly add them to production.
    """

    def __init__(
        self,
        actor_id: str,
        agent: Agent,
        governance: CostFunctionGovernance,
    ) -> None:
        self.actor_id = actor_id
        self.agent = agent
        self.governance = governance
        self.audit_log: List[VerificationReport] = []

    def propose(self, act: CustomAct) -> VerificationReport:
        act.proposer_id = self.actor_id

        report = self.governance.verify(act)
        self.audit_log.append(report)

        if (
            report.status == DecisionStatus.APPROVED
            and report.reduced_action is not None
        ):
            self.agent.register(report.reduced_action)

        return report


# ============================================================
# DBFT-style weighted consensus
# ============================================================

@dataclass(frozen=True)
class ConsensusProposal:
    actor_id: str
    value: str
    certainty: float
    trust: float
    governance_cost: float

    def weight(self) -> float:
        return (
            _clamp01(self.certainty)
            * _clamp01(self.trust)
            * (1.0 - _clamp01(self.governance_cost))
        )


@dataclass
class ConsensusResult:
    accepted_value: Optional[str]
    scores: Dict[str, float]
    total_weight: float
    reached: bool


class DBFTConsensus:
    """
    Lightweight Dimensional Byzantine Fault Tolerance analogue.

    This is a research demonstration, not a production BFT protocol.
    """

    def __init__(self, quorum_ratio: float = 2 / 3) -> None:
        if not 0.5 < quorum_ratio <= 1.0:
            raise ValueError(
                "quorum_ratio must be in (0.5, 1.0]."
            )

        self.quorum_ratio = quorum_ratio

    def resolve(
        self,
        proposals: Iterable[ConsensusProposal],
    ) -> ConsensusResult:
        scores: Dict[str, float] = {}
        total_weight = 0.0

        for proposal in proposals:
            proposal_weight = proposal.weight()
            total_weight += proposal_weight

            scores[proposal.value] = (
                scores.get(proposal.value, 0.0)
                + proposal_weight
            )

        if total_weight <= 0.0:
            return ConsensusResult(
                accepted_value=None,
                scores=scores,
                total_weight=0.0,
                reached=False,
            )

        accepted_value, accepted_score = max(
            scores.items(),
            key=lambda item: item[1],
        )

        reached = (
            accepted_score / total_weight
            >= self.quorum_ratio
        )

        return ConsensusResult(
            accepted_value=accepted_value if reached else None,
            scores=scores,
            total_weight=total_weight,
            reached=reached,
        )


# ============================================================
# High-level runtime
# ============================================================

class OBINexusRuntime:
    """
    High-level integration point for Agent, Actor, and governance.
    """

    def __init__(
        self,
        policy: Optional[GovernancePolicy] = None,
    ) -> None:
        self.agent = Agent()
        self.governance = CostFunctionGovernance(policy)
        self.actors: Dict[str, Actor] = {}

    def create_actor(self, actor_id: str) -> Actor:
        if actor_id in self.actors:
            raise ValueError(
                f"Actor already exists: {actor_id}"
            )

        actor = Actor(
            actor_id=actor_id,
            agent=self.agent,
            governance=self.governance,
        )

        self.actors[actor_id] = actor
        return actor

    def execute_or_innovate(
        self,
        requested_action: str,
        context: Mapping[str, Any],
        actor_id: str,
        custom_act_factory: Callable[
            [Mapping[str, Any]],
            CustomAct,
        ],
    ) -> Tuple[
        Optional[ActionResult],
        Optional[VerificationReport],
    ]:
        """
        Agent-first, Actor-second execution flow.

        1. Execute a known verified Agent action.
        2. Otherwise create an Actor proposal.
        3. Verify the proposal.
        4. Execute only when approved.
        """
        if self.agent.has_action(requested_action):
            return (
                self.agent.act(requested_action, context),
                None,
            )

        try:
            actor = self.actors[actor_id]
        except KeyError as exc:
            raise KeyError(
                f"Unknown Actor: {actor_id}"
            ) from exc

        custom_act = custom_act_factory(context)

        if custom_act.name != requested_action:
            raise ValueError(
                "CustomAct name must match the requested action "
                f"({custom_act.name!r} != "
                f"{requested_action!r})."
            )

        report = actor.propose(custom_act)

        if report.status == DecisionStatus.APPROVED:
            return (
                self.agent.act(requested_action, context),
                report,
            )

        return None, report


# ============================================================
# Mathematical helpers
# ============================================================

def logistic_trust(
    weighted_success: float,
    k: float = 8.0,
    theta: float = 0.5,
) -> float:
    """
    Trust growth/decay function:

        psi(t) = 1 / (1 + exp(-k(success - theta)))
    """
    return 1.0 / (
        1.0
        + exp(
            -k * (
                weighted_success - theta
            )
        )
    )


def bernoulli_kl(
    p: float,
    q: float,
    epsilon: float = 1e-9,
) -> float:
    """
    Normalized Bernoulli KL divergence helper.
    """
    p = min(
        max(p, epsilon),
        1.0 - epsilon,
    )

    q = min(
        max(q, epsilon),
        1.0 - epsilon,
    )

    value = (
        p * log(p / q)
        + (1.0 - p)
        * log(
            (1.0 - p)
            / (1.0 - q)
        )
    )

    return _clamp01(value)


def _clamp01(value: float) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


# ============================================================
# Demo actions
# ============================================================

def pass_ball(
    context: Mapping[str, Any],
) -> ActionResult:
    teammate = context.get(
        "teammate",
        "unknown teammate",
    )

    return ActionResult(
        action_name="pass",
        output={
            "to": teammate,
            "status": "completed",
        },
    )


def build_dribble(
    context: Mapping[str, Any],
) -> CustomAct:
    def dribble(
        verified_context: Mapping[str, Any],
    ) -> ActionResult:
        distance = verified_context.get(
            "distance_m",
            1,
        )

        return ActionResult(
            action_name="dribble",
            output={
                "distance_m": distance,
                "status": "completed",
            },
            metadata={
                "execution_mode": "verified-custom-act",
            },
        )

    return CustomAct(
        name="dribble",
        description=(
            "Move while maintaining controlled "
            "possession of the ball."
        ),
        execute=dribble,
        epistemic_divergence=0.20,
        entropy_delta=0.20,
        semantic_risk=0.15,
        dimensionality_cost=0.25,
        evidence=[
            Evidence(
                name="simulation",
                reliability=0.95,
                relevance=0.95,
            ),
            Evidence(
                name="rule-check",
                reliability=0.90,
                relevance=0.90,
            ),
        ],
        safety_tags=(
            "bounded-speed",
            "ball-control",
        ),
    )


def create_demo_runtime() -> Tuple[
    OBINexusRuntime,
    Actor,
]:
    runtime = OBINexusRuntime(
        GovernancePolicy(
            autonomous_max=0.50,
            warning_max=0.60,
            minimum_certainty=0.70,
        )
    )

    runtime.agent.register(
        Action(
            name="pass",
            execute=pass_ball,
            safety_tags=("safe",),
        )
    )

    actor = runtime.create_actor(
        "obinexus-actor-1"
    )

    return runtime, actor


# ============================================================
# Demo runner
# ============================================================

def run_demo() -> None:
    runtime, actor = create_demo_runtime()

    result, report = runtime.execute_or_innovate(
        requested_action="dribble",
        context={
            "distance_m": 3,
        },
        actor_id=actor.actor_id,
        custom_act_factory=build_dribble,
    )

    if report is None:
        raise RuntimeError(
            "Expected an Actor verification report."
        )

    print("Verification:", report.status.value)
    print("Zone:", report.zone.value)
    print("Cost:", round(report.total_cost, 3))
    print("Certainty:", round(report.certainty, 3))
    print(
        "Result:",
        result.output if result else None,
    )
    print(
        "Registered actions:",
        runtime.agent.action_names(),
    )
    print(
        "Verification signature:",
        report.signature,
    )

    consensus = DBFTConsensus(
        quorum_ratio=2 / 3
    )

    consensus_result = consensus.resolve(
        [
            ConsensusProposal(
                actor_id="A",
                value="APPROVE",
                certainty=0.95,
                trust=0.90,
                governance_cost=0.15,
            ),
            ConsensusProposal(
                actor_id="B",
                value="APPROVE",
                certainty=0.90,
                trust=0.85,
                governance_cost=0.20,
            ),
            ConsensusProposal(
                actor_id="C",
                value="REJECT",
                certainty=0.60,
                trust=0.50,
                governance_cost=0.55,
            ),
        ]
    )

    print(
        "Consensus reached:",
        consensus_result.reached,
    )
    print(
        "Consensus value:",
        consensus_result.accepted_value,
    )
    print(
        "Consensus scores:",
        consensus_result.scores,
    )


# ============================================================
# Unit tests
# ============================================================

class OBINexusTests(unittest.TestCase):
    def test_safe_custom_act_is_registered(self) -> None:
        runtime = OBINexusRuntime(
            GovernancePolicy(
                minimum_certainty=0.70
            )
        )

        actor = runtime.create_actor(
            "actor-1"
        )

        act = CustomAct(
            name="safe_move",
            description=(
                "A bounded test movement."
            ),
            execute=lambda context: ActionResult(
                "safe_move",
                "ok",
            ),
            epistemic_divergence=0.10,
            entropy_delta=0.10,
            semantic_risk=0.10,
            dimensionality_cost=0.10,
            evidence=[
                Evidence(
                    "test-1",
                    0.95,
                    0.95,
                ),
                Evidence(
                    "test-2",
                    0.90,
                    0.90,
                ),
            ],
        )

        report = actor.propose(act)

        self.assertEqual(
            report.status,
            DecisionStatus.APPROVED,
        )

        self.assertTrue(
            runtime.agent.has_action(
                "safe_move"
            )
        )

    def test_low_certainty_is_rejected(self) -> None:
        runtime = OBINexusRuntime(
            GovernancePolicy(
                minimum_certainty=0.80
            )
        )

        actor = runtime.create_actor(
            "actor-1"
        )

        act = CustomAct(
            name="uncertain_move",
            description=(
                "An insufficiently supported action."
            ),
            execute=lambda context: ActionResult(
                "uncertain_move",
                "unsafe",
            ),
            epistemic_divergence=0.10,
            entropy_delta=0.10,
            semantic_risk=0.10,
            dimensionality_cost=0.10,
            evidence=[
                Evidence(
                    "weak",
                    0.20,
                    0.20,
                )
            ],
        )

        report = actor.propose(act)

        self.assertEqual(
            report.status,
            DecisionStatus.REJECTED,
        )

        self.assertFalse(
            runtime.agent.has_action(
                "uncertain_move"
            )
        )

    def test_governance_zone_requires_review(self) -> None:
        runtime = OBINexusRuntime(
            GovernancePolicy(
                autonomous_max=0.20,
                warning_max=0.30,
                minimum_certainty=0.50,
            )
        )

        actor = runtime.create_actor(
            "actor-review"
        )

        act = CustomAct(
            name="high_cost_move",
            description=(
                "A valid but high-cost action."
            ),
            execute=lambda context: ActionResult(
                "high_cost_move",
                "pending",
            ),
            epistemic_divergence=0.95,
            entropy_delta=0.90,
            semantic_risk=0.70,
            dimensionality_cost=0.75,
            evidence=[
                Evidence(
                    "strong",
                    0.95,
                    0.95,
                )
            ],
        )

        report = actor.propose(act)

        self.assertEqual(
            report.status,
            DecisionStatus.NEEDS_GOVERNANCE,
        )

        self.assertFalse(
            runtime.agent.has_action(
                "high_cost_move"
            )
        )

    def test_consensus_reaches_approval(self) -> None:
        consensus = DBFTConsensus(
            quorum_ratio=2 / 3
        )

        result = consensus.resolve(
            [
                ConsensusProposal(
                    "A",
                    "APPROVE",
                    0.95,
                    0.90,
                    0.15,
                ),
                ConsensusProposal(
                    "B",
                    "APPROVE",
                    0.90,
                    0.85,
                    0.20,
                ),
                ConsensusProposal(
                    "C",
                    "REJECT",
                    0.60,
                    0.50,
                    0.55,
                ),
            ]
        )

        self.assertTrue(result.reached)
        self.assertEqual(
            result.accepted_value,
            "APPROVE",
        )


# ============================================================
# Entry point
# ============================================================

def main() -> None:
    print("=== OBINexus AI Demo ===")
    run_demo()

    print()
    print("=== OBINexus AI Tests ===")

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        OBINexusTests
    )

    runner = unittest.TextTestRunner(
        verbosity=2
    )

    result = runner.run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
