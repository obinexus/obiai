"""Speech-transcript normalization and confidence-aware response.

Speech recognition is two separate stages, and this module is only the
second one:

    audio -> speech-to-text engine -> transcript
          -> UAI transcript normalization and response   (this module)

Nothing here decodes audio. It takes already-recognized text plus the
recognizer's own confidence score and decides whether to answer it, or to
ask for confirmation instead of guessing at what a low-confidence
recognition might have meant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

__all__ = [
    "LOW_CONFIDENCE_THRESHOLD",
    "UAIResponse",
    "answer_transcript",
    "normalize_transcript",
]

LOW_CONFIDENCE_THRESHOLD = 0.6

GenerateFn = Callable[[str], "tuple[str, str] | None"]
SeededAnswerFn = Callable[[str], str]

# Speech recognizers spell OBIAI/OBINexus terms out phonetically because
# they are not dictionary words. Correcting them is a lookup, not a language
# understanding problem, so it happens deterministically here rather than
# being left to the trained model to guess at.
_TERM_GLOSSARY: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bo\s*b\s*i\s*eye\b", re.IGNORECASE), "OBIAI"),
    (re.compile(r"\bobi\s*eye\b", re.IGNORECASE), "OBIAI"),
    (re.compile(r"\bobi\s*a\s*i\b", re.IGNORECASE), "OBIAI"),
    (re.compile(r"\byou\s*a\s*eye\b", re.IGNORECASE), "UAI"),
    (re.compile(r"\byou\s*eye\b", re.IGNORECASE), "UAI"),
    (re.compile(r"\bobi\s*nexus\b", re.IGNORECASE), "OBINexus"),
    (re.compile(r"\bobey\s*nexus\b", re.IGNORECASE), "OBINexus"),
    (re.compile(r"\bq\s*lora\b", re.IGNORECASE), "QLoRA"),
    (re.compile(r"\blora\b", re.IGNORECASE), "LoRA"),
)


@dataclass(frozen=True)
class UAIResponse:
    """A chat/voice reply carrying honest provenance metadata.

    ``response_source`` is one of ``"governance_pipeline"``, ``"trained_uai"``,
    ``"seeded_uagentic"``, or ``"transcript_confidence_guard"`` -- never
    ``"trained_uai"`` unless ``adapter_loaded`` is also true.
    """

    text: str
    response_source: str
    adapter_loaded: bool
    model_run_id: str | None = None
    normalized_transcript: str | None = None
    confidence_label: str | None = None


def normalize_transcript(transcript: str) -> str:
    """Punctuation/casing cleanup plus OBIAI/OBINexus term correction."""
    text = transcript.strip()
    for pattern, canonical in _TERM_GLOSSARY:
        text = pattern.sub(canonical, text)
    if not text:
        return text
    text = text[0].upper() + text[1:]
    if text[-1] not in ".!?":
        text += "."
    return text


def answer_transcript(
    transcript: str,
    *,
    confidence: float | None = None,
    language: str | None = None,
    generate: GenerateFn | None = None,
    seeded_answer: SeededAnswerFn | None = None,
) -> UAIResponse:
    """Normalize a transcript and answer it, or ask for confirmation.

    When ``confidence`` is below :data:`LOW_CONFIDENCE_THRESHOLD`, the
    trained model is never invoked: an uncertain recognition is not
    silently rewritten into a confident-sounding fact, it is surfaced back
    as a possible interpretation and confirmation is requested.
    """
    _ = language  # reserved for future locale-specific normalization
    normalized = normalize_transcript(transcript)

    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        return UAIResponse(
            text=f"I may have heard: '{normalized}' Please confirm.",
            response_source="transcript_confidence_guard",
            adapter_loaded=False,
            normalized_transcript=normalized,
            confidence_label="low",
        )

    confidence_label = "high" if confidence is not None else None

    if generate is not None:
        result = generate(normalized)
        if result is not None:
            text, run_id = result
            return UAIResponse(
                text=text,
                response_source="trained_uai",
                adapter_loaded=True,
                model_run_id=run_id,
                normalized_transcript=normalized,
                confidence_label=confidence_label,
            )

    fallback_text = seeded_answer(normalized) if seeded_answer is not None else normalized
    return UAIResponse(
        text=fallback_text,
        response_source="seeded_uagentic",
        adapter_loaded=False,
        normalized_transcript=normalized,
        confidence_label=confidence_label,
    )
