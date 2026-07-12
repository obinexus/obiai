"""Maps normalized observations onto ontological concepts and network variables.

The mapper is the single place where a raw ``event_type`` string acquires
meaning: which belief-network variable it toggles, which proposition it
supports, and which ontology concepts describe it. Downstream stages never
interpret event types themselves.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from obiai.core.errors import UnknownEventTypeError
from obiai.core.models import Evidence, MappedEvidence, Observation, Provenance

__all__ = ["EventMapping", "EventOntologyMapper", "HAND_RAISE_MAPPING"]

MAPPER_VERSION = "0.2.0"


class EventMapping(BaseModel):
    event_type: str
    bn_variable: str
    proposition: str
    concepts: list[str] = Field(default_factory=list)
    provenance_module: str
    # Three-stage semantic chain traversed in the epistemic DAG:
    # observation concept -> intermediate concept -> decision concept.
    semantic_chain: list[str] = Field(min_length=3, max_length=3)


HAND_RAISE_MAPPING = EventMapping(
    event_type="participant_raised_hand",
    bn_variable="participant_raised_hand",
    proposition="participant_requests_turn",
    concepts=["vision.hand_raise", "communication.request_turn"],
    provenance_module="vision.hand_raise",
    semantic_chain=[
        "observation.hand_raised",
        "communication.request_turn",
        "decision.announce_hand_raise",
    ],
)


class EventOntologyMapper:
    """Registry-backed observation-to-concept mapper."""

    def __init__(self, mappings: list[EventMapping] | None = None) -> None:
        entries = mappings if mappings is not None else [HAND_RAISE_MAPPING]
        self._registry: dict[str, EventMapping] = {m.event_type: m for m in entries}

    @property
    def known_event_types(self) -> list[str]:
        return sorted(self._registry)

    def register(self, mapping: EventMapping) -> None:
        self._registry[mapping.event_type] = mapping

    def map(self, observation: Observation) -> MappedEvidence:
        mapping = self._registry.get(observation.event_type)
        if mapping is None:
            raise UnknownEventTypeError(observation.event_type)
        evidence = Evidence(
            proposition=mapping.proposition,
            value=bool(observation.value),
            confidence=observation.confidence,
            source_observation_id=observation.observation_id,
            provenance=Provenance(module=mapping.provenance_module, version=MAPPER_VERSION),
        )
        return MappedEvidence(
            bn_variable=mapping.bn_variable,
            proposition=mapping.proposition,
            concepts=list(mapping.concepts),
            semantic_chain=list(mapping.semantic_chain),
            evidence=evidence,
        )
