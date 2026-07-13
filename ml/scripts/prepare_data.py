"""Convert OASST2 conversation trees into flat prompt/completion SFT pairs.

For every non-deleted assistant message in a ready_for_export tree, emits one
training example: the conversation so far (rendered with a simple Human/
Assistant template) as the prompt, and that assistant message as the
completion. This is the standard "one example per assistant turn" SFT
construction used for the original OpenAssistant models.

No special tokens are added to the tokenizer (keeps QLoRA simple — no
embedding-matrix resizing); <|endoftext|> already exists in the GPT-NeoX /
Pythia vocabulary and is used as the completion terminator.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Iterator

COMPLETION_SUFFIX = "<|endoftext|>"

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "oasst2"
DEFAULT_INPUT = DATA_DIR / "2023-11-05_oasst2_ready.trees.jsonl.gz"
DEFAULT_OUTPUT = DATA_DIR / "sft_pairs.jsonl"


def build_prompt(history: list[dict]) -> str:
    """Render prior turns, ending with the '### Assistant: ' generation cue."""
    blocks = []
    for turn in history:
        if turn["role"] == "prompter":
            blocks.append(f"### Human: {turn['text']}\n\n")
        else:
            blocks.append(f"### Assistant: {turn['text']}{COMPLETION_SUFFIX}\n\n")
    return "".join(blocks) + "### Assistant: "


def is_low_quality(node: dict) -> bool:
    labels = node.get("labels") or {}
    spam = labels.get("spam", {}).get("value")
    inappropriate = labels.get("not_appropriate", {}).get("value")
    if spam is not None and spam >= 0.5:
        return True
    if inappropriate is not None and inappropriate >= 0.5:
        return True
    return False


def walk_tree(
    node: dict, history: list[dict], lang: str | None, max_turns: int
) -> Iterator[dict]:
    if node.get("deleted"):
        return
    if len(history) >= max_turns:
        return

    if node["role"] == "assistant" and not is_low_quality(node):
        if lang is None or node.get("lang") == lang:
            yield {
                "prompt": build_prompt(history),
                "completion": f"{node['text']}{COMPLETION_SUFFIX}",
            }

    new_history = history + [{"role": node["role"], "text": node["text"]}]
    for reply in node.get("replies", []):
        yield from walk_tree(reply, new_history, lang, max_turns)


def iter_trees(path: Path) -> Iterator[dict]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--lang", default="en", help="Keep only this language's assistant turns; 'all' for no filter."
    )
    parser.add_argument("--max-turns", type=int, default=10, help="Cap conversation depth per example.")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(
            f"{args.input} not found — run scripts/download_dataset.py first."
        )

    lang = None if args.lang == "all" else args.lang
    tree_count = 0
    example_count = 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        for tree in iter_trees(args.input):
            if tree.get("tree_state") != "ready_for_export":
                continue
            tree_count += 1
            for example in walk_tree(tree["prompt"], [], lang, args.max_turns):
                out.write(json.dumps(example) + "\n")
                example_count += 1

    print(f"Processed {tree_count} ready_for_export trees -> {example_count} SFT examples")
    print(f"Written to {args.output}")


if __name__ == "__main__":
    main()
