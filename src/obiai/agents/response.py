"""Response generation: turns a Decision into what U says.

Kept separate from planning (which selects the action) and from transport
(which delivers the message) per the separation-of-concerns contract.
"""

from __future__ import annotations

from obiai.core.models import Decision

__all__ = ["GREETING", "render_agent_message"]

GREETING = "Hi, I am U."

_ACTION_MESSAGES: dict[str, str] = {
    "announce_hand_raise": "A participant appears to be requesting a turn to speak.",
    "ask_for_clarification": (
        "I am not certain yet. Could you confirm what you would like me to check?"
    ),
    "withhold_and_flag": (
        "I am withholding this conclusion because an audit did not pass; "
        "the trace has been flagged for review."
    ),
}


def render_agent_message(decision: Decision) -> str | None:
    """The utterance for a decision, or None when U should stay silent."""
    if decision.action is None:
        return None
    return _ACTION_MESSAGES.get(decision.action.name)
