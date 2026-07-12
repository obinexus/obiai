"""Provider-neutral protocols for every external or swappable service.

The reasoning core depends only on these structural interfaces (dependency
inversion): FastAPI, MediaPipe, Whisper, Piper, PyMC, or a database can each
be swapped without touching the pipeline. Speech providers are declared here
but intentionally have no implementation yet (deferred phase).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Mapping, Protocol, runtime_checkable

from obiai.core.models import (
    Action,
    BiasReport,
    MappedEvidence,
    Observation,
    SafetyAudit,
    TranscriptSegment,
    TruthState,
)

if TYPE_CHECKING:
    from obiai.ontology import Ontology

__all__ = [
    "AgentPlanner",
    "BayesianReasoner",
    "BiasAuditorProtocol",
    "OntologyMapperProtocol",
    "SafetyAuditorProtocol",
    "SpeechToTextProvider",
    "TextToSpeechProvider",
    "VisionClassifier",
]


@runtime_checkable
class BayesianReasoner(Protocol):
    """Posterior probability of a binary target given boolean evidence.

    Satisfied structurally by both ``obiai.bayes.BayesianNetwork`` and
    ``obiai.bayesian.PhiMarginalizedNetwork``.
    """

    def query(self, target: str, evidence: Mapping[str, bool]) -> float: ...


@runtime_checkable
class OntologyMapperProtocol(Protocol):
    def map(self, observation: Observation) -> MappedEvidence: ...


@runtime_checkable
class BiasAuditorProtocol(Protocol):
    def audit_paths(self, ontology: "Ontology", decision_node: str) -> BiasReport: ...


@runtime_checkable
class SafetyAuditorProtocol(Protocol):
    def audit(self, observation: Observation, mapping: MappedEvidence) -> SafetyAudit: ...


@runtime_checkable
class AgentPlanner(Protocol):
    def plan(
        self,
        state: TruthState,
        proposition: str,
        probability: float,
        uncertainty: float,
        bias: BiasReport,
        safety: SafetyAudit,
    ) -> Action | None: ...


@runtime_checkable
class VisionClassifier(Protocol):
    """Server-side frame classification (browser-side classification is the
    default; this exists for future backend classifiers)."""

    async def classify(self, frame: bytes) -> list[Observation]: ...


@runtime_checkable
class SpeechToTextProvider(Protocol):
    """Deferred: streaming transcription provider (e.g. faster-whisper)."""

    def transcribe(
        self, audio: AsyncIterator[bytes]
    ) -> AsyncIterator[TranscriptSegment]: ...


@runtime_checkable
class TextToSpeechProvider(Protocol):
    """Deferred: speech synthesis provider (e.g. Piper)."""

    async def synthesize(self, text: str) -> bytes: ...
