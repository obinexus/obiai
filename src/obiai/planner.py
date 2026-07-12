from __future__ import annotations

from .types import Action


class Planner:
    """Deterministic starter planner; replace with search or an LLM adapter later."""

    def plan(self, proposition: str, probability: float, uncertainty: float) -> list[Action]:
        if uncertainty > 0.35:
            return [Action(
                name="gather_evidence",
                parameters={"proposition": proposition},
                rationale="Posterior uncertainty is above the permitted threshold.",
            )]
        if probability >= 0.60:
            return [Action(
                name="proceed",
                parameters={"proposition": proposition},
                rationale="Evidence supports the proposition above the decision threshold.",
            )]
        return [Action(
            name="withhold",
            parameters={"proposition": proposition},
            rationale="Evidence is insufficient for a positive decision.",
        )]
