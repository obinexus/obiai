"""Action selection for U.

Hard rules, in priority order:

1. failed safety or bias audit -> ``withhold_and_flag`` (never act on
   unaudited beliefs);
2. MAYBE -> ``ask_for_clarification`` (a MAYBE state must never trigger a
   high-impact action);
3. YES -> the registered high-impact action for the proposition;
4. NO -> ``withhold``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from obiai.core.models import Action, BiasReport, SafetyAudit, TruthState

__all__ = ["ActionSpec", "HIGH_IMPACT_ACTIONS", "UPlanner"]

HIGH_IMPACT_ACTIONS = frozenset({"announce_hand_raise", "proceed"})


class ActionSpec(BaseModel):
    name: str
    parameters: dict[str, object] = Field(default_factory=dict)
    rationale: str


_DEFAULT_YES_ACTIONS: dict[str, ActionSpec] = {
    "participant_requests_turn": ActionSpec(
        name="announce_hand_raise",
        rationale="The observed hand-raise event has high posterior support.",
    ),
}


class UPlanner:
    def __init__(self, yes_actions: dict[str, ActionSpec] | None = None) -> None:
        self.yes_actions = dict(_DEFAULT_YES_ACTIONS if yes_actions is None else yes_actions)

    def plan(
        self,
        state: TruthState,
        proposition: str,
        probability: float,
        uncertainty: float,
        bias: BiasReport,
        safety: SafetyAudit,
    ) -> Action:
        if not safety.passed or not bias.passed:
            failed = [
                name
                for name, audit_passed in (("safety", safety.passed), ("bias", bias.passed))
                if not audit_passed
            ]
            return Action(
                name="withhold_and_flag",
                parameters={"failed_audits": failed},
                rationale="An audit failed; the decision is withheld and flagged for review.",
            )
        if state is TruthState.MAYBE:
            return Action(
                name="ask_for_clarification",
                parameters={"proposition": proposition},
                rationale=(
                    f"Posterior {probability:.4f} with uncertainty {uncertainty:.4f} is "
                    "inconclusive; asking instead of acting."
                ),
            )
        if state is TruthState.YES:
            spec = self.yes_actions.get(proposition)
            if spec is None:
                return Action(
                    name="report_belief",
                    parameters={"proposition": proposition},
                    rationale="No high-impact action is registered for this proposition.",
                )
            return Action(name=spec.name, parameters=dict(spec.parameters), rationale=spec.rationale)
        return Action(
            name="withhold",
            parameters={"proposition": proposition},
            rationale=f"Posterior {probability:.4f} is below the negative threshold.",
        )
