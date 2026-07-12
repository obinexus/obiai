"""WebSocket event envelopes, validated as Pydantic discriminated unions.

Every message on the wire is ``{"type": "<name>", ...payload}``. Unknown or
malformed events fail validation and are answered with an ``error`` event —
they never crash the connection.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

from obiai.core.models import Decision, Observation, ObservationIn, SafetyAudit
from obiai.types import BiasReport

__all__ = [
    "AgentMessage",
    "AuditCreated",
    "ChatMessage",
    "ClarificationAnswer",
    "ClientEvent",
    "DecisionCreated",
    "ErrorEvent",
    "ObservationCreated",
    "ObservationSubmit",
    "ReasoningStarted",
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


ClientEvent = Annotated[
    Union[SessionStart, SessionEnd, ChatMessage, ObservationSubmit, ClarificationAnswer],
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


class AuditCreated(BaseModel):
    type: Literal["audit.created"] = "audit.created"
    decision_id: str
    bias_audit: BiasReport
    safety_audit: SafetyAudit


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: str = "invalid_event"


ServerEvent = Annotated[
    Union[
        SessionReady,
        ObservationCreated,
        ReasoningStarted,
        DecisionCreated,
        AgentMessage,
        AuditCreated,
        ErrorEvent,
    ],
    Field(discriminator="type"),
]

server_event_adapter: TypeAdapter[ServerEvent] = TypeAdapter(ServerEvent)
