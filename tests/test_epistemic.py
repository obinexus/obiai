import subprocess
import sys

import numpy as np
import pytest

from obiai.core.config import EpistemicSettings
from obiai.epistemic import (
    EpistemicDAG,
    SemanticBeliefNode,
    build_semantic_dag,
    traverse_semantic_path,
)

POSTERIOR = 943 / 1010  # raised-hand posterior from tests/test_marginal.py
SOURCE = "observation.hand_raised"
INTERMEDIATE = "communication.request_turn"
TARGET = "decision.announce_hand_raise"


@pytest.fixture()
def settings() -> EpistemicSettings:
    return EpistemicSettings()  # alpha 0.6, beta 0.4, filter 2.0, flash 0.25


def _hand_raise_dag(settings: EpistemicSettings) -> EpistemicDAG:
    return build_semantic_dag(
        POSTERIOR, settings, source=SOURCE, intermediate=INTERMEDIATE, target=TARGET
    )


def test_semantic_path_for_hand_raise(settings: EpistemicSettings) -> None:
    dag = _hand_raise_dag(settings)
    result = traverse_semantic_path(dag, SOURCE, TARGET, settings)
    assert result is not None
    assert result.path == [SOURCE, INTERMEDIATE, TARGET]
    assert result.total_cost >= 0.0


def test_two_flash_events_for_hand_raise(settings: EpistemicSettings) -> None:
    dag = _hand_raise_dag(settings)
    result = traverse_semantic_path(dag, SOURCE, TARGET, settings)
    assert result is not None
    assert len(result.flash_events) == 2
    assert all(e.event_type == "SEMANTIC_DISAMBIGUATION" for e in result.flash_events)
    assert result.flash_events[0].entropy_gradient == pytest.approx(0.5)
    assert result.flash_events[1].entropy_gradient == pytest.approx(0.4)


def test_filter_rejects_expensive_transitions(settings: EpistemicSettings) -> None:
    tight = EpistemicSettings(filter_threshold=0.1, flash_threshold=0.25)
    dag = _hand_raise_dag(tight)
    assert traverse_semantic_path(dag, SOURCE, TARGET, tight) is None


def test_alpha_beta_normalization_enforced() -> None:
    with pytest.raises(ValueError, match="alpha \\+ beta"):
        EpistemicDAG(alpha=0.7, beta=0.4)
    with pytest.raises(ValueError, match="Non-degeneracy"):
        EpistemicDAG(alpha=1.0, beta=0.0)


def test_cost_non_negative_even_when_entropy_rises() -> None:
    dag = EpistemicDAG(alpha=0.5, beta=0.5)
    low = SemanticBeliefNode("low", P=np.array([0.5, 0.5]), H_S=0.0)
    high = SemanticBeliefNode("high", P=np.array([0.5, 0.5]), H_S=5.0)
    # KL is 0 (identical distributions) and DeltaH is -5: raw cost would be
    # negative, Theorem 1 clamps it.
    assert dag.calculate_traversal_cost(low, high) == 0.0


def test_cycle_rejected() -> None:
    dag = EpistemicDAG()
    for node_id in ("a", "b", "c"):
        dag.add_node(SemanticBeliefNode(node_id, P=np.array([0.5, 0.5]), H_S=1.0))
    dag.add_edge("a", "b")
    dag.add_edge("b", "c")
    with pytest.raises(ValueError, match="cycle"):
        dag.add_edge("c", "a")


def test_legacy_import_is_silent_and_compatible() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", "import obiai.EpistemicDAG as m; assert m.EpistemicDAG"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout == ""
