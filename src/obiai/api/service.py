"""UService: session-scoped application logic shared by REST and WebSocket.

The service owns the order of events for one observation:

    observation.created -> reasoning.started -> decision.created
    -> audit.created -> agent.message (when U has something to say)

Transport layers (routes, WS handler) call the service and never talk to the
engine, repository, or bus directly.
"""

from __future__ import annotations

import re

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
from obiai.knowledge import UAgenticModel, answer_transcript
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
from obiai.training.runtime import UAIModelManager

__all__ = ["UService"]

_HAND_RAISE_PATTERN = re.compile(
    r"\b("
    r"participant_raised_hand|"
    r"raised[-_\s]?hand|"
    r"raises?\s+(?:their\s+|the\s+|a\s+)?hand|"
    r"hand\s+(?:is\s+|was\s+)?raised"
    r")\b",
    re.IGNORECASE,
)
_HAND_LOWERED_PATTERN = re.compile(
    r"\b("
    r"not\s+raised|"
    r"no\s+hand\s+raise|"
    r"lowers?\s+(?:their\s+|the\s+|a\s+)?hand|"
    r"lowered\s+(?:their\s+|the\s+|a\s+)?hand"
    r")\b",
    re.IGNORECASE,
)
_CONFIDENCE_PATTERNS = (
    re.compile(
        r"\bconfidence(?:\s+of|\s*[:=]|\s+)?\s*(?P<number>\d+(?:\.\d+)?)\s*(?P<percent>%)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<number>\d+(?:\.\d+)?)\s*(?P<percent>%)?\s*(?:confidence|confident)\b",
        re.IGNORECASE,
    ),
)


class UService:
    def __init__(
        self,
        repo: SessionRepository,
        bus: SessionEventBus,
        engine: UReasoningEngine,
        settings: Settings,
        u_model: UAgenticModel,
        uai_models: UAIModelManager | None = None,
    ) -> None:
        self.repo = repo
        self.bus = bus
        self.engine = engine
        self.settings = settings
        self.u_model = u_model
        self.uai_models = uai_models

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
        await self._emit_reply(
            session_id, GREETING, response_source="static_greeting", adapter_loaded=False
        )

    async def handle_observation(
        self, session_id: str, observation_in: ObservationIn
    ) -> tuple[Observation, Decision]:
        self.get_session(session_id)
        return await self._run_observation_pipeline(
            session_id, observation_in, publish_default_message=True
        )

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
        return await self._respond(session_id, segment.text, confidence=segment.confidence)

    async def _respond(
        self, session_id: str, prompt: str, *, confidence: float | None = None
    ) -> str:
        parsed_observation = self._observation_from_chat(prompt)
        if parsed_observation is not None:
            observation, decision = await self._run_observation_pipeline(
                session_id, parsed_observation, publish_default_message=False
            )
            reply = self._render_decision_trace(observation, decision)
            await self._emit_reply(
                session_id, reply, response_source="governance_pipeline", adapter_loaded=False
            )
            return reply

        # Not a governed observation: normalize (OBIAI/OBINexus terminology,
        # punctuation/casing) and answer through the trained model when one
        # is loaded, falling back to the seeded router only when it is not
        # -- see obiai.knowledge.transcript for the confidence gate.
        result = answer_transcript(
            prompt,
            confidence=confidence,
            generate=self.uai_models.try_generate if self.uai_models is not None else None,
            seeded_answer=self.u_model.answer,
        )
        await self._emit_reply(
            session_id,
            result.text,
            response_source=result.response_source,
            adapter_loaded=result.adapter_loaded,
            model_run_id=result.model_run_id,
        )
        return result.text

    async def _emit_reply(
        self,
        session_id: str,
        text: str,
        *,
        response_source: str,
        adapter_loaded: bool,
        model_run_id: str | None = None,
    ) -> None:
        self.repo.append_transcript(session_id, TranscriptEntry(role="u", text=text))
        await self.bus.publish(
            session_id,
            AgentMessage(
                text=text,
                response_source=response_source,
                adapter_loaded=adapter_loaded,
                model_run_id=model_run_id,
            ),
        )

    async def _run_observation_pipeline(
        self,
        session_id: str,
        observation_in: ObservationIn,
        *,
        publish_default_message: bool,
    ) -> tuple[Observation, Decision]:
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

        if publish_default_message:
            message = render_agent_message(decision)
            if message is not None:
                await self._emit_reply(
                    session_id, message, response_source="governance_pipeline", adapter_loaded=False
                )
        return observation, decision

    def _observation_from_chat(self, prompt: str) -> ObservationIn | None:
        if _HAND_RAISE_PATTERN.search(prompt) is None and _HAND_LOWERED_PATTERN.search(prompt) is None:
            return None
        return ObservationIn(
            modality="chat",
            event_type="participant_raised_hand",
            value=_HAND_LOWERED_PATTERN.search(prompt) is None,
            confidence=_extract_confidence(prompt),
            source="chat_observation_parser",
        )

    def _render_decision_trace(self, observation: Observation, decision: Decision) -> str:
        action_name = decision.action.name if decision.action is not None else "none"
        action_rationale = decision.action.rationale if decision.action is not None else "No action selected."
        path = " -> ".join(decision.semantic_path) if decision.semantic_path else "none"
        evidence = decision.evidence[0] if decision.evidence else None
        observed = (
            f"{observation.event_type}={bool(observation.value)} "
            f"with confidence {observation.confidence:.2f}"
        )
        evidence_line = (
            f"{evidence.proposition} from {evidence.provenance.module}"
            if evidence is not None
            else "no mapped evidence"
        )
        bias = (
            "passed"
            if decision.bias_audit.passed
            else f"failed ({decision.bias_audit.protected_paths})"
        )
        safety = (
            "passed"
            if decision.safety_audit.passed
            else f"failed ({', '.join(decision.safety_audit.policy_flags)})"
        )
        return (
            "Observable evidence only: "
            f"{observed}. Mapped evidence: {evidence_line}. "
            f"Posterior P({decision.proposition}) = {decision.probability:.4f}; "
            f"uncertainty = {decision.uncertainty:.4f}; state = {decision.state.value}. "
            f"Semantic path: {path}. "
            f"Bias audit: {bias}. Safety audit: {safety}. "
            f"Final action: {action_name}. Rationale: {action_rationale}"
        )

    def rereason_latest(self, session_id: str) -> Decision:
        """Re-run reasoning over the most recent stored observation."""
        session = self.get_session(session_id)
        if not session.observations:
            raise NoObservationsError(session_id)
        decision = self.engine.reason(session_id, session.observations[-1])
        self.repo.add_decision(session_id, decision)
        return decision


def _extract_confidence(prompt: str) -> float:
    for pattern in _CONFIDENCE_PATTERNS:
        match = pattern.search(prompt)
        if match is None:
            continue
        raw = float(match.group("number"))
        confidence = raw / 100.0 if match.group("percent") or raw > 1.0 else raw
        return min(max(confidence, 0.0), 1.0)
    return 0.9
