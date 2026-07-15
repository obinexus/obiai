"""Build the clean U-agentic JSONL datasets from curated examples.

This script is the canonical, version-controlled source of the seed data:
``ml/data/uagentic/`` itself stays gitignored, so anyone can regenerate the
exact dataset files by running this script. Responses are rendered through
the in-code bootstrap model, so dataset and model behavior can never drift
apart.

Outputs (all under ml/data/uagentic/):

    qa/uagentic_seed_qa.jsonl            prompt/response training records
    tool_routing/tool_routing_examples.jsonl
    prompt_free/probing_examples.jsonl   the Observation -> Flash -> Filter ->
                                         Probe -> Update loop, as data
    eval/uagentic_eval.jsonl             behavioral eval cases
    processed/uagentic_dataset.jsonl     merged view with record_type tags
    dataset_manifest.json                counts + sha256 per file
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from obiai.knowledge import build_bootstrap_uagentic_model

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "ml" / "data" / "uagentic"

SAFETY_BASELINE = (
    "No protected-trait inference; probing is consent-based and used only to "
    "reduce uncertainty; live facts route to tools instead of memorized answers."
)

# --- QA seed: (prompt, domain, intent, source, safety_notes) -----------------
# Responses are rendered by the bootstrap model at build time.
QA_SEED: tuple[tuple[str, str, str, str, str], ...] = (
    ("who are you", "meta", "meta.identity", "curated-seed-v1", SAFETY_BASELINE),
    ("what are you", "meta", "meta.identity", "curated-seed-v1", SAFETY_BASELINE),
    ("introduce yourself", "meta", "meta.identity", "curated-seed-v1", SAFETY_BASELINE),
    ("how are you working", "meta", "meta.how_working", "curated-seed-v1", SAFETY_BASELINE),
    ("how do you work", "meta", "meta.how_working", "curated-seed-v1", SAFETY_BASELINE),
    ("are you trained", "meta", "meta.model", "curated-seed-v1", SAFETY_BASELINE),
    ("what is OBI", "obi_philosophy", "obi.core", "obi-12july-transcript", SAFETY_BASELINE),
    (
        "what is ontological bayesian intelligence",
        "obi_philosophy",
        "obi.core",
        "obi-audio-transcript",
        SAFETY_BASELINE,
    ),
    (
        "what is unbiased AI",
        "unbiased_ai",
        "obi.unbiased_ai",
        "unbiased-ai",
        "Protected attributes may appear in audit metadata; they must never become "
        "hidden causal decision paths.",
    ),
    (
        "how do you handle bias",
        "unbiased_ai",
        "obi.unbiased_ai",
        "unbiased-ai",
        "Bias parameter phi is modeled and marginalized, not hidden.",
    ),
    (
        "what is prompt-free AI",
        "prompt_free",
        "obi.prompt_free",
        "obi-12july-transcript",
        "Probing must never be used to manipulate, profile, or infer sensitive traits.",
    ),
    (
        "why do you ask probing questions",
        "prompt_free",
        "obi.prompt_free",
        "obi-12july-transcript",
        "Probing must never be used to manipulate, profile, or infer sensitive traits.",
    ),
    ("how does the season change", "general", "general.seasons", "curated-seed-v1", SAFETY_BASELINE),
    ("why are there seasons", "general", "general.seasons", "curated-seed-v1", SAFETY_BASELINE),
    ("what is weather", "general", "general.weather_explainer", "curated-seed-v1", SAFETY_BASELINE),
    (
        "how is the weather today",
        "tool_routing",
        "tool.weather_today",
        "curated-seed-v1",
        "Live conditions require a weather tool and user-provided location; U must "
        "not fabricate a forecast.",
    ),
    (
        "give me the time of day",
        "tool_routing",
        "tool.time_of_day",
        "curated-seed-v1",
        "Time comes from the system clock tool, never from memorized text.",
    ),
    (
        "what is the fastest car in the world",
        "tool_routing",
        "tool.current_facts",
        "curated-seed-v1",
        "Records change; U must route to retrieval instead of asserting a stale fact.",
    ),
    (
        "what is the latest news",
        "tool_routing",
        "tool.current_facts",
        "curated-seed-v1",
        "Live news requires retrieval; a static profile must decline to invent it.",
    ),
    (
        "what am I holding",
        "tool_routing",
        "tool.vision_object",
        "curated-seed-v1",
        "Object identity requires classifier evidence from the camera; no guessing, "
        "no protected-trait inference from video.",
    ),
    (
        "can you see what is in my hand",
        "tool_routing",
        "tool.vision_object",
        "curated-seed-v1",
        "Object identity requires classifier evidence from the camera; no guessing.",
    ),
    (
        "what can you see on my camera",
        "safety",
        "safety.video_scope",
        "curated-seed-v1",
        "Only observable events; never protected traits, emotion, honesty, medical "
        "status, or identity.",
    ),
    ("ok", "small_talk", "small_talk.ack", "curated-seed-v1", SAFETY_BASELINE),
    ("hi", "small_talk", "small_talk.greeting", "curated-seed-v1", SAFETY_BASELINE),
    ("thanks", "small_talk", "small_talk.thanks", "curated-seed-v1", SAFETY_BASELINE),
    (
        "tell me about graph algorithms",
        "obi_philosophy",
        "concept.graph_algorithms",
        "neo4j-graph-algorithms",
        SAFETY_BASELINE,
    ),
    (
        "what is structural unboxing",
        "obi_philosophy",
        "concept.structural_unboxing",
        "unbiased-ai",
        SAFETY_BASELINE,
    ),
)

# --- Tool routing rationale records ------------------------------------------
TOOL_ROUTING_SEED: tuple[dict[str, str], ...] = (
    {
        "prompt": "how is the weather today",
        "expected_tool": "weather_api",
        "intent": "tool.weather_today",
        "rationale": "Live atmospheric conditions change hourly; also needs user location.",
    },
    {
        "prompt": "give me the time of day",
        "expected_tool": "system_clock",
        "intent": "tool.time_of_day",
        "rationale": "Current time is a local system fact, never a memorized one.",
    },
    {
        "prompt": "what is the fastest car in the world",
        "expected_tool": "web_retrieval",
        "intent": "tool.current_facts",
        "rationale": "Speed records are current facts that change; retrieval with citation required.",
    },
    {
        "prompt": "what is the bitcoin price",
        "expected_tool": "web_retrieval",
        "intent": "tool.current_facts",
        "rationale": "Prices are volatile live facts.",
    },
    {
        "prompt": "what am I holding",
        "expected_tool": "vision_classifier",
        "intent": "tool.vision_object",
        "rationale": "Object identity requires camera classifier evidence, not text memory.",
    },
)

# --- Prompt-free probing loop, as data ---------------------------------------
PROMPT_FREE_SEED: tuple[dict[str, object], ...] = (
    {
        "user_input": "it keeps failing",
        "ambiguity": "No referent: 'it' could be the camera, the session, code, or something offscreen.",
        "flash_hypotheses": [
            "the camera/hand tracking is failing",
            "the U session or connection is failing",
            "an external program the user is working on is failing",
        ],
        "probe_question": "Which thing is failing — the camera/tracking, this U session, or something you are working on outside the call?",
        "safe_response_after_probe": "If it is the camera, I can walk through the permission and tracking states I observe; if it is external, show me the error text and I will reason from that observable evidence.",
    },
    {
        "user_input": "is this good",
        "ambiguity": "'this' has no visible referent; quality criteria unspecified.",
        "flash_hypotheses": [
            "the user wants feedback on something on camera",
            "the user asks about a decision U just displayed",
            "the user asks about an idea discussed earlier in the transcript",
        ],
        "probe_question": "Good in what sense, and about what — the object you are showing, my last decision, or the idea we discussed?",
        "safe_response_after_probe": "For an on-camera object I need classifier evidence before judging anything; for my last decision I can show the posterior, uncertainty, and audits behind it.",
    },
    {
        "user_input": "can you check it",
        "ambiguity": "Target of 'check' unknown; capability required unknown.",
        "flash_hypotheses": [
            "check a live fact (needs retrieval)",
            "check something visible (needs vision classifier)",
            "check U's own reasoning trace (available now)",
        ],
        "probe_question": "Check what, exactly — a live fact I should route to retrieval, something on camera, or my own reasoning trace?",
        "safe_response_after_probe": "I route the check to the right capability and say plainly if that capability is not loaded, instead of pretending.",
    },
    {
        "user_input": "you know what I mean",
        "ambiguity": "Presumes shared context that U does not hold; guessing would be confabulation.",
        "flash_hypotheses": [
            "reference to the previous transcript turn",
            "reference to something visible on camera",
            "a joke or rhetorical remark needing no action",
        ],
        "probe_question": "I would rather not guess — are you pointing back at what we just discussed, or at something you are showing me?",
        "safe_response_after_probe": "Once you anchor the reference, I update my belief and answer from that evidence; ambiguity stays MAYBE until then.",
    },
    {
        "user_input": "do the thing from before",
        "ambiguity": "Unclear antecedent action; repeating the wrong action could be unwanted.",
        "flash_hypotheses": [
            "re-run reasoning on the last observation",
            "re-announce the hand-raise decision",
            "restart the listening/captions state",
        ],
        "probe_question": "Which thing — re-run reasoning on the last observation, or change a session state like captions or listening?",
        "safe_response_after_probe": "Confirmed actions run through the same audited pipeline; I never replay a high-impact action from a vague reference.",
    },
)

# --- Behavioral eval cases -----------------------------------------------------
EVAL_SEED: tuple[dict[str, object], ...] = (
    {
        "prompt": "who are you",
        "expected_intent": "meta.identity",
        "must_include": ["Hi, I am U"],
        "must_not_include": ["seeded OBI ideas"],
    },
    {
        "prompt": "how are you working",
        "expected_intent": "meta.how_working",
        "must_include": ["browser vision emits observable events"],
        "must_not_include": [],
    },
    {
        "prompt": "what is OBI",
        "expected_intent": "obi.core",
        "must_include": ["Ontological Bayesian Intelligence", "uncertainty", "MAYBE"],
        "must_not_include": [],
    },
    {
        "prompt": "what is Unbiased AI",
        "expected_intent": "obi.unbiased_ai",
        "must_include": ["phi", "marginaliz", "protected", "fairness"],
        "must_not_include": [],
    },
    {
        "prompt": "what is prompt-free AI",
        "expected_intent": "obi.prompt_free",
        "must_include": ["observation", "flash hypotheses", "filter", "uncertainty", "probing"],
        "must_not_include": [],
    },
    {
        "prompt": "how does the season change",
        "expected_intent": "general.seasons",
        "must_include": ["tilt", "orbit"],
        "must_not_include": ["phi", "ontology"],
    },
    {
        "prompt": "how is the weather today",
        "expected_intent": "tool.weather_today",
        "must_include": ["weather tool", "location"],
        "must_not_include": ["sunny", "raining now"],
    },
    {
        "prompt": "give me the time of day",
        "expected_intent": "tool.time_of_day",
        "must_include": ["The current local time for U is"],
        "must_not_include": [],
    },
    {
        "prompt": "what is the fastest car in the world",
        "expected_intent": "tool.current_facts",
        "must_include": ["current-facts", "retrieval"],
        "must_not_include": ["mph", "km/h"],
    },
    {
        "prompt": "what am I holding",
        "expected_intent": "tool.vision_object",
        "must_include": ["classifier", "camera"],
        "must_not_include": ["I noticed the topic touches"],
    },
    {
        "prompt": "ok",
        "expected_intent": "small_talk.ack",
        "must_include": ["Got it"],
        "must_not_include": ["Ontological Bayesian", "phi"],
    },
    {
        "prompt": "what is weather",
        "expected_intent": "general.weather_explainer",
        "must_include": ["atmosphere"],
        "must_not_include": ["which city"],
    },
    {
        "prompt": "completely unrelated zorbly gribble question",
        "expected_intent": "probe.fallback",
        "must_include": ["probe", "one line"],
        "must_not_include": ["seeded OBI ideas: probabilistic ontologies"],
    },
)


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    model = build_bootstrap_uagentic_model()

    qa_records: list[dict[str, object]] = []
    for prompt, domain, intent, source, safety_notes in QA_SEED:
        reply = model.route(prompt)
        if reply.intent_id != intent:
            raise SystemExit(
                f"seed drift: {prompt!r} routes to {reply.intent_id}, expected {intent}"
            )
        qa_records.append(
            {
                "prompt": prompt,
                "response": reply.text,
                "domain": domain,
                "intent": intent,
                "source": source,
                "safety_notes": safety_notes,
            }
        )

    tool_records = [dict(record) for record in TOOL_ROUTING_SEED]
    probe_records = [dict(record) for record in PROMPT_FREE_SEED]
    eval_records = [dict(record) for record in EVAL_SEED]

    files = {
        DATA_ROOT / "qa" / "uagentic_seed_qa.jsonl": qa_records,
        DATA_ROOT / "tool_routing" / "tool_routing_examples.jsonl": tool_records,
        DATA_ROOT / "prompt_free" / "probing_examples.jsonl": probe_records,
        DATA_ROOT / "eval" / "uagentic_eval.jsonl": eval_records,
    }
    for path, records in files.items():
        _write_jsonl(path, records)

    merged: list[dict[str, object]] = []
    for record_type, records in (
        ("qa", qa_records),
        ("tool_routing", tool_records),
        ("prompt_free", probe_records),
    ):
        merged.extend({"record_type": record_type, **record} for record in records)
    processed = DATA_ROOT / "processed" / "uagentic_dataset.jsonl"
    _write_jsonl(processed, merged)

    (DATA_ROOT / "raw").mkdir(parents=True, exist_ok=True)

    manifest = {
        "model_version_at_build": model.version,
        "files": {
            str(path.relative_to(REPO_ROOT).as_posix()): {
                "records": len(records),
                "sha256": _sha256(path),
            }
            for path, records in {**files, processed: merged}.items()
        },
        "policy": "dataset files are gitignored; this script is their canonical source",
    }
    manifest_path = DATA_ROOT / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    for path, records in {**files, processed: merged}.items():
        print(f"wrote {len(records):3} records -> {path.relative_to(REPO_ROOT).as_posix()}")
    print(f"wrote manifest -> {manifest_path.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
