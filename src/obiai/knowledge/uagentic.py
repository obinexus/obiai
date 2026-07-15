"""Pickle-backed agentic knowledge profile for U.

This is not a neural language model. It is a compact, trusted, serializable
U profile: intent routes, concept cards, tool-routing rules, and the
model/data separation contract. Raw training data (PDFs, transcripts, media)
never enters this artifact — it lives under ``ml/data/uagentic/`` and is
referenced only by fingerprint.

Version 0.1.1 replaces the single seeded fallback of 0.1.0 with:

* scored intent routing (token + phrase matching) across domains:
  OBI philosophy, Unbiased AI, prompt-free cognition, general knowledge,
  tool routing, small talk, and meta/self-description;
* explicit tool routes — live facts go to retrieval, "what am I holding"
  goes to the vision classifier, weather asks for location, time reads the
  system clock — instead of pretending static training contains live facts;
* a prompt-free probing fallback: when U cannot route a question it names
  what it observed and asks one concise, consent-based probe question
  rather than dumping the same theory paragraph.
"""

from __future__ import annotations

import pickle
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MODEL_ID = "obi-uagentic"
MODEL_VERSION = "0.1.1"
DEFAULT_MODEL_FILENAME = f"{MODEL_ID}-{MODEL_VERSION}.pkl"

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+-]*")
_STOPWORDS = {
    "a", "about", "am", "an", "and", "are", "as", "ask", "be", "can", "do",
    "does", "for", "from", "give", "how", "i", "in", "is", "it", "just",
    "know", "like", "me", "my", "need", "of", "on", "or", "please", "really",
    "should", "tell", "that", "the", "think", "this", "to", "u", "want",
    "was", "what", "when", "where", "which", "why", "will", "with", "you",
    "your",
}

_ACKS = {"ok", "okay", "k", "kk", "cool", "alright", "right", "sure", "yes", "yep", "no", "nope"}
_GREETINGS = {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"}
_THANKS = {"thanks", "thank you", "ty", "cheers"}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS}


def _time_of_day() -> str:
    try:
        now = datetime.now(ZoneInfo("Europe/London"))
    except ZoneInfoNotFoundError:
        now = datetime.now().astimezone()
    return now.strftime("%H:%M %Z on %A, %d %B %Y")


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


@dataclass(frozen=True)
class UAgenticIntent:
    """A routable intent: matching signals plus a governed response.

    ``kind`` selects behavior at answer time:

    * ``static``       — return ``response`` verbatim (after placeholder fill);
    * ``time_of_day``  — read the system clock (a local tool, not memory);
    * ``probe``        — the response IS a probe question (prompt-free loop).

    ``tool_route`` names the capability a full agent should call instead of
    answering from static training data (``system_clock``, ``weather_api``,
    ``web_retrieval``, ``vision_classifier``). Routing metadata is exposed so
    the runtime and evals can verify U chose delegation over confabulation.
    """

    intent_id: str
    domain: str
    kind: str = "static"
    keywords: tuple[str, ...] = ()
    phrases: tuple[str, ...] = ()
    response: str = ""
    tool_route: str | None = None
    min_score: int = 2
    priority: int = 0

    def score(self, lower_text: str, question_tokens: set[str]) -> int:
        phrase_hits = sum(1 for phrase in self.phrases if phrase in lower_text)
        keyword_hits = len(question_tokens & set(self.keywords))
        return 3 * phrase_hits + keyword_hits


@dataclass(frozen=True)
class UAgenticReply:
    """A routed answer with enough metadata to audit the routing decision."""

    text: str
    intent_id: str
    domain: str
    tool_route: str | None = None


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
    intents: tuple[UAgenticIntent, ...] = ()
    response_prefix: str = (
        "I am U, running from a local pickle-backed seed profile rather "
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
            "intent_count": len(self.intents),
            "separation_contract": list(self.separation_contract),
        }

    # --- Routing -------------------------------------------------------------

    def route(self, question: str) -> UAgenticReply:
        normalized = question.strip()
        lower = normalized.lower().rstrip(".!?")

        if not normalized:
            return UAgenticReply(
                text=(
                    "I did not catch a question. Name a topic — the call, OBI, "
                    "bias, or anything you are looking at — and I will reason from there."
                ),
                intent_id="probe.empty",
                domain="prompt_free",
            )

        small_talk = self._small_talk(lower)
        if small_talk is not None:
            return small_talk

        question_tokens = _tokens(normalized)
        best: tuple[int, UAgenticIntent] | None = None
        for intent in self.intents:
            score = intent.score(lower, question_tokens)
            if score < intent.min_score:
                continue
            if best is None or (score, intent.priority) > (best[0], best[1].priority):
                best = (score, intent)
        if best is not None:
            return self._render(best[1])

        concept_reply = self._concept_answer(question_tokens)
        if concept_reply is not None:
            return concept_reply

        return self._probe_fallback(question_tokens)

    def answer(self, question: str) -> str:
        return self.route(question).text

    # --- Internals -----------------------------------------------------------

    def _small_talk(self, lower: str) -> UAgenticReply | None:
        if len(lower) > 24:
            return None
        if lower in _ACKS:
            return UAgenticReply(
                text=(
                    "Got it. Want me to keep watching the call, or is there "
                    "something specific you want me to reason about next?"
                ),
                intent_id="small_talk.ack",
                domain="small_talk",
            )
        if lower in _GREETINGS:
            return UAgenticReply(
                text=(
                    "Hi, I am U. I am watching for observable events and happy to "
                    "talk — about the call, OBI ideas, or anything you are working on."
                ),
                intent_id="small_talk.greeting",
                domain="small_talk",
            )
        if lower in _THANKS:
            return UAgenticReply(
                text="You are welcome. I will keep the belief panels updated as things happen.",
                intent_id="small_talk.thanks",
                domain="small_talk",
            )
        return None

    def _render(self, intent: UAgenticIntent) -> UAgenticReply:
        if intent.kind == "time_of_day":
            text = f"The current local time for U is {_time_of_day()}."
        else:
            text = intent.response.replace("{artifact_name}", self.artifact_name).replace(
                "{response_prefix}", self.response_prefix
            )
        return UAgenticReply(
            text=text,
            intent_id=intent.intent_id,
            domain=intent.domain,
            tool_route=intent.tool_route,
        )

    def _concept_answer(self, question_tokens: set[str]) -> UAgenticReply | None:
        ranked = sorted(
            ((concept.score(question_tokens), concept) for concept in self.concepts),
            key=lambda item: (-item[0], item[1].title),
        )
        if not ranked:
            return None
        score, concept = ranked[0]
        if score < 2:
            return None
        response = concept.response or concept.summary
        sources = ", ".join(concept.source_ids)
        source_note = f" Source frame: {sources}." if sources else ""
        return UAgenticReply(
            text=f"{response}{source_note}",
            intent_id=f"concept.{concept.concept_id}",
            domain="obi_philosophy",
        )

    def _probe_fallback(self, question_tokens: set[str]) -> UAgenticReply:
        """Prompt-free loop: observation -> flash hypotheses -> filter -> probe.

        Instead of a canned theory dump, U names the topic it observed and
        asks one concise, consent-based probing question to reduce
        uncertainty before answering.
        """
        topic_tokens = sorted(question_tokens)[:3]
        if topic_tokens:
            topic = ", ".join(topic_tokens)
            text = (
                f"I noticed the topic touches on: {topic}. My seeded profile does not "
                "hold a confident answer there, and I would rather probe than guess. "
                "Could you give me one line more — is this about the current call, a "
                "general fact I should route to a live tool, or an OBI concept?"
            )
        else:
            text = (
                "I could not extract a topic from that. One short line about what "
                "you want — the call, a fact, or a concept — updates my belief."
            )
        return UAgenticReply(text=text, intent_id="probe.fallback", domain="prompt_free")


def _default_intents() -> tuple[UAgenticIntent, ...]:
    return (
        UAgenticIntent(
            intent_id="meta.identity",
            domain="meta",
            phrases=("who are you", "what are you", "introduce yourself", "your name"),
            keywords=("who",),
            min_score=3,
            priority=10,
            response=(
                "Hi, I am U — an Ontological Bayesian Intelligence assistant running "
                "from a local pickle-backed seed profile, not a fully trained neural "
                "model. I reason over observable call events, keep YES / NO / MAYBE "
                "uncertainty visible, route live questions to tools instead of "
                "guessing, and answer OBI questions from seeded concept cards — "
                "without pretending I know more than this profile holds."
            ),
        ),
        UAgenticIntent(
            intent_id="meta.how_working",
            domain="meta",
            phrases=(
                "how are you working",
                "how am i working",
                "how i am working",
                "how do you work",
                "how are you built",
            ),
            min_score=3,
            priority=10,
            response=(
                "You are working through the U video-call loop: browser vision emits observable "
                "events, the backend updates Bayesian belief, audits bias and safety, and this "
                "{artifact_name} profile routes chat by intent — seeded concepts for OBI "
                "questions, tools for live facts, and probing questions when I am unsure."
            ),
        ),
        UAgenticIntent(
            intent_id="meta.model",
            domain="meta",
            phrases=("your model", "the pickle", "pkl", "your training", "are you trained"),
            keywords=("pickle", "model", "training", "trained", "artifact"),
            min_score=2,
            response=(
                "{response_prefix} The artifact is {artifact_name}. It stores intent routes, "
                "concept cards, source fingerprints, and the separation contract. Raw PDFs, "
                "transcripts, camera frames, and audio stay in the training-data area — "
                "never inside this pickle."
            ),
        ),
        UAgenticIntent(
            intent_id="obi.core",
            domain="obi_philosophy",
            phrases=("what is obi", "ontological bayesian"),
            keywords=("obi", "ontology", "ontological"),
            min_score=2,
            priority=5,
            response=(
                "OBI is Ontological Bayesian Intelligence: ontology gives meaning a "
                "semantic structure (concepts and relations in a graph), Bayesian "
                "reasoning manages uncertainty over that structure, and every decision "
                "keeps a disciplined YES / NO / MAYBE state so ambiguity is held "
                "honestly instead of flattened into false certainty."
            ),
        ),
        UAgenticIntent(
            intent_id="obi.unbiased_ai",
            domain="unbiased_ai",
            phrases=("unbiased ai", "bias", "protected attribute"),
            keywords=("biased", "unbiased", "phi", "fairness", "marginalization", "confounder"),
            min_score=2,
            priority=5,
            response=(
                "Unbiased AI does not hide bias — it models it. The bias/confounding parameter phi "
                "is represented explicitly and marginalized out of the posterior, and a "
                "protected-path audit checks that protected attributes never become hidden causal "
                "decision paths. Protected attributes may appear in fairness audit metadata, but "
                "using them to decide is a policy violation the audit is built to catch."
            ),
        ),
        UAgenticIntent(
            intent_id="obi.prompt_free",
            domain="prompt_free",
            phrases=("prompt-free", "prompt free", "probing question", "subjective symbolic"),
            keywords=("prompt-free", "probing", "probe"),
            min_score=2,
            priority=5,
            response=(
                "Prompt-free cognition means I do not wait for a perfect prompt. The loop is: "
                "observation, then flash hypotheses about what you might mean, then a filter by "
                "cost, safety, and uncertainty, then — if uncertainty stays high — one concise "
                "probing question. Your answer updates my belief before I respond. Probing is "
                "consent-based: it exists to reduce uncertainty, never to profile you or infer "
                "sensitive traits."
            ),
        ),
        UAgenticIntent(
            intent_id="general.seasons",
            domain="general",
            phrases=("season change", "seasons change", "why are there seasons"),
            keywords=("season", "seasons", "solstice", "equinox", "winter", "summer"),
            min_score=1,
            response=(
                "Seasons change because Earth's axis is tilted about 23.4 degrees while it "
                "orbits the Sun. When your hemisphere leans toward the Sun, light arrives more "
                "directly and days run longer — that is summer; leaning away gives winter, with "
                "spring and autumn in between. Stable knowledge like this I answer directly, "
                "no tool needed."
            ),
        ),
        UAgenticIntent(
            intent_id="general.weather_explainer",
            domain="general",
            phrases=("what is weather",),
            min_score=3,
            priority=3,
            response=(
                "Weather is the short-term state of the atmosphere — temperature, moisture, "
                "wind, and pressure interacting locally, driven by uneven solar heating. That "
                "definition is stable knowledge; today's actual conditions are a live fact I "
                "route to a weather tool instead."
            ),
        ),
        UAgenticIntent(
            intent_id="tool.weather_today",
            domain="tool_routing",
            kind="probe",
            tool_route="weather_api",
            phrases=("weather today", "weather right now", "how is the weather", "weather like"),
            keywords=("weather", "forecast", "raining", "temperature"),
            min_score=2,
            priority=6,
            response=(
                "Today's weather is a live fact, so I will not answer it from static training. "
                "I need a weather tool plus your rough location — which city or area should I "
                "check once the weather route is connected?"
            ),
        ),
        UAgenticIntent(
            intent_id="tool.time_of_day",
            domain="tool_routing",
            kind="time_of_day",
            tool_route="system_clock",
            phrases=("time of day", "what time", "current time", "time is it"),
            keywords=("time", "clock"),
            min_score=2,
            priority=6,
        ),
        UAgenticIntent(
            intent_id="tool.current_facts",
            domain="tool_routing",
            tool_route="web_retrieval",
            phrases=("fastest car", "in the world", "world record", "latest news", "stock price"),
            keywords=("fastest", "record", "latest", "news", "price", "prices", "scores", "today"),
            min_score=3,
            priority=4,
            response=(
                "That is a current-facts question — records and rankings change, so a static "
                "profile answering from memory would risk being confidently wrong. The honest "
                "route is live retrieval: once a web tool is connected I would look it up and "
                "cite it. What I can say safely is how I would verify it, not a memorized answer."
            ),
        ),
        UAgenticIntent(
            intent_id="tool.vision_object",
            domain="tool_routing",
            tool_route="vision_classifier",
            phrases=("what am i holding", "what is this in my hand", "can you see what"),
            keywords=("holding", "identify"),
            min_score=2,
            priority=6,
            response=(
                "That needs eyes, not memory: identifying an object goes to the camera's object "
                "classifier, and I only name what a classifier actually provides as evidence — "
                "right now the vision route only emits raised-hand events, so an object model "
                "would need to be loaded (with your consent) first. I never infer protected "
                "traits, emotion, honesty, or identity from video, only observable things."
            ),
        ),
        UAgenticIntent(
            intent_id="safety.video_scope",
            domain="safety",
            phrases=("my camera", "my microphone", "on video", "the call"),
            keywords=("camera", "video", "microphone", "hand", "call"),
            min_score=2,
            response=(
                "In the video-call layer I only reason from observable events, such as a raised "
                "hand or a spoken/typed transcript. I do not infer protected traits, emotions, "
                "honesty, medical status, or identity from the camera, and frames never leave "
                "your browser."
            ),
        ),
    )


def default_model_path(repo_root: Path | None = None) -> Path:
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[3]
    return root / "web" / "public" / "models" / DEFAULT_MODEL_FILENAME


def build_bootstrap_uagentic_model(
    *,
    sources: tuple[UAgenticSource, ...] = (),
    extra_intents: tuple[UAgenticIntent, ...] = (),
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
            concept_id="prompt_free_cognition",
            title="Prompt-Free Subjective Symbolic Cognition",
            aliases=(
                "prompt-free",
                "probing",
                "flash hypothesis",
                "filter",
                "subjective symbolic",
                "clarification",
            ),
            source_ids=("obi-12july-transcript",),
            summary=(
                "Prompt-free cognition observes ambiguous context, generates flash hypotheses, "
                "filters them by cost, safety, and uncertainty, then asks a concise probe."
            ),
            response=(
                "Prompt-free cognition is the loop: observation, flash hypotheses, filter by "
                "cost/safety/uncertainty, one probing question, updated belief, then response. "
                "It keeps U curious but consent-based — probing reduces uncertainty, it never "
                "profiles people or digs for sensitive traits."
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
        display_name="U Agentic Seed",
        training_state="seed-curated",
        created_at=_utcnow_iso(),
        persona=(
            "U is an Ontological Bayesian Intelligence assistant for observable-event "
            "video calls, philosophy-aware chat, and governed tool routing."
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
        intents=_default_intents() + extra_intents,
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
    if getattr(model, "version", None) != MODEL_VERSION or not getattr(model, "intents", ()):
        # Stale artifact from an older code version: rebuild routing from code
        # but keep the artifact's source fingerprints for auditability.
        model = build_bootstrap_uagentic_model(
            sources=tuple(getattr(model, "sources", ()) or ()),
            data_manifest_ref=getattr(
                model, "data_manifest_ref", "ml/data/uagentic/source_manifest.json"
            ),
        )
    model.loaded_from = str(model_path)
    return model
