"""Exact-number tests for phi-marginalization (Unbiased AI paper, section 6).

The raised-hand network per phi value:

    participant_requests_turn (T, root, P=0.5) -> participant_raised_hand (D)

    phi=calibrated   (prior 0.9): P(D|T)=0.97, P(D|~T)=0.03
    phi=miscalibrated(prior 0.1): P(D|T)=0.70, P(D|~T)=0.40

Hand-derived posteriors (see docs/traceability.md):

    P(T | D=true)  = 0.4715 / 0.505 = 943/1010 = 0.93366336...
    P(T | D=false) = 0.0285 / 0.495 = 19/330   = 0.05757575...
"""

import pytest

from obiai.bayes import BayesianNetwork, BinaryNode
from obiai.bayesian import PhiMarginalizedNetwork

T = "participant_requests_turn"
D = "participant_raised_hand"


def _network(p_d_given_t: float, p_d_given_not_t: float) -> BayesianNetwork:
    network = BayesianNetwork()
    network.add(BinaryNode(T, cpt={(): 0.5}))
    network.add(
        BinaryNode(D, parents=(T,), cpt={(True,): p_d_given_t, (False,): p_d_given_not_t})
    )
    return network


@pytest.fixture()
def phimix() -> PhiMarginalizedNetwork:
    return PhiMarginalizedNetwork(
        phi_prior={"calibrated": 0.9, "miscalibrated": 0.1},
        networks={
            "calibrated": _network(0.97, 0.03),
            "miscalibrated": _network(0.70, 0.40),
        },
    )


def test_per_phi_posteriors(phimix: PhiMarginalizedNetwork) -> None:
    assert phimix.networks["calibrated"].query(T, {D: True}) == pytest.approx(0.97, abs=1e-12)
    assert phimix.networks["miscalibrated"].query(T, {D: True}) == pytest.approx(
        7 / 11, abs=1e-12
    )


def test_marginal_posterior_matches_spec(phimix: PhiMarginalizedNetwork) -> None:
    posterior = phimix.query(T, {D: True})
    assert posterior == pytest.approx(943 / 1010, abs=1e-12)
    assert round(posterior, 2) == 0.93


def test_negative_evidence(phimix: PhiMarginalizedNetwork) -> None:
    assert phimix.query(T, {D: False}) == pytest.approx(19 / 330, abs=1e-12)


def test_empty_evidence_recovers_prior(phimix: PhiMarginalizedNetwork) -> None:
    assert phimix.query(T, {}) == pytest.approx(0.5, abs=1e-12)
    assert phimix.phi_posterior({}) == pytest.approx(
        {"calibrated": 0.9, "miscalibrated": 0.1}
    )


def test_phi_posterior_shifts_with_evidence(phimix: PhiMarginalizedNetwork) -> None:
    posterior = phimix.phi_posterior({D: True})
    assert posterior["calibrated"] == pytest.approx(0.45 / 0.505, abs=1e-12)
    assert posterior["miscalibrated"] == pytest.approx(0.055 / 0.505, abs=1e-12)
    assert sum(posterior.values()) == pytest.approx(1.0, abs=1e-12)


def test_equivalence_with_explicit_latent_phi(phimix: PhiMarginalizedNetwork) -> None:
    """The mixture must equal a single network with phi as an explicit latent root."""
    latent = BayesianNetwork()
    latent.add(BinaryNode("phi_calibrated", cpt={(): 0.9}))
    latent.add(BinaryNode(T, cpt={(): 0.5}))
    latent.add(
        BinaryNode(
            D,
            parents=(T, "phi_calibrated"),
            cpt={
                (True, True): 0.97,
                (False, True): 0.03,
                (True, False): 0.70,
                (False, False): 0.40,
            },
        )
    )
    assert latent.query(T, {D: True}) == pytest.approx(
        phimix.query(T, {D: True}), abs=1e-12
    )
    assert latent.query(T, {D: False}) == pytest.approx(
        phimix.query(T, {D: False}), abs=1e-12
    )


def test_prior_validation() -> None:
    networks = {"a": _network(0.9, 0.1), "b": _network(0.8, 0.2)}
    with pytest.raises(ValueError, match="sum to 1"):
        PhiMarginalizedNetwork({"a": 0.5, "b": 0.6}, networks)
    with pytest.raises(ValueError, match="positive"):
        PhiMarginalizedNetwork({"a": 1.0, "b": 0.0}, networks)
    with pytest.raises(ValueError, match="same phi"):
        PhiMarginalizedNetwork({"a": 1.0}, networks)
