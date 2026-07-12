from __future__ import annotations

import networkx as nx


class Ontology:
    """Directed semantic graph with typed relations."""

    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def add_concept(self, name: str, **attributes: object) -> None:
        self.graph.add_node(name, **attributes)

    def relate(self, subject: str, relation: str, obj: str, **attributes: object) -> None:
        self.add_concept(subject)
        self.add_concept(obj)
        self.graph.add_edge(subject, obj, key=relation, relation=relation, **attributes)

    def ancestors(self, concept: str) -> set[str]:
        return nx.ancestors(nx.DiGraph(self.graph), concept)

    def paths(self, source: str, target: str, cutoff: int = 6) -> list[list[str]]:
        graph = nx.DiGraph(self.graph)
        if source not in graph or target not in graph:
            return []
        return list(nx.all_simple_paths(graph, source, target, cutoff=cutoff))

    def explain_relation(self, source: str, target: str) -> list[str]:
        explanations: list[str] = []
        for path in self.paths(source, target):
            explanations.append(" -> ".join(path))
        return explanations
