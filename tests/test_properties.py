"""Property-based invariants (Hypothesis).

These encode the spec's hard guarantees:

* posteriors and uncertainties always live in [0, 1];
* alpha + beta = 1 is enforced, never silently normalized;
* traversal cost is never negative;
* a MAYBE state can never trigger a high-impact action.
"""

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from obiai.agents import HIGH_IMPACT_ACTIONS, UPlanner
from obiai.agents.engine import truth_state
from obiai.bayes import BayesianNetwork, BinaryNode
from obiai.bayesian import PhiMarginalizedNetwork
from obiai.core.config import ThresholdSettings
from obiai.core.models import BiasReport, SafetyAudit, TruthState
from obiai.epistemic import EpistemicDAG, SemanticBeliefNode

probability = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
open_probability = st.floats(min_value=0.01, max_value=0.99, allow_nan=False)


def _network(p_root: float, p_true: float, p_false: float) -> BayesianNetwork:
    network = BayesianNetwork()
    network.add(BinaryNode("t", cpt={(): p_root}))
    network.add(BinaryNode("d", parents=("t",), cpt={(True,): p_true, (False,): p_false}))
    return network


@given(
    p_root=open_probability,
    cal=st.tuples(open_probability, open_probability),
    mis=st.tuples(open_probability, open_probability),
    prior=st.floats(min_value=0.01, max_value=0.99),
    evidence_value=st.booleans(),
)
def test_marginal_posterior_always_in_unit_interval(p_root, cal, mis, prior, evidence_value):
    mixture = PhiMarginalizedNetwork(
        phi_prior={"cal": prior, "mis": 1.0 - prior},
        networks={"cal": _network(p_root, *cal), "mis": _network(p_root, *mis)},
    )
    posterior = mixture.query("t", {"d": evidence_value})
    assert 0.0 <= posterior <= 1.0


@given(posterior=probability)
def test_uncertainty_always_in_unit_interval(posterior):
    uncertainty = 1.0 - abs(posterior - 0.5) * 2.0
    assert 0.0 <= uncertainty <= 1.0 + 1e-12


@given(
    alpha=st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
    beta=st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
)
def test_alpha_beta_constraint_enforced(alpha, beta):
    valid = bool(np.isclose(alpha + beta, 1.0)) and alpha > 0 and beta > 0
    if valid:
        EpistemicDAG(alpha=alpha, beta=beta)
    else:
        try:
            EpistemicDAG(alpha=alpha, beta=beta)
        except ValueError:
            return
        raise AssertionError("invalid alpha/beta accepted")


@given(
    p_i=open_probability,
    p_j=open_probability,
    h_i=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    h_j=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
)
def test_traversal_cost_never_negative(p_i, p_j, h_i, h_j):
    dag = EpistemicDAG(alpha=0.6, beta=0.4)
    node_i = SemanticBeliefNode("i", P=np.array([p_i, 1.0 - p_i]), H_S=h_i)
    node_j = SemanticBeliefNode("j", P=np.array([p_j, 1.0 - p_j]), H_S=h_j)
    assert dag.calculate_traversal_cost(node_i, node_j) >= 0.0


@given(posterior=probability, uncertainty=probability)
def test_maybe_never_triggers_high_impact_action(posterior, uncertainty):
    thresholds = ThresholdSettings()
    state = truth_state(posterior, uncertainty, thresholds)
    action = UPlanner().plan(
        state,
        "participant_requests_turn",
        posterior,
        uncertainty,
        BiasReport(),
        SafetyAudit(),
    )
    if state is TruthState.MAYBE:
        assert action.name == "ask_for_clarification"
        assert action.name not in HIGH_IMPACT_ACTIONS


@given(posterior=probability, uncertainty=probability)
def test_failed_audit_never_triggers_high_impact_action(posterior, uncertainty):
    thresholds = ThresholdSettings()
    state = truth_state(posterior, uncertainty, thresholds)
    action = UPlanner().plan(
        state,
        "participant_requests_turn",
        posterior,
        uncertainty,
        BiasReport(passed=False, protected_paths=[["ethnicity", "participant_requests_turn"]]),
        SafetyAudit(),
    )
    assert action.name == "withhold_and_flag"
    assert action.name not in HIGH_IMPACT_ACTIONS
