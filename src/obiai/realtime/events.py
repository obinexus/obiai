"""WebSocket event envelopes, validated as Pydantic discriminated unions.

Every message on the wire is ``{"type": "<name>", ...payload}``. Unknown or
malformed events fail validation and are answered with an ``error`` event —
they never crash the connection.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

from obiai.core.models import (
    Decision,
    Observation,
    ObservationIn,
    SafetyAudit,
    TranscriptSegment,
)
from obiai.types import BiasReport

__all__ = [
    "AgentMessage",
    "AuditCreated",
    "ChatMessage",
    "ClarificationAnswer",
    "ClientEvent",
    "ClientTranscriptFinal",
    "ClientTranscriptPartial",
    "DecisionCreated",
    "ErrorEvent",
    "ObservationCreated",
    "ObservationSubmit",
    "ReasoningStarted",
    "ServerTranscriptFinal",
    "ServerTranscriptPartial",
    "SessionEnd",
    "SessionReady",
    "SessionStart",
    "client_event_adapter",
    "server_event_adapter",
]


# --- Client -> server -------------------------------------------------------


class SessionStart(BaseModel):
    type: Literal["session.start"] = "session.start"


class SessionEnd(BaseModel):
    type: Literal["session.end"] = "session.end"


class ChatMessage(BaseModel):
    type: Literal["chat.message"] = "chat.message"
    text: str = Field(min_length=1, max_length=4000)


class ObservationSubmit(BaseModel):
    type: Literal["observation.submit"] = "observation.submit"
    observation: ObservationIn


class ClarificationAnswer(BaseModel):
    type: Literal["clarification.answer"] = "clarification.answer"
    decision_id: str
    answer: str = Field(min_length=1, max_length=4000)


class ClientTranscriptPartial(BaseModel):
    """An interim (not-yet-final) speech recognition result.

    Never persisted — purely for live captioning. Recognition runs entirely
    in the browser (Web Speech API); only recognized text crosses the wire,
    never audio.
    """

    type: Literal["transcript.partial"] = "transcript.partial"
    segment: TranscriptSegment


class ClientTranscriptFinal(BaseModel):
    """A finalized utterance, treated as a spoken chat message."""

    type: Literal["transcript.final"] = "transcript.final"
    segment: TranscriptSegment


ClientEvent = Annotated[
    Union[
        SessionStart,
        SessionEnd,
        ChatMessage,
        ObservationSubmit,
        ClarificationAnswer,
        ClientTranscriptPartial,
        ClientTranscriptFinal,
    ],
    Field(discriminator="type"),
]

client_event_adapter: TypeAdapter[ClientEvent] = TypeAdapter(ClientEvent)


# --- Server -> client -------------------------------------------------------


class SessionReady(BaseModel):
    type: Literal["session.ready"] = "session.ready"
    session_id: str


class ObservationCreated(BaseModel):
    type: Literal["observation.created"] = "observation.created"
    observation: Observation


class ReasoningStarted(BaseModel):
    type: Literal["reasoning.started"] = "reasoning.started"
    observation_id: str


class DecisionCreated(BaseModel):
    type: Literal["decision.created"] = "decision.created"
    decision: Decision


class AgentMessage(BaseModel):
    type: Literal["agent.message"] = "agent.message"
    text: str
    # Provenance: which layer actually produced ``text``. Never
    # "trained_uai" unless adapter_loaded is also true -- see
    # obiai.knowledge.transcript.UAIResponse.
    response_source: str = "seeded_uagentic"
    adapter_loaded: bool = False
    model_run_id: str | None = None


class AuditCreated(BaseModel):
    type: Literal["audit.created"] = "audit.created"
    decision_id: str
    bias_audit: BiasReport
    safety_audit: SafetyAudit


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: str = "invalid_event"


class ServerTranscriptPartial(BaseModel):
    """Live-caption echo of an interim recognition result."""

    type: Literal["transcript.partial"] = "transcript.partial"
    segment: TranscriptSegment


class ServerTranscriptFinal(BaseModel):
    """The finalized utterance, for rendering the user's spoken turn in the transcript."""

    type: Literal["transcript.final"] = "transcript.final"
    segment: TranscriptSegment


ServerEvent = Annotated[
    Union[
        SessionReady,
        ObservationCreated,
        ReasoningStarted,
        DecisionCreated,
        AgentMessage,
        AuditCreated,
        ServerTranscriptPartial,
        ServerTranscriptFinal,
        ErrorEvent,
    ],
    Field(discriminator="type"),
]

server_event_adapter: TypeAdapter[ServerEvent] = TypeAdapter(ServerEvent)
