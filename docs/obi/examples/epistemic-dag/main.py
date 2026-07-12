import numpy as np

from EpistemicDAG import EpistemicDAG, SemanticBeliefNode


def build_demo_dag() -> EpistemicDAG:
    aegis_brain = EpistemicDAG(alpha=0.6, beta=0.4)

    node_a = SemanticBeliefNode("State_A", np.array([0.5, 0.5]), H_S=2.0)
    node_b = SemanticBeliefNode("State_B", np.array([0.8, 0.2]), H_S=1.0)
    node_c = SemanticBeliefNode("State_C", np.array([1.0, 0.0]), H_S=0.0)

    for node in (node_a, node_b, node_c):
        aegis_brain.add_node(node)

    aegis_brain.add_edge("State_A", "State_B")
    aegis_brain.add_edge("State_B", "State_C")
    aegis_brain.add_edge("State_A", "State_C")
    return aegis_brain


if __name__ == "__main__":
    aegis_brain = build_demo_dag()

    for from_id, to_id in [("State_A", "State_B"), ("State_B", "State_C"), ("State_A", "State_C")]:
        cost = aegis_brain.calculate_traversal_cost(aegis_brain.nodes[from_id], aegis_brain.nodes[to_id])
        print(f"Cost {from_id} -> {to_id}: {cost:.4f}")

    result = aegis_brain.filter_flash_traversal(
        start_id="State_A",
        target_id="State_C",
        filter_threshold=5.0,
        flash_threshold=0.5,
    )

    print("--- AEGIS TRAVERSAL RESULT ---")
    if result:
        print(f"Optimal Path: {' -> '.join(result['path'])}")
        print(f"Total Traversal Cost: {result['total_cost']:.4f}")
        print(f"Flash Events Triggered: {len(result['flash_events'])}")
        for event in result["flash_events"]:
            print(f"  -> {event['transition']} | Gradient: {event['entropy_gradient']:.2f}")
    else:
        print("No valid path found within the semantic filter constraints.")
