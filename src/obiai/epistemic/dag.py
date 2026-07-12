"""Epistemological DAG with cost-weighted Filter-Flash traversal.

Implements the AEGIS-PROOF-1.2 specification:

    C(Node_i -> Node_j) = alpha * KL(P_i || P_j) + beta * DeltaH(S_i, S_j)

with alpha + beta = 1, alpha > 0, beta > 0 (Lemma 1), cost clamped
non-negative (Theorem 1), and numerically stable KL (Section 5.1).

Moved from the legacy module-level script ``obiai/EpistemicDAG.py``; the
original demo now lives under ``__main__`` so importing has no side effects.
"""

import heapq
from dataclasses import dataclass
from itertools import count
from typing import Any, Dict, List, Optional

import numpy as np


# --- Definition 1: Semantic Belief Node ---
@dataclass
class SemanticBeliefNode:
    """
    Represents a probabilistic state in the Epistemological DAG.
    """
    node_id: str
    P: np.ndarray          # Probability distribution over semantic interpretations
    H_S: float             # Entropy of the semantic context S_i

    @property
    def H_P(self) -> float:
        """Calculates the entropy of the probability distribution P_i."""
        # Safeguard against log(0)
        p_safe = np.clip(self.P, 1e-12, 1.0)
        return -np.sum(self.P * np.log2(p_safe))


class EpistemicDAG:
    """
    Core data structure implementing cost-weighted traversal for the Aegis Framework.
    Complies with AEGIS-PROOF-1.2 mathematical specifications.
    """

    def __init__(self, alpha: float = 0.5, beta: float = 0.5, epsilon_min: float = 1e-12):
        # Lemma 1: Parameter Boundedness Constraints
        if not np.isclose(alpha + beta, 1.0):
            raise ValueError("Normalization constraint violated: alpha + beta must equal 1.0")
        if alpha <= 0 or beta <= 0:
            raise ValueError("Non-degeneracy constraint violated: alpha, beta must be > 0")

        self.alpha = alpha
        self.beta = beta
        self.epsilon_min = epsilon_min  # Section 5.1: Numerical stability safeguard

        self.nodes: Dict[str, SemanticBeliefNode] = {}
        self.edges: Dict[str, List[str]] = {}  # Adjacency list for the DAG

    def add_node(self, node: SemanticBeliefNode):
        self.nodes[node.node_id] = node
        if node.node_id not in self.edges:
            self.edges[node.node_id] = []

    def add_edge(self, from_id: str, to_id: str):
        if from_id not in self.nodes or to_id not in self.nodes:
            raise ValueError("Both nodes must exist in the DAG before adding an edge.")
        if to_id in self.edges.get(from_id, []):
            return
        # Invariant: the graph must remain acyclic. Adding from->to creates a
        # cycle exactly when from is already reachable from to.
        if self._reachable(to_id, from_id):
            raise ValueError(f"Edge {from_id} -> {to_id} would create a cycle.")
        self.edges[from_id].append(to_id)

    def _reachable(self, source: str, target: str) -> bool:
        stack = [source]
        seen = set()
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(self.edges.get(node, []))
        return False

    # --- Section 5.1: Handling Singular Probability Distributions ---
    def _kl_divergence_stable(self, P_i: np.ndarray, P_j: np.ndarray) -> float:
        """
        Calculates KL(P_i || P_j) with numerical safeguards.
        KL_stable = sum( P_i * log2( P_i / max(P_j, epsilon_min) ) )
        """
        P_j_safe = np.maximum(P_j, self.epsilon_min)
        # Avoid log(0) for P_i as well
        P_i_safe = np.maximum(P_i, self.epsilon_min)
        return np.sum(P_i * np.log2(P_i_safe / P_j_safe))

    # --- Definition 2 & Theorem 1: Traversal Cost Function ---
    def calculate_traversal_cost(self, node_i: SemanticBeliefNode, node_j: SemanticBeliefNode) -> float:
        """
        C(Node_i -> Node_j) = alpha * KL(P_i || P_j) + beta * Delta_H(S_i,j)
        Enforces Theorem 1 (Non-negativity).
        """
        kl_div = self._kl_divergence_stable(node_i.P, node_j.P)

        # Delta H(S_i,j) = H(S_i) - H(S_j)
        delta_H = node_i.H_S - node_j.H_S

        # Calculate total cost
        cost = (self.alpha * kl_div) + (self.beta * delta_H)

        # Theorem 1 Part 1 & 3: Enforce Non-negativity
        return max(0.0, cost)

    # --- Algorithm 1: Filter-Flash Integrated Traversal ---
    def filter_flash_traversal(self, start_id: str, target_id: str,
                               filter_threshold: float, flash_threshold: float) -> Optional[Dict[str, Any]]:
        """
        Finds the optimal traversal path using Dijkstra's algorithm,
        integrating semantic filtering and consciousness-aware flash events.
        """
        if start_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("Start or target node does not exist in the DAG.")

        # Priority Queue: (cumulative_cost, tiebreak, current_node_id, path_history, flash_events_log)
        # The monotonically increasing tiebreak keeps heapq from ever comparing
        # path/flash payloads when costs are equal.
        tiebreak = count()
        pq = [(0.0, next(tiebreak), start_id, [start_id], [])]
        visited = set()

        while pq:
            current_cost, _, current_id, path, flashes = heapq.heappop(pq)

            # Goal reached
            if current_id == target_id:
                return {
                    "path": path,
                    "total_cost": current_cost,
                    "flash_events": flashes
                }

            if current_id in visited:
                continue
            visited.add(current_id)

            current_node = self.nodes[current_id]
            neighbors = self.edges.get(current_id, [])

            for neighbor_id in neighbors:
                if neighbor_id in visited:
                    continue

                neighbor_node = self.nodes[neighbor_id]
                cost_i_j = self.calculate_traversal_cost(current_node, neighbor_node)

                # --- Semantic Filter Condition ---
                if cost_i_j >= filter_threshold:
                    # If cost exceeds threshold, the semantic filter rejects this transition
                    continue

                # --- Flash Event Condition ---
                entropy_gradient = current_node.H_S - neighbor_node.H_S  # Delta H
                new_flashes = list(flashes)

                if entropy_gradient > flash_threshold:
                    new_flashes.append({
                        "transition": f"{current_id} -> {neighbor_id}",
                        "entropy_gradient": entropy_gradient,
                        "event_type": "SEMANTIC_DISAMBIGUATION"
                    })

                # Push to priority queue
                heapq.heappush(pq, (
                    current_cost + cost_i_j,
                    next(tiebreak),
                    neighbor_id,
                    path + [neighbor_id],
                    new_flashes
                ))

        return None  # No valid path found within filter constraints


def _demo() -> None:
    """The original AEGIS example (previously ran at import time)."""
    # 1. Initialize the DAG (Alpha and Beta must sum to 1.0)
    aegis_brain = EpistemicDAG(alpha=0.6, beta=0.4)

    # 2. Create Semantic Belief Nodes (Simulating Robot Sensor States)
    node_a = SemanticBeliefNode(node_id="State_A", P=np.array([0.5, 0.5]), H_S=2.0)
    node_b = SemanticBeliefNode(node_id="State_B", P=np.array([0.8, 0.2]), H_S=1.0)
    node_c = SemanticBeliefNode(node_id="State_C", P=np.array([1.0, 0.0]), H_S=0.0)

    # 3. Build the DAG
    aegis_brain.add_node(node_a)
    aegis_brain.add_node(node_b)
    aegis_brain.add_node(node_c)
    aegis_brain.add_edge("State_A", "State_B")
    aegis_brain.add_edge("State_B", "State_C")
    aegis_brain.add_edge("State_A", "State_C")  # Direct jump

    # 4. Run Algorithm 1 (Filter-Flash Traversal)
    result = aegis_brain.filter_flash_traversal(
        start_id="State_A",
        target_id="State_C",
        filter_threshold=1.5,
        flash_threshold=0.5,
    )

    print("--- AEGIS TRAVERSAL RESULT ---")
    if result:
        print(f"Optimal Path: {' -> '.join(result['path'])}")
        print(f"Total Traversal Cost: {result['total_cost']:.4f}")
        print(f"Flash Events Triggered: {len(result['flash_events'])}")
        for event in result['flash_events']:
            print(f"  -> {event['transition']} | Gradient: {event['entropy_gradient']:.2f}")
    else:
        print("No valid path found within the semantic filter constraints.")


if __name__ == "__main__":
    _demo()
