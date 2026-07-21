"""Tests for obiai.knowledge.transcript: normalization + confidence gate."""

from __future__ import annotations

import pytest

from obiai.knowledge.transcript import LOW_CONFIDENCE_THRESHOLD, answer_transcript, normalize_transcript


def test_normalize_transcript_fixes_obiai_obinexus_terms() -> None:
    assert normalize_transcript("obi eye train you a eye max steps eight") == (
        "OBIAI train UAI max steps eight."
    )


def test_normalize_transcript_fixes_obinexus() -> None:
    assert normalize_transcript("who runs obi nexus") == "Who runs OBINexus."


def test_normalize_transcript_adds_casing_and_punctuation() -> None:
    assert normalize_transcript("can you inspect this error") == "Can you inspect this error."


def test_normalize_transcript_empty_string() -> None:
    assert normalize_transcript("   ") == ""


def test_low_confidence_never_invokes_generation() -> None:
    def _boom(_prompt: str):
        raise AssertionError("generate() must not be called below the confidence threshold")

    result = answer_transcript(
        "load the new model pickle",
        confidence=LOW_CONFIDENCE_THRESHOLD - 0.1,
        generate=_boom,
        seeded_answer=_boom,
    )

    assert result.response_source == "transcript_confidence_guard"
    assert result.adapter_loaded is False
    assert result.confidence_label == "low"
    assert result.text == "I may have heard: 'Load the new model pickle.' Please confirm."


def test_high_confidence_uses_trained_model_when_available() -> None:
    result = answer_transcript(
        "what is OBIAI",
        confidence=0.95,
        generate=lambda prompt: (f"trained reply about: {prompt}", "run-42"),
        seeded_answer=lambda prompt: "seeded fallback",
    )

    assert result.response_source == "trained_uai"
    assert result.adapter_loaded is True
    assert result.model_run_id == "run-42"
    assert "trained reply" in result.text


def test_falls_back_to_seeded_answer_when_generate_returns_none() -> None:
    result = answer_transcript(
        "what is OBIAI",
        confidence=0.95,
        generate=lambda prompt: None,
        seeded_answer=lambda prompt: "seeded fallback text",
    )

    assert result.response_source == "seeded_uagentic"
    assert result.adapter_loaded is False
    assert result.model_run_id is None
    assert result.text == "seeded fallback text"


def test_falls_back_to_seeded_answer_when_no_generate_configured() -> None:
    result = answer_transcript(
        "what is OBIAI", confidence=None, generate=None, seeded_answer=lambda prompt: "seeded only"
    )

    assert result.response_source == "seeded_uagentic"
    assert result.text == "seeded only"


@pytest.mark.parametrize("confidence", [0.0, 0.59, LOW_CONFIDENCE_THRESHOLD - 1e-6])
def test_threshold_boundary_is_exclusive_below(confidence: float) -> None:
    result = answer_transcript(
        "test",
        confidence=confidence,
        generate=lambda prompt: (_ for _ in ()).throw(AssertionError("must not be called")),
    )
    assert result.response_source == "transcript_confidence_guard"


def test_threshold_boundary_at_exactly_threshold_is_not_low() -> None:
    result = answer_transcript(
        "test",
        confidence=LOW_CONFIDENCE_THRESHOLD,
        generate=lambda prompt: ("ok", "run-1"),
    )
    assert result.response_source == "trained_uai"
