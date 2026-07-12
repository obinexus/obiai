from __future__ import annotations

from collections.abc import Iterable
from .ontology import Ontology
from .types import BiasReport


class BiasAuditor:
    def __init__(self, protected_attributes: Iterable[str], max_gap: float = 0.10) -> None:
        self.protected_attributes = set(protected_attributes)
        self.max_gap = max_gap

    def audit_paths(self, ontology: Ontology, decision_node: str) -> BiasReport:
        paths: list[list[str]] = []
        for attribute in sorted(self.protected_attributes):
            paths.extend(ontology.paths(attribute, decision_node))
        notes = []
        if paths:
            notes.append("Protected attribute has a semantic path to the decision node; review causality.")
        return BiasReport(protected_paths=paths, passed=not paths, notes=notes)

    def demographic_parity(self, positive_rates: dict[str, float]) -> BiasReport:
        if len(positive_rates) < 2:
            return BiasReport(notes=["At least two groups are required for parity measurement."])
        gap = max(positive_rates.values()) - min(positive_rates.values())
        return BiasReport(
            parity_gap=gap,
            passed=gap <= self.max_gap,
            notes=[f"Maximum permitted demographic-parity gap: {self.max_gap:.3f}"],
        )
