from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Mapping


@dataclass(slots=True)
class BinaryNode:
    name: str
    parents: tuple[str, ...] = ()
    # Maps parent truth tuple to P(node=True). Root nodes use key ().
    cpt: dict[tuple[bool, ...], float] = field(default_factory=dict)

    def probability(self, value: bool, assignment: Mapping[str, bool]) -> float:
        key = tuple(bool(assignment[parent]) for parent in self.parents)
        p_true = self.cpt[key]
        return p_true if value else 1.0 - p_true


class BayesianNetwork:
    """Small exact binary Bayesian network suitable for auditable prototypes."""

    def __init__(self) -> None:
        self.nodes: dict[str, BinaryNode] = {}

    def add(self, node: BinaryNode) -> None:
        missing = [parent for parent in node.parents if parent not in self.nodes]
        if missing:
            raise ValueError(f"Parents must be added first: {missing}")
        self.nodes[node.name] = node

    def query(self, target: str, evidence: Mapping[str, bool]) -> float:
        if target not in self.nodes:
            raise KeyError(target)
        numerator = self._enumerate({**evidence, target: True})
        denominator = numerator + self._enumerate({**evidence, target: False})
        return 0.5 if denominator == 0 else numerator / denominator

    def _enumerate(self, fixed: Mapping[str, bool]) -> float:
        names = list(self.nodes)
        unknown = [name for name in names if name not in fixed]
        total = 0.0
        for values in product([False, True], repeat=len(unknown)):
            assignment = dict(fixed)
            assignment.update(dict(zip(unknown, values, strict=True)))
            joint = 1.0
            for name in names:
                joint *= self.nodes[name].probability(assignment[name], assignment)
            total += joint
        return total
