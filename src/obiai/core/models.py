"""Core data contracts for the U pipeline.

These extend the legacy models in :mod:`obiai.types` (which remain untouched
for the original ``OBIAgent`` path) with session-scoped, auditable objects:
every stage of the pipeline consumes and produces these models, so a Decision
can always be traced back to the Observation that caused it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from obiai.types import Action, BiasReport, TruthState

__all__ = [
    "Action",
    "BiasReport",
    "Decision",
    "Evidence",
    "MappedEvidence",
    "Observation",
    "ObservationIn",
    "Provenance",
    "SafetyAudit",
    "TranscriptEntry",
    "TranscriptSegment",
    "TruthState",
]

MAX_SCALAR_TEXT = 256


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Provenance(BaseModel):
    module: str
    version: str


class Observation(BaseModel):
    """A normalized, structured event from a media or chat source.

    Values are scalars only; string payloads are hard-capped so raw media
    (frames, audio) can never ride in through this model.
    """

    observation_id: str = Field(default_factory=lambda: new_id("obs"))
    session_id: str
    modality: Literal["vision", "chat", "system"]
    event_type: str
    value: bool | int | float | str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    timestamp: datetime = Field(default_factory=utcnow)

    @field_validator("value")
    @classmethod
    def _reject_oversized_text(cls, value: bool | int | float | str) -> bool | int | float | str:
        if isinstance(value, str) and len(value) > MAX_SCALAR_TEXT:
            raise ValueError(
                f"observation value must be a short scalar (<= {MAX_SCALAR_TEXT} chars); "
                "raw media payloads are not accepted"
            )
        return value


class ObservationIn(BaseModel):
    """Client-submitted observation (session_id and ids are assigned server-side)."""

    modality: Literal["vision", "chat", "system"]
    event_type: str
    value: bool | int | float | str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str

    @field_validator("value")
    @classmethod
    def _reject_oversized_text(cls, value: bool | int | float | str) -> bool | int | float | str:
        if isinstance(value, str) and len(value) > MAX_SCALAR_TEXT:
            raise ValueError(
                f"observation value must be a short scalar (<= {MAX_SCALAR_TEXT} chars); "
                "raw media payloads are not accepted"
            )
        return value

    def to_observation(self, session_id: str) -> Observation:
        return Observation(
            session_id=session_id,
            modality=self.modality,
            event_type=self.event_type,
            value=self.value,
            confidence=self.confidence,
            source=self.source,
        )


class Evidence(BaseModel):
    """Evidence for a proposition, traceable to its source observation."""

    evidence_id: str = Field(default_factory=lambda: new_id("evidence"))
    proposition: str
    value: bool
    confidence: float = Field(ge=0.0, le=1.0)
    source_observation_id: str | None = None
    provenance: Provenance


class MappedEvidence(BaseModel):
    """Output of the ontology mapper: an observation grounded in the belief network."""

    bn_variable: str
    proposition: str
    concepts: list[str] = Field(default_factory=list)
    semantic_chain: list[str] = Field(default_factory=list)
    evidence: Evidence


class SafetyAudit(BaseModel):
    passed: bool = True
    policy_flags: list[str] = Field(default_factory=list)


class Decision(BaseModel):
    """A fully auditable decision produced by the U reasoning pipeline."""

    decision_id: str = Field(default_factory=lambda: new_id("decision"))
    session_id: str
    proposition: str
    probability: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    state: TruthState
    evidence: list[Evidence] = Field(default_factory=list)
    ontological_concepts: list[str] = Field(default_factory=list)
    semantic_path: list[str] = Field(default_factory=list)
    bias_audit: BiasReport = Field(default_factory=BiasReport)
    safety_audit: SafetyAudit = Field(default_factory=SafetyAudit)
    action: Action | None = None
    explanation: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class TranscriptEntry(BaseModel):
    role: Literal["user", "u"]
    text: str
    timestamp: datetime = Field(default_factory=utcnow)


class TranscriptSegment(BaseModel):
    """A segment of live speech transcription.

    Recognition runs client-side (browser Web Speech API in the current
    implementation); only recognized text crosses the wire, never audio. A
    server-side :class:`~obiai.core.protocols.SpeechToTextProvider` that
    accepts raw audio remains a deferred provider for a future backend
    transcription path.
    """

    text: str = Field(max_length=4000)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    final: bool = True
