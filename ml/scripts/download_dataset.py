"""Download and archive the OASST2 dataset from Hugging Face.

Uses huggingface_hub directly (not a raw curl against the resolve URL) so
redirects and LFS pointers are handled correctly — a plain curl against the
resolve URL for these files returns an S3 AccessDenied error.
"""

from __future__ import annotations

from pathlib import Path

from huggingface_hub import hf_hub_download

REPO_ID = "OpenAssistant/oasst2"
DEST = Path(__file__).resolve().parent.parent / "data" / "oasst2"

# The "ready for export" files: deduplicated, spam-filtered, non-deleted
# message trees — the canonical archive per the dataset card.
FILES = [
    "2023-11-05_oasst2_ready.trees.jsonl.gz",
    "2023-11-05_oasst2_ready.messages.jsonl.gz",
]


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    for filename in FILES:
        path = hf_hub_download(
            repo_id=REPO_ID,
            repo_type="dataset",
            filename=filename,
            local_dir=DEST,
        )
        size_mb = Path(path).stat().st_size / (1024 * 1024)
        print(f"archived {filename} -> {path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
