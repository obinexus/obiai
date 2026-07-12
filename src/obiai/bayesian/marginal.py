"""Explicit discrete phi-marginalization (Unbiased AI paper, section 6).

The paper prescribes debiasing by marginalizing over a bias/confounding
parameter phi instead of optimizing a single point estimate:

    P(theta | D) = integral P(theta, phi | D) d phi

For a discrete phi this is the exact mixture

    P(theta | D) = sum_phi P(theta | D, phi) * P(phi | D)
    P(phi | D)   = P(D | phi) * P(phi) / sum_phi' P(D | phi') * P(phi')

Each phi value carries its own :class:`~obiai.bayes.BayesianNetwork` (same
structure, different CPTs — e.g. a well-calibrated vs. a miscalibrated
sensor model), so the marginalization is exact, auditable, and requires no
sampler.
"""

from __future__ import annotations

from typing import Mapping

from obiai.bayes import BayesianNetwork

__all__ = ["PhiMarginalizedNetwork"]

_PRIOR_TOLERANCE = 1e-9


class PhiMarginalizedNetwork:
    """Mixture of exact Bayesian networks indexed by a discrete bias parameter phi."""

    def __init__(
        self,
        phi_prior: Mapping[str, float],
        networks: Mapping[str, BayesianNetwork],
    ) -> None:
        if set(phi_prior) != set(networks):
            raise ValueError(
                "phi_prior and networks must share the same phi values; "
                f"got {sorted(phi_prior)} vs {sorted(networks)}"
            )
        if not phi_prior:
            raise ValueError("At least one phi value is required")
        if any(weight <= 0.0 for weight in phi_prior.values()):
            raise ValueError("Every phi prior probability must be positive")
        total = sum(phi_prior.values())
        if abs(total - 1.0) > _PRIOR_TOLERANCE:
            raise ValueError(f"phi prior must sum to 1.0, got {total}")

        self.phi_prior: dict[str, float] = dict(phi_prior)
        self.networks: dict[str, BayesianNetwork] = dict(networks)

    def query(self, target: str, evidence: Mapping[str, bool]) -> float:
        """P(target=True | evidence), marginalized over phi."""
        weights = self._evidence_weights(evidence)
        total = sum(weights.values())
        if total == 0.0:
            # Evidence impossible under every phi; fall back to ignorance.
            return 0.5
        posterior = sum(
            weights[phi] * self.networks[phi].query(target, evidence)
            for phi in weights
        )
        return posterior / total

    def phi_posterior(self, evidence: Mapping[str, bool]) -> dict[str, float]:
        """P(phi | evidence) — surfaced in decision explanations for auditability."""
        weights = self._evidence_weights(evidence)
        total = sum(weights.values())
        if total == 0.0:
            return dict(self.phi_prior)
        return {phi: weight / total for phi, weight in weights.items()}

    def _evidence_weights(self, evidence: Mapping[str, bool]) -> dict[str, float]:
        # P(D | phi) * P(phi), the unnormalized posterior over phi.
        return {
            phi: self.phi_prior[phi] * self.networks[phi].probability_of(evidence)
            for phi in self.phi_prior
        }
