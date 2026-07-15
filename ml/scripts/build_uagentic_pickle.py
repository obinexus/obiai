"""Build the local U-agentic pickle artifact from source fingerprints.

The output pickle is intentionally compact: it contains source hashes, concept
cards, and the model separation contract. It does not embed raw transcript,
PDF, image, audio, or video training data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import pickle
from typing import Any

from obiai.knowledge import (
    UAgenticSource,
    build_bootstrap_uagentic_model,
    default_model_path,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "ml" / "data" / "uagentic" / "source_manifest.json"


def _downloads() -> Path:
    return Path.home() / "Downloads"


DEFAULT_SOURCES: tuple[tuple[str, str, str, Path], ...] = (
    (
        "obi-audio-transcript",
        "Ontological Bayesian Intelligence audio transcript",
        "text/transcript",
        _downloads() / "ontologicalbayesianintelligence-audio.txt",
    ),
    (
        "obi-12july-transcript",
        "Ontological Bayesian Intelligence July 12 transcript",
        "text/transcript",
        _downloads() / "OntologicalBayesianIntelligence 12July.txt",
    ),
    (
        "learning-gans",
        "Learning Generative Adversarial Networks",
        "application/pdf",
        _downloads()
        / "Learning generative adversarial networks _ next-generation deep learning simplified ( PDFDrive ).pdf",
    ),
    (
        "neo4j-graph-algorithms",
        "Neo4j Graph Algorithms",
        "application/pdf",
        _downloads() / "Neo4j Graph Algorithm.pdf",
    ),
    (
        "unbiased-ai",
        "Formal Argument for Bias in AI Systems",
        "application/pdf",
        _downloads() / "Unbiased_AI.pdf",
    ),
)


def _unbiased_png_sources() -> list[tuple[str, str, str, Path]]:
    root = _downloads() / "Unbiased_AI"
    return [
        (
            f"unbiased-ai-page-{page}",
            f"Unbiased AI page {page} PNG",
            "image/png",
            root / f"Unbiased_AI-{page}.png",
        )
        for page in range(1, 8)
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pdf_page_count(path: Path) -> int | None:
    try:
        from pypdf import PdfReader
    except Exception:
        return None
    try:
        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def build_sources(include_png_pages: bool) -> tuple[list[UAgenticSource], list[dict[str, Any]]]:
    source_specs = list(DEFAULT_SOURCES)
    if include_png_pages:
        source_specs.extend(_unbiased_png_sources())

    model_sources: list[UAgenticSource] = []
    manifest_entries: list[dict[str, Any]] = []
    for source_id, title, kind, path in source_specs:
        if not path.is_file():
            raise FileNotFoundError(f"source not found: {path}")
        pages = pdf_page_count(path) if kind == "application/pdf" else None
        fingerprint = sha256(path)
        model_sources.append(
            UAgenticSource(
                source_id=source_id,
                title=title,
                kind=kind,
                pages=pages,
                sha256=fingerprint,
            )
        )
        manifest_entries.append(
            {
                "source_id": source_id,
                "title": title,
                "kind": kind,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": fingerprint,
                "pages": pages,
                "included_in_pickle": "fingerprint_and_derived_concepts_only",
            }
        )
    return model_sources, manifest_entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_model_path(REPO_ROOT))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--skip-png-pages",
        action="store_true",
        help="Only fingerprint the PDFs/transcripts, not the Unbiased_AI page PNGs.",
    )
    args = parser.parse_args()

    model_sources, manifest_entries = build_sources(include_png_pages=not args.skip_png_pages)
    manifest_ref = args.manifest.relative_to(REPO_ROOT).as_posix()
    model = build_bootstrap_uagentic_model(
        sources=tuple(model_sources),
        data_manifest_ref=manifest_ref,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as handle:
        pickle.dump(model, handle, protocol=pickle.HIGHEST_PROTOCOL)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(
            {
                "model": model.describe(),
                "source_policy": {
                    "raw_training_data_location": "external/local only",
                    "web_artifact_policy": "no raw source bodies in pickle",
                },
                "sources": manifest_entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {args.output}")
    print(f"Wrote {args.manifest}")
    print(f"Sources fingerprinted: {len(model_sources)}")


if __name__ == "__main__":
    main()
