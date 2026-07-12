"""Builds the semantic belief DAG for a reasoning pass and runs traversal.

For the vertical slice the DAG is a three-stage semantic chain:

    <observation concept>  ->  <intermediate concept>  ->  <decision concept>

The observation node carries the raw classifier belief, the intermediate node
carries the phi-marginalized posterior, and the decision node carries a
near-certain committed belief. Filter-Flash traversal then yields the
semantic path and any SEMANTIC_DISAMBIGUATION flash events, which the engine
surfaces in the decision explanation.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field

from obiai.core.config import EpistemicSettings
from obiai.epistemic.dag import EpistemicDAG, SemanticBeliefNode

__all__ = ["FlashEvent", "SemanticPathResult", "build_semantic_dag", "traverse_semantic_path"]

DECISION_BELIEF = 0.99
OBSERVATION_ENTROPY = 1.0
INTERMEDIATE_ENTROPY = 0.5
DECISION_ENTROPY = 0.1


class FlashEvent(BaseModel):
    transition: str
    entropy_gradient: float
    event_type: str = "SEMANTIC_DISAMBIGUATION"


class SemanticPathResult(BaseModel):
    path: list[str] = Field(default_factory=list)
    total_cost: float = Field(ge=0.0)
    flash_events: list[FlashEvent] = Field(default_factory=list)


def build_semantic_dag(
    posterior: float,
    settings: EpistemicSettings,
    *,
    source: str,
    intermediate: str,
    target: str,
    source_belief: float = 0.85,
) -> EpistemicDAG:
    dag = EpistemicDAG(alpha=settings.alpha, beta=settings.beta)
    dag.add_node(
        SemanticBeliefNode(source, P=np.array([source_belief, 1.0 - source_belief]),
                           H_S=OBSERVATION_ENTROPY)
    )
    dag.add_node(
        SemanticBeliefNode(intermediate, P=np.array([posterior, 1.0 - posterior]),
                           H_S=INTERMEDIATE_ENTROPY)
    )
    dag.add_node(
        SemanticBeliefNode(target, P=np.array([DECISION_BELIEF, 1.0 - DECISION_BELIEF]),
                           H_S=DECISION_ENTROPY)
    )
    dag.add_edge(source, intermediate)
    dag.add_edge(intermediate, target)
    return dag


def traverse_semantic_path(
    dag: EpistemicDAG,
    start: str,
    target: str,
    settings: EpistemicSettings,
) -> SemanticPathResult | None:
    raw = dag.filter_flash_traversal(
        start_id=start,
        target_id=target,
        filter_threshold=settings.filter_threshold,
        flash_threshold=settings.flash_threshold,
    )
    if raw is None:
        return None
    return SemanticPathResult(
        path=raw["path"],
        total_cost=raw["total_cost"],
        flash_events=[FlashEvent(**event) for event in raw["flash_events"]],
    )
