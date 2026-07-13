"""Apply the Unbiased AI paper's method to compute debiased SFT training weights.

Source: "Formal Argument for Bias in AI Systems: Bayesian Modeling as a Proof
Mechanism" (Okpala, OBINexus, May 2025) and its follow-up "A Bayesian Network
Framework for Mitigating Bias in Machine Learning Systems" (June 2026) —
section 5's unbiased factorization P(T|S,C,A) = P(T|C,S) * P'(A) and section
6/Algorithm 1's marginalization P(theta|D) = integral P(theta,phi|D) d phi.

What this script actually does, concretely:

    A = protected-attribute mention present in the example text (keyword
        proxy over the same categories obiai.core.config.BiasSettings uses:
        age_group, disability, ethnicity, gender)
    C = a content-quality confound, from OASST2's own review labels
        (not_appropriate / spam), independent of A
    T = "trustworthy training signal" (low toxicity / hate_speech)

Two Bayesian estimates of P(T=1 | C) are built exactly like the raised-hand
network in obiai.bayesian.PhiMarginalizedNetwork: one from the whole corpus
("raw" -- the traditional MLE estimate, which can be skewed by whichever
examples happen to mention protected attributes) and one from only the A=0
examples ("corrected" -- an estimate insulated from that skew). These are
mixed by a phi prior favoring the corrected estimate, giving each example a
debiased weight w_i = P(T=1 | C=c_i), independent of A by construction (the
factorization). Weights are used later as per-example loss weights in
train_qlora.py.

This is a heuristic, not a validated bias classifier -- keyword matching for
A and the OASST2 reviewers' own labels for C/T are both proxies. It is a
faithful implementation of the paper's marginalization *mechanism*, not a
claim that it eliminates bias. See ml/README.md for what is and is not
implemented from the source papers.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from obiai.bayes import BayesianNetwork, BinaryNode
from obiai.bayesian import PhiMarginalizedNetwork

ML_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ML_DIR / "data" / "oasst2" / "sft_pairs.jsonl"
DEFAULT_OUTPUT = ML_DIR / "data" / "oasst2" / "sft_pairs_weighted.jsonl"
DEFAULT_REPORT = ML_DIR / "data" / "oasst2" / "bias_audit_report.json"

# Same protected-attribute categories as obiai.core.config.BiasSettings,
# expanded into a small keyword lexicon. Crude by design -- see docstring.
PROTECTED_ATTRIBUTE_TERMS: dict[str, list[str]] = {
    "gender": [
        "woman", "women", "male", "female", "transgender", "nonbinary",
        "non-binary", "gender", "lesbian", "gay", "bisexual",
    ],
    "ethnicity": [
        "black", "white", "asian", "hispanic", "latino", "latina",
        "african", "race", "racial", "ethnicity", "indigenous",
    ],
    "disability": [
        "disability", "disabled", "wheelchair", "blind", "deaf",
        "autistic", "autism", "adhd",
    ],
    "age_group": [
        "elderly", "senior citizen", "teenager", "toddler", "infant",
        "young adult", "old age",
    ],
}
_TERM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for terms in PROTECTED_ATTRIBUTE_TERMS.values() for t in terms) + r")\b",
    re.IGNORECASE,
)

QUALITY_FLAG_THRESHOLD = 0.3
TRUST_THRESHOLD = 0.3
PHI_PRIOR = {"raw": 0.1, "corrected": 0.9}


def mentions_protected_attribute(text: str) -> bool:
    return _TERM_PATTERN.search(text) is not None


def label_value(labels: dict | None, key: str) -> float | None:
    if not labels:
        return None
    entry = labels.get(key)
    if not entry:
        return None
    return entry.get("value")


def compute_evidence(example: dict) -> tuple[bool, bool, bool]:
    text = example["prompt"] + example["completion"]
    a = mentions_protected_attribute(text)

    labels = example.get("labels")
    not_appropriate = label_value(labels, "not_appropriate")
    spam = label_value(labels, "spam")
    c = (not_appropriate is not None and not_appropriate >= QUALITY_FLAG_THRESHOLD) or (
        spam is not None and spam >= QUALITY_FLAG_THRESHOLD
    )

    toxicity = label_value(labels, "toxicity")
    hate_speech = label_value(labels, "hate_speech")
    # No labels at all -> assume trustworthy rather than penalize unlabeled data.
    if toxicity is None and hate_speech is None:
        t = True
    else:
        t = (toxicity is None or toxicity < TRUST_THRESHOLD) and (
            hate_speech is None or hate_speech < TRUST_THRESHOLD
        )
    return a, c, t


def build_cpt(examples: list[tuple[bool, bool, bool]], only_a: bool | None) -> dict[bool, float]:
    """P(T=1 | C=c) estimated over the given subset (Laplace-smoothed)."""
    counts = {False: [0, 0], True: [0, 0]}  # c -> [T=1 count, total count]
    for a, c, t in examples:
        if only_a is not None and a != only_a:
            continue
        counts[c][1] += 1
        if t:
            counts[c][0] += 1
    return {
        c: (hits + 1) / (total + 2)  # Laplace smoothing avoids 0/1 CPT entries
        for c, (hits, total) in counts.items()
    }


def build_marginalized_network(evidence: list[tuple[bool, bool, bool]]) -> PhiMarginalizedNetwork:
    c_prior = (sum(c for _, c, _ in evidence) + 1) / (len(evidence) + 2)
    raw_cpt = build_cpt(evidence, only_a=None)
    corrected_cpt = build_cpt(evidence, only_a=False)

    def network(cpt: dict[bool, float]) -> BayesianNetwork:
        net = BayesianNetwork()
        net.add(BinaryNode("C", cpt={(): c_prior}))
        net.add(BinaryNode("T", parents=("C",), cpt={(True,): cpt[True], (False,): cpt[False]}))
        return net

    return PhiMarginalizedNetwork(
        phi_prior=PHI_PRIOR,
        networks={"raw": network(raw_cpt), "corrected": network(corrected_cpt)},
    )


def parity_gap(weights: list[float], protected: list[bool]) -> float | None:
    """Theorem 5.2-style demographic-parity gap: |mean(A=1) - mean(A=0)|."""
    group_a = [w for w, a in zip(weights, protected) if a]
    group_not_a = [w for w, a in zip(weights, protected) if not a]
    if not group_a or not group_not_a:
        return None
    mean_a = sum(group_a) / len(group_a)
    mean_not_a = sum(group_not_a) / len(group_not_a)
    return abs(mean_a - mean_not_a)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"{args.input} not found -- run scripts/prepare_data.py first.")

    examples = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line]
    evidence = [compute_evidence(ex) for ex in examples]

    mix = build_marginalized_network(evidence)
    raw_only = mix.networks["raw"]

    raw_weights = [raw_only.query("T", {"C": c}) for _, c, _ in evidence]
    debiased_weights = [mix.query("T", {"C": c}) for _, c, _ in evidence]
    protected = [a for a, _, _ in evidence]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        for example, weight in zip(examples, debiased_weights):
            out.write(json.dumps({**example, "weight": weight}) + "\n")

    report = {
        "n_examples": len(examples),
        "n_protected_attribute_mentions": sum(protected),
        "phi_prior": PHI_PRIOR,
        "raw_demographic_parity_gap": parity_gap(raw_weights, protected),
        "debiased_demographic_parity_gap": parity_gap(debiased_weights, protected),
        "phi_posterior_examples": [
            mix.phi_posterior({"C": c}) for c in (False, True)
        ],
    }
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote {len(examples)} weighted examples -> {args.output}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
