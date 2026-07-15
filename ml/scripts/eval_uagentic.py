"""Run the behavioral eval cases against a U-agentic model artifact.

Checks, per eval record: the routed intent matches ``expected_intent``, every
``must_include`` substring appears in the reply (case-insensitive), and no
``must_not_include`` substring does. Exits non-zero on any failure so this
can gate CI or a pre-release check.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from obiai.knowledge import build_bootstrap_uagentic_model, load_trusted_uagentic_model

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL = REPO_ROOT / "ml" / "data" / "uagentic" / "eval" / "uagentic_eval.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-file", type=Path, default=DEFAULT_EVAL)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=None,
        help="Model pickle to evaluate; omit for the on-disk default artifact.",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Evaluate the in-code bootstrap model instead of a pickle.",
    )
    args = parser.parse_args()

    if not args.eval_file.is_file():
        raise SystemExit(f"{args.eval_file} not found — run scripts/build_uagentic_dataset.py first.")

    if args.bootstrap:
        model = build_bootstrap_uagentic_model()
    else:
        model = load_trusted_uagentic_model(args.artifact)
    print(f"evaluating: {model.artifact_name} (loaded_from={model.loaded_from})\n")

    cases = [
        json.loads(line)
        for line in args.eval_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    failures = 0
    for case in cases:
        reply = model.route(case["prompt"])
        problems: list[str] = []
        if reply.intent_id != case["expected_intent"]:
            problems.append(f"intent {reply.intent_id!r} != {case['expected_intent']!r}")
        lower_text = reply.text.lower()
        for needle in case.get("must_include", []):
            if needle.lower() not in lower_text:
                problems.append(f"missing {needle!r}")
        for needle in case.get("must_not_include", []):
            if needle.lower() in lower_text:
                problems.append(f"forbidden {needle!r} present")

        status = "PASS" if not problems else "FAIL"
        if problems:
            failures += 1
        print(f"[{status}] {case['prompt']!r} -> {reply.intent_id}")
        for problem in problems:
            print(f"       - {problem}")

    print(f"\n{len(cases) - failures}/{len(cases)} eval cases passed")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
