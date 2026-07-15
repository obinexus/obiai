"""UService: session-scoped application logic shared by REST and WebSocket.

The service owns the order of events for one observation:

    observation.created -> reasoning.started -> decision.created
    -> audit.created -> agent.message (when U has something to say)

Transport layers (routes, WS handler) call the service and never talk to the
engine, repository, or bus directly.
"""

from __future__ import annotations

from obiai.agents import GREETING, UReasoningEngine, render_agent_message
from obiai.core.config import Settings
from obiai.core.errors import (
    DisallowedEventTypeError,
    NoObservationsError,
    SessionNotFoundError,
)
from obiai.core.models import (
    Decision,
    Observation,
    ObservationIn,
    TranscriptEntry,
    TranscriptSegment,
)
from obiai.knowledge import UAgenticModel
from obiai.memory import Session, SessionRepository
from obiai.realtime import SessionEventBus
from obiai.realtime.events import (
    AgentMessage,
    AuditCreated,
    DecisionCreated,
    ObservationCreated,
    ReasoningStarted,
    ServerTranscriptFinal,
    ServerTranscriptPartial,
)

__all__ = ["UService"]


class UService:
    def __init__(
        self,
        repo: SessionRepository,
        bus: SessionEventBus,
        engine: UReasoningEngine,
        settings: Settings,
        u_model: UAgenticModel,
    ) -> None:
        self.repo = repo
        self.bus = bus
        self.engine = engine
        self.settings = settings
        self.u_model = u_model

    # --- Sessions -----------------------------------------------------------

    def create_session(self) -> Session:
        return self.repo.create()

    def get_session(self, session_id: str) -> Session:
        session = self.repo.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def delete_session(self, session_id: str) -> None:
        if not self.repo.delete(session_id):
            raise SessionNotFoundError(session_id)
        self.bus.drop_session(session_id)

    # --- Pipeline entry points ----------------------------------------------

    async def greet(self, session_id: str) -> None:
        self.get_session(session_id)
        self.repo.append_transcript(session_id, TranscriptEntry(role="u", text=GREETING))
        await self.bus.publish(session_id, AgentMessage(text=GREETING))

    async def handle_observation(
        self, session_id: str, observation_in: ObservationIn
    ) -> tuple[Observation, Decision]:
        self.get_session(session_id)
        if not self.engine.safety_auditor.is_event_type_allowed(observation_in.event_type):
            raise DisallowedEventTypeError(observation_in.event_type)

        observation = observation_in.to_observation(session_id)
        self.repo.add_observation(session_id, observation)
        await self.bus.publish(session_id, ObservationCreated(observation=observation))
        await self.bus.publish(
            session_id, ReasoningStarted(observation_id=observation.observation_id)
        )

        decision = self.engine.reason(session_id, observation)
        self.repo.add_decision(session_id, decision)
        await self.bus.publish(session_id, DecisionCreated(decision=decision))
        await self.bus.publish(
            session_id,
            AuditCreated(
                decision_id=decision.decision_id,
                bias_audit=decision.bias_audit,
                safety_audit=decision.safety_audit,
            ),
        )

        message = render_agent_message(decision)
        if message is not None:
            self.repo.append_transcript(session_id, TranscriptEntry(role="u", text=message))
            await self.bus.publish(session_id, AgentMessage(text=message))
        return observation, decision

    async def handle_chat(self, session_id: str, text: str) -> str:
        """Typed chat: the client already shows the user's own message locally."""
        self.get_session(session_id)
        self.repo.append_transcript(session_id, TranscriptEntry(role="user", text=text))
        return await self._respond(session_id, text)

    async def handle_partial_transcript(
        self, session_id: str, segment: TranscriptSegment
    ) -> None:
        """Interim speech recognition result: rebroadcast only, never persisted."""
        self.get_session(session_id)
        await self.bus.publish(session_id, ServerTranscriptPartial(segment=segment))

    async def handle_voice_transcript(
        self, session_id: str, segment: TranscriptSegment
    ) -> str:
        """A finalized spoken utterance: persisted and treated as a chat turn.

        Unlike typed chat, the client has not shown the user's own words yet
        (recognition happens after the fact), so the finalized segment is
        echoed back before U's reply.
        """
        self.get_session(session_id)
        self.repo.append_transcript(session_id, TranscriptEntry(role="user", text=segment.text))
        await self.bus.publish(session_id, ServerTranscriptFinal(segment=segment))
        return await self._respond(session_id, segment.text)

    async def _respond(self, session_id: str, prompt: str) -> str:
        reply = self.u_model.answer(prompt)
        self.repo.append_transcript(session_id, TranscriptEntry(role="u", text=reply))
        await self.bus.publish(session_id, AgentMessage(text=reply))
        return reply

    def rereason_latest(self, session_id: str) -> Decision:
        """Re-run reasoning over the most recent stored observation."""
        session = self.get_session(session_id)
        if not session.observations:
            raise NoObservationsError(session_id)
        decision = self.engine.reason(session_id, session.observations[-1])
        self.repo.add_decision(session_id, decision)
        return decision
