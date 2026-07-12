# Traceability: Unbiased AI paper → U implementation

Source specification: *Formal Argument for Bias in AI Systems: Bayesian Modeling
as a Proof Mechanism* (Nnamdi M. Okpala, OBINexus Computing, May 4 2025) —
`Ontological Bayesian Intelligence - July 2026/Unbiased_AI.pdf`.

Each paper concept is classified (per the project protocol, speculative claims
are not treated as proven) and mapped to the code that implements or records it.

| Paper concept | Classification | Implementation |
|---|---|---|
| §2 Hypothesis I — pattern learning replicates/amplifies bias `φ` in training data; `θ* = argmax P(θ\|D)` lands on a biased optimum | Hypothesis requiring validation | Motivates the marginalized design of [`src/obiai/bayesian/marginal.py`](../src/obiai/bayesian/marginal.py); no claim of validation is made in code |
| §3 Hypothesis II — "structural unboxing" (4D tensor → k-NN → 3D semantic map) | Implementation proposal, underspecified | **Deferred.** No formal semantics are given in the paper; nothing implements it and nothing should until it is specified |
| §4 Hypothesis III — modular core with dynamically loaded voice/vision/accessibility/robotics modules | Design requirement | [`src/obiai/modules/loader.py`](../src/obiai/modules/loader.py) (`ModuleRegistry`, pre-existing), wired into app startup in [`src/obiai/api/app.py`](../src/obiai/api/app.py) via `modules.enabled` in [`config/obiai.yaml`](../config/obiai.yaml) |
| §5 Bayesian network with protected attribute A; unbiased factorization `P(T\|S,C,A) = P(T\|C,S)·P′(A)` (T independent of A given the legitimate evidence) | Formal definition | Structural audit in [`src/obiai/bias.py`](../src/obiai/bias.py) `BiasAuditor.audit_paths` — fails any decision whose proposition is reachable from a protected attribute in the ontology; input-side enforcement in [`src/obiai/safety/validator.py`](../src/obiai/safety/validator.py) (observable-event allowlist + forbidden inference categories) |
| §6 / Appendix A — debiasing by marginalization: `P(θ\|D) = ∫ P(θ,φ\|D) dφ` | Formal definition (derivation is a valid application of Bayes' rule) | [`src/obiai/bayesian/marginal.py`](../src/obiai/bayesian/marginal.py) `PhiMarginalizedNetwork` — exact discrete sum `Σ_φ P(θ\|D,φ)P(φ\|D)`; equivalence with an explicit latent-φ network is proven to 1e-12 in [`tests/test_marginal.py`](../tests/test_marginal.py) |
| §6 worked contrast: point estimate vs. posterior integration | Formal definition | `PhiMarginalizedNetwork.phi_posterior` surfaces `P(φ\|evidence)` in every decision explanation (see `UReasoningEngine.reason` in [`src/obiai/agents/engine.py`](../src/obiai/agents/engine.py)) |
| §8 expected-outcomes table (fairness High, transparency Complete, ...) | **Unsupported claim requiring validation** | Not hard-coded anywhere. The auditable Decision trace (evidence, provenance, audits, explanation) provides the *mechanism* for evaluating these claims; the claims themselves remain open |
| Appendix B — "use INLA or Stan" | Implementation note | Substituted (user-approved) with exact discrete enumeration ([`src/obiai/bayes.py`](../src/obiai/bayes.py)) — the networks in the vertical slice are small enough for exact inference; PyMC remains an optional extra for future models |

## Related formal source

The epistemic traversal implements **AEGIS-PROOF-1.2** (traversal cost
`C = α·KL(P_i‖P_j) + β·ΔH(S_i,S_j)`, `α+β=1`, `α,β>0`, cost ≥ 0, Filter-Flash
traversal): [`src/obiai/epistemic/dag.py`](../src/obiai/epistemic/dag.py) with
invariant tests in [`tests/test_epistemic.py`](../tests/test_epistemic.py) and
property tests in [`tests/test_properties.py`](../tests/test_properties.py).

## Hard guarantees carried by tests

| Invariant | Test |
|---|---|
| `0 ≤ posterior ≤ 1`, `0 ≤ uncertainty ≤ 1` | `tests/test_properties.py` |
| `α + β = 1` enforced, never silently normalized | `tests/test_properties.py`, `tests/test_epistemic.py` |
| traversal cost ≥ 0 | `tests/test_properties.py` |
| MAYBE never triggers a high-impact action | `tests/test_properties.py`, `tests/test_engine.py` |
| failed bias/safety audit → `withhold_and_flag` | `tests/test_properties.py`, `tests/test_engine.py` |
| protected-attribute path ⇒ bias audit fails | `tests/test_bias.py`, `tests/test_engine.py` |
| no raw media enters the pipeline (scalar-only observations) | `tests/test_safety.py`, `tests/test_api.py` |
| raised-hand posterior is exactly `943/1010 ≈ 0.9337` | `tests/test_marginal.py`, `tests/test_engine.py`, `tests/test_api.py` |
