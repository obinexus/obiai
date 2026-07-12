"""Backward-compatible shim: the implementation moved to obiai.epistemic.dag.

Run ``python -m obiai.epistemic.dag`` for the original AEGIS demo.
"""

from obiai.epistemic.dag import EpistemicDAG, SemanticBeliefNode  # noqa: F401

__all__ = ["EpistemicDAG", "SemanticBeliefNode"]
