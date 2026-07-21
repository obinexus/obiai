"""Behavioral tests for the U-agentic knowledge model (intent routing).

These mirror ml/data/uagentic/eval/uagentic_eval.jsonl but run against the
in-code bootstrap model so they never depend on gitignored dataset files.
"""

import pickle

import pytest

from obiai.knowledge import (
    MODEL_VERSION,
    UAgenticModel,
    build_bootstrap_uagentic_model,
    load_trusted_uagentic_model,
)


@pytest.fixture(scope="module")
def model() -> UAgenticModel:
    return build_bootstrap_uagentic_model()


CASES = [
    ("who are you", "meta.identity", ["Hi, I am U"], ["seeded OBI ideas"]),
    ("how are you working", "meta.how_working", ["browser vision emits observable events"], []),
    ("what is OBI", "obi.core", ["Ontological Bayesian Intelligence", "uncertainty", "MAYBE"], []),
    ("what is Unbiased AI", "obi.unbiased_ai", ["phi", "marginaliz", "protected", "fairness"], []),
    (
        "what is prompt-free AI",
        "obi.prompt_free",
        ["observation", "flash hypotheses", "filter", "uncertainty", "probing"],
        [],
    ),
    ("how does the season change", "general.seasons", ["tilt", "orbit"], ["phi", "ontology"]),
    ("how is the weather today", "tool.weather_today", ["weather tool", "location"], []),
    ("give me the time of day", "tool.time_of_day", ["The current local time for U is"], []),
    (
        "what is the fastest car in the world",
        "tool.current_facts",
        ["current-facts", "retrieval"],
        ["mph", "km/h"],
    ),
    ("what am I holding", "tool.vision_object", ["classifier", "camera"], []),
    ("ok", "small_talk.ack", ["Got it"], ["Ontological Bayesian", "phi"]),
    ("what is weather", "general.weather_explainer", ["atmosphere"], ["which city"]),
    ("Can U answer well?", "meta.capability", ["governed surface", "tool route"], []),
    (
        "Can U answer while preserving OBINexus governance?",
        "meta.governance_preservation",
        ["posterior", "uncertainty", "safety", "bias"],
        ["seeded profile does not hold"],
    ),
]


@pytest.mark.parametrize(("prompt", "intent", "must", "must_not"), CASES, ids=lambda c: str(c)[:40])
def test_required_prompts_route_correctly(model, prompt, intent, must, must_not) -> None:
    reply = model.route(prompt)
    assert reply.intent_id == intent
    lower = reply.text.lower()
    for needle in must:
        assert needle.lower() in lower, f"missing {needle!r} in {reply.text!r}"
    for needle in must_not:
        assert needle.lower() not in lower, f"forbidden {needle!r} in {reply.text!r}"


def test_tool_routes_are_exposed(model) -> None:
    assert model.route("how is the weather today").tool_route == "weather_api"
    assert model.route("give me the time of day").tool_route == "system_clock"
    assert model.route("what is the fastest car in the world").tool_route == "web_retrieval"
    assert model.route("what am I holding").tool_route == "vision_classifier"
    assert model.route("what is OBI").tool_route is None


def test_unknown_prompts_probe_instead_of_generic_dump(model) -> None:
    replies = {
        model.answer("what do you think about quantum farming"),
        model.answer("zorbly gribble"),
        model.answer("evaluate the harbor tax proposal"),
    }
    # Not one identical canned dump: fallbacks name the observed topic.
    assert len(replies) == 3
    for text in replies:
        assert "probe" in text.lower() or "topic" in text.lower()


def test_small_talk_is_short_and_natural(model) -> None:
    for prompt in ("ok", "hi", "thanks"):
        text = model.answer(prompt)
        assert len(text) < 200
        assert "phi" not in text.lower()


def test_no_protected_trait_language_in_vision_answers(model) -> None:
    reply = model.route("what am I holding")
    assert "never infer protected traits" in reply.text.lower()


def test_describe_reports_routing_surface(model) -> None:
    profile = model.describe()
    assert profile["version"] == MODEL_VERSION
    assert profile["intent_count"] >= 10
    assert profile["concept_count"] >= 6
    assert "raw training files remain outside web/public" in profile["separation_contract"]


def test_stale_artifact_is_rebuilt_from_code(tmp_path) -> None:
    stale = build_bootstrap_uagentic_model()
    stale.version = "0.0.9"
    stale.intents = ()
    path = tmp_path / "obi-uagentic-0.0.9.pkl"
    with path.open("wb") as handle:
        pickle.dump(stale, handle)

    loaded = load_trusted_uagentic_model(path)
    assert loaded.version == MODEL_VERSION
    assert loaded.intents  # routing restored from code
    assert loaded.loaded_from == str(path)


def test_missing_artifact_falls_back_to_bootstrap(tmp_path) -> None:
    loaded = load_trusted_uagentic_model(tmp_path / "nope.pkl")
    assert loaded.version == MODEL_VERSION
    assert loaded.answer("what is OBI").startswith("OBI is Ontological Bayesian Intelligence")
