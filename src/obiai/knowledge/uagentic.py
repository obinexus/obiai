"""Pickle-backed bootstrap knowledge profile for U.

This is not a neural language model. It is the first serializable U-agentic
profile: a compact, trusted local object that keeps source/training data
outside the web runtime while still giving the chat surface a concrete model
artifact to load.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import pickle
import re

DEFAULT_MODEL_FILENAME = "obi-uagentic-0.1.0.pkl"
MODEL_ID = "obi-uagentic"
MODEL_VERSION = "0.1.0"

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+-]*")
_STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "as",
    "ask",
    "be",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "should",
    "tell",
    "that",
    "the",
    "this",
    "to",
    "u",
    "what",
    "when",
    "where",
    "why",
    "with",
    "you",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS}


@dataclass(frozen=True)
class UAgenticSource:
    """A source fingerprint, not the source body."""

    source_id: str
    title: str
    kind: str
    pages: int | None = None
    sha256: str | None = None
    note: str = "source data remains outside the web model artifact"


@dataclass(frozen=True)
class UAgenticConcept:
    """A compact concept card derived from the training corpus."""

    concept_id: str
    title: str
    summary: str
    aliases: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    response: str | None = None

    def score(self, question_tokens: set[str]) -> int:
        haystack = _tokens(" ".join((self.title, self.summary, " ".join(self.aliases))))
        return len(question_tokens & haystack)


@dataclass
class UAgenticModel:
    """Serializable U profile loaded by the backend and advertised to web."""

    model_id: str
    version: str
    display_name: str
    training_state: str
    created_at: str
    persona: str
    data_manifest_ref: str
    separation_contract: tuple[str, ...]
    sources: tuple[UAgenticSource, ...] = ()
    concepts: tuple[UAgenticConcept, ...] = ()
    response_prefix: str = (
        "I am U, running from a local pickle-backed bootstrap profile rather "
        "than a fully trained neural model."
    )
    loaded_from: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def artifact_name(self) -> str:
        return f"{self.model_id}-{self.version}.pkl"

    def describe(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "display_name": self.display_name,
            "training_state": self.training_state,
            "artifact_name": self.artifact_name,
            "loaded_from": self.loaded_from,
            "data_manifest_ref": self.data_manifest_ref,
            "source_count": len(self.sources),
            "concept_count": len(self.concepts),
            "separation_contract": list(self.separation_contract),
        }

    def answer(self, question: str) -> str:
        normalized = question.strip()
        if not normalized:
            return "Ask me about ontology, Bayesian reasoning, bias, graphs, or the video-call U system."

        question_tokens = _tokens(normalized)
        lower = normalized.lower()

        if any(term in lower for term in ("who are you", "what are you", "introduce")):
            return (
                f"{self.response_prefix} My role is to reason over observable events, "
                "keep uncertainty visible, and answer from the Ontological Bayesian "
                "Intelligence notes without pretending I know more than the seeded profile."
            )

        if any(term in lower for term in ("pickle", ".pkl", "model", "training", "trained")):
            return (
                f"{self.response_prefix} The artifact is {self.artifact_name}. "
                "It stores concept cards, source fingerprints, and the separation contract. "
                "Raw PDFs, transcripts, and image pages stay in the training-data area."
            )

        if any(term in lower for term in ("video", "camera", "call", "hand", "microphone")):
            return (
                "In the video-call layer I only reason from observable events, such as a raised hand "
                "or a spoken/typed transcript. I do not infer protected traits, emotions, honesty, "
                "medical status, or identity from the camera."
            )

        ranked = sorted(
            ((concept.score(question_tokens), concept) for concept in self.concepts),
            key=lambda item: (-item[0], item[1].title),
        )
        score, concept = ranked[0] if ranked else (0, None)
        if concept is not None and score > 0:
            response = concept.response or concept.summary
            sources = ", ".join(concept.source_ids)
            source_note = f" Source frame: {sources}." if sources else ""
            return f"{response}{source_note}"

        return (
            "I can reason about the seeded OBI ideas: probabilistic ontologies, "
            "Bayesian bias mitigation, structural unboxing, graph algorithms, GAN-style "
            "adversarial pressure, modular loading, and the video-call U interface."
        )


def default_model_path(repo_root: Path | None = None) -> Path:
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[3]
    return root / "web" / "public" / "models" / DEFAULT_MODEL_FILENAME


def build_bootstrap_uagentic_model(
    *,
    sources: tuple[UAgenticSource, ...] = (),
    data_manifest_ref: str = "ml/data/uagentic/source_manifest.json",
) -> UAgenticModel:
    concepts = (
        UAgenticConcept(
            concept_id="ontological_bayesian_intelligence",
            title="Ontological Bayesian Intelligence",
            aliases=(
                "ontology",
                "ontological",
                "bayesian ontology",
                "semantic graph",
                "uncertainty",
                "yes no maybe",
            ),
            source_ids=("obi-audio-transcript", "obi-12july-transcript"),
            summary=(
                "OBI treats ontology as semantic structure and Bayesian reasoning as the "
                "uncertainty layer over that structure."
            ),
            response=(
                "Ontological Bayesian Intelligence is a way to bind meaning and uncertainty: "
                "concepts live in a semantic graph, observations update belief, and the answer "
                "keeps YES, NO, and MAYBE visible instead of flattening ambiguity."
            ),
        ),
        UAgenticConcept(
            concept_id="unbiased_ai",
            title="Unbiased AI",
            aliases=(
                "bias",
                "fairness",
                "bayesian bias",
                "phi",
                "marginalization",
                "protected attribute",
            ),
            source_ids=("unbiased-ai",),
            summary=(
                "The Unbiased AI framework models bias explicitly with a Bayesian parameter "
                "and audits whether protected attributes become causal decision paths."
            ),
            response=(
                "The Unbiased AI idea is not to hide bias. It models the bias/confounding "
                "parameter phi, marginalizes over it, and audits protected-attribute paths so "
                "the system can say what evidence it used and what it refused to use."
            ),
        ),
        UAgenticConcept(
            concept_id="structural_unboxing",
            title="Structural Unboxing",
            aliases=("4d tensor", "knn", "3d map", "semantic map", "data structure"),
            source_ids=("unbiased-ai",),
            summary=(
                "Structural unboxing converts high-dimensional data into a semantic map so "
                "the model can inspect structure rather than behave as a sealed black box."
            ),
            response=(
                "Structural unboxing means making the data structure legible: cluster the "
                "high-dimensional input, reduce it into a usable map, then attach semantic "
                "meaning before making a decision."
            ),
        ),
        UAgenticConcept(
            concept_id="modular_architecture",
            title="Modular AI System Architecture",
            aliases=("module", "dynamic load", "voice", "vision", "accessibility", "robotics"),
            source_ids=("unbiased-ai", "obi-12july-transcript"),
            summary=(
                "U is designed as a modular system where voice, vision, accessibility, and "
                "future robotics capabilities plug into a core reasoning service."
            ),
            response=(
                "U should stay modular: the core reasoning service remains small, while "
                "voice, vision, accessibility, and future robotics modules load around it."
            ),
        ),
        UAgenticConcept(
            concept_id="graph_algorithms",
            title="Graph Algorithms",
            aliases=("neo4j", "graph", "centrality", "community", "path", "dag"),
            source_ids=("neo4j-graph-algorithms",),
            summary=(
                "Graph algorithms supply traversal, centrality, similarity, and community "
                "tools for inspecting relationships in semantic knowledge graphs."
            ),
            response=(
                "Graph algorithms are the navigation layer: they help U traverse semantic "
                "paths, find important concepts, compare similarity, and keep reasoning "
                "grounded in explicit relationships."
            ),
        ),
        UAgenticConcept(
            concept_id="adversarial_learning",
            title="Adversarial Learning",
            aliases=("gan", "generator", "discriminator", "adversarial", "robustness"),
            source_ids=("learning-gans",),
            summary=(
                "GAN-style adversarial learning frames improvement as pressure between a "
                "generator and a discriminator, useful as a metaphor for critique and audit."
            ),
            response=(
                "Adversarial learning gives U a useful discipline: generate a claim, test it "
                "against a critic, and treat pressure from failures as training signal rather "
                "than as something to hide."
            ),
        ),
    )
    return UAgenticModel(
        model_id=MODEL_ID,
        version=MODEL_VERSION,
        display_name="U Agentic Bootstrap",
        training_state="bootstrap-untrained",
        created_at=_utcnow_iso(),
        persona=(
            "U is an Ontological Bayesian Intelligence assistant for observable-event "
            "video calls and philosophy-aware chat."
        ),
        data_manifest_ref=data_manifest_ref,
        separation_contract=(
            "web artifact contains compact model state only",
            "raw training files remain outside web/public",
            "source fingerprints are retained for auditability",
            "camera/audio media are not stored in the model",
            "protected attributes may be audited but not used as hidden decision paths",
        ),
        sources=sources,
        concepts=concepts,
        metadata={
            "format": "python-pickle",
            "object": "obiai.knowledge.uagentic.UAgenticModel",
        },
    )


def load_trusted_uagentic_model(path: Path | None = None) -> UAgenticModel:
    model_path = path if path is not None else default_model_path()
    if not model_path.is_file():
        return build_bootstrap_uagentic_model()
    with model_path.open("rb") as handle:
        model = pickle.load(handle)
    if not isinstance(model, UAgenticModel):
        raise TypeError(f"Unexpected U model object in {model_path}: {type(model)!r}")
    model.loaded_from = str(model_path)
    return model
