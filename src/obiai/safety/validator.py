"""Safety auditing: observable-events-only enforcement.

U must never infer protected or internal traits (medical status, disability,
ethnicity, emotion, identity, honesty, ...) from media. This is enforced
structurally:

* only allowlisted observable event types are accepted at all;
* mapped concepts and propositions must not fall in a forbidden inference
  category (checked by category prefix, e.g. ``medical.diagnosis``);
* observation values are scalar-only with a hard text cap (enforced in the
  :class:`~obiai.core.models.Observation` model), so raw frames or audio can
  never enter the pipeline disguised as an event.
"""

from __future__ import annotations

from typing import Iterable

from obiai.core.models import MappedEvidence, Observation, SafetyAudit

__all__ = ["SafetyAuditor"]


class SafetyAuditor:
    def __init__(
        self,
        allowed_event_types: Iterable[str],
        forbidden_categories: Iterable[str],
    ) -> None:
        self.allowed_event_types = frozenset(allowed_event_types)
        self.forbidden_categories = frozenset(forbidden_categories)

    def is_event_type_allowed(self, event_type: str) -> bool:
        return event_type in self.allowed_event_types

    def audit(self, observation: Observation, mapping: MappedEvidence) -> SafetyAudit:
        flags: list[str] = []
        if not self.is_event_type_allowed(observation.event_type):
            flags.append(f"event_type_not_allowed:{observation.event_type}")
        for concept in [*mapping.concepts, mapping.proposition]:
            category = concept.split(".", 1)[0]
            if category in self.forbidden_categories:
                flags.append(f"forbidden_inference_category:{concept}")
        return SafetyAudit(passed=not flags, policy_flags=flags)
