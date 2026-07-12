import heapq
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass(frozen=True)
class SemanticBeliefNode:
    """A probabilistic semantic belief state in an epistemological DAG."""

    node_id: str
    P: np.ndarray
    H_S: float

    def __post_init__(self) -> None:
        p = np.asarray(self.P, dtype=float)
        if p.ndim != 1:
            raise ValueError("P must be a 1D probability vector.")
        if np.any(p < 0):
            raise ValueError("P must not contain negative probabilities.")
        total = float(np.sum(p))
        if not np.isclose(total, 1.0):
            raise ValueError(f"P must sum to 1.0; got {total}.")
        object.__setattr__(self, "P", p)

    @property
    def H_P(self) -> float:
        p_safe = np.clip(self.P, 1e-12, 1.0)
        return float(-np.sum(self.P * np.log2(p_safe)))


class EpistemicDAG:
    """Cost-weighted traversal engine for AEGIS epistemological inference."""

    def __init__(self, alpha: float = 0.5, beta: float = 0.5, epsilon_min: float = 1e-12):
        if not np.isclose(alpha + beta, 1.0):
            raise ValueError("Normalization constraint violated: alpha + beta must equal 1.0")
        if alpha <= 0 or beta <= 0:
            raise ValueError("Non-degeneracy constraint violated: alpha, beta must be > 0")
        if epsilon_min <= 0:
            raise ValueError("epsilon_min must be > 0")

        self.alpha = float(alpha)
        self.beta = float(beta)
        self.epsilon_min = float(epsilon_min)
        self.nodes: Dict[str, SemanticBeliefNode] = {}
        self.edges: Dict[str, List[str]] = {}

    def add_node(self, node: SemanticBeliefNode) -> None:
        self.nodes[node.node_id] = node
        self.edges.setdefault(node.node_id, [])

    def _has_path(self, start_id: str, target_id: str) -> bool:
        stack = [start_id]
        seen = set()
        while stack:
            current = stack.pop()
            if current == target_id:
                return True
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self.edges.get(current, []))
        return False

    def add_edge(self, from_id: str, to_id: str) -> None:
        if from_id not in self.nodes or to_id not in self.nodes:
            raise ValueError("Both nodes must exist in the DAG before adding an edge.")
        if from_id == to_id:
            raise ValueError("Self-loops are not permitted in a DAG.")
        if self._has_path(to_id, from_id):
            raise ValueError(f"Adding {from_id} -> {to_id} would create a cycle.")
        if to_id not in self.edges[from_id]:
            self.edges[from_id].append(to_id)

    def _kl_divergence_stable(self, P_i: np.ndarray, P_j: np.ndarray) -> float:
        if P_i.shape != P_j.shape:
            raise ValueError("Probability vectors must have the same dimensionality.")
        p_i_safe = np.maximum(P_i, self.epsilon_min)
        p_j_safe = np.maximum(P_j, self.epsilon_min)
        return float(np.sum(P_i * np.log2(p_i_safe / p_j_safe)))

    def calculate_traversal_cost(self, node_i: SemanticBeliefNode, node_j: SemanticBeliefNode) -> float:
        kl_div = self._kl_divergence_stable(node_i.P, node_j.P)
        delta_h = node_i.H_S - node_j.H_S
        return max(0.0, (self.alpha * kl_div) + (self.beta * delta_h))

    def filter_flash_traversal(
        self,
        start_id: str,
        target_id: str,
        filter_threshold: float,
        flash_threshold: float,
    ) -> Optional[Dict[str, Any]]:
        if start_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("Start or target node does not exist in the DAG.")

        pq = [(0.0, start_id, [start_id], [])]
        best_cost: Dict[str, float] = {start_id: 0.0}

        while pq:
            current_cost, current_id, path, flashes = heapq.heappop(pq)
            if current_cost > best_cost.get(current_id, float("inf")):
                continue
            if current_id == target_id:
                return {"path": path, "total_cost": current_cost, "flash_events": flashes}

            current_node = self.nodes[current_id]
            for neighbor_id in self.edges.get(current_id, []):
                neighbor_node = self.nodes[neighbor_id]
                step_cost = self.calculate_traversal_cost(current_node, neighbor_node)
                if step_cost >= filter_threshold:
                    continue

                entropy_gradient = current_node.H_S - neighbor_node.H_S
                new_flashes = list(flashes)
                if entropy_gradient > flash_threshold:
                    new_flashes.append({
                        "transition": f"{current_id} -> {neighbor_id}",
                        "entropy_gradient": entropy_gradient,
                        "event_type": "SEMANTIC_DISAMBIGUATION",
                    })

                next_cost = current_cost + step_cost
                if next_cost < best_cost.get(neighbor_id, float("inf")):
                    best_cost[neighbor_id] = next_cost
                    heapq.heappush(pq, (next_cost, neighbor_id, path + [neighbor_id], new_flashes))

        return None
