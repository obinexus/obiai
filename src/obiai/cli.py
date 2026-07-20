from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print

from .demo import build_demo_agent

app = typer.Typer(help="OBI Ontological Bayesian Intelligence CLI")
train_app = typer.Typer(help="Model training commands")
app.add_typer(train_app, name="train")


def parse_evidence(items: list[str]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for item in items:
        key, sep, raw = item.partition("=")
        if not sep or raw.lower() not in {"true", "false"}:
            raise typer.BadParameter("Evidence must use name=true or name=false")
        result[key] = raw.lower() == "true"
    return result


@app.command()
def demo() -> None:
    agent = build_demo_agent()
    decision = agent.reason("wet_grass", {"rain": True, "sprinkler": False})
    print(json.dumps(decision.model_dump(mode="json"), indent=2))


@app.command()
def reason(
    proposition: str = typer.Option("wet_grass", help="Binary target variable"),
    evidence: list[str] = typer.Option([], "--evidence", "-e"),
) -> None:
    agent = build_demo_agent()
    decision = agent.reason(proposition, parse_evidence(evidence))
    print(json.dumps(decision.model_dump(mode="json"), indent=2))


@train_app.command("uai")
def train_uai(
    base_model: str = typer.Option(
        "EleutherAI/pythia-2.8b",
        "--base-model",
        help="Base causal LM to QLoRA fine-tune.",
    ),
    data: Optional[Path] = typer.Option(
        None,
        "--data",
        help="Training JSONL path; defaults to ml/data/oasst2/sft_pairs_weighted.jsonl.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help="LoRA adapter output directory; defaults under ml/checkpoints.",
    ),
    max_steps: int = typer.Option(
        -1,
        "--max-steps",
        help="-1 trains by epoch count; positive values run a fixed-step job.",
    ),
    epochs: float = typer.Option(1.0, "--epochs", help="Number of training epochs."),
    batch_size: int = typer.Option(1, "--batch-size", help="Per-device train batch size."),
    grad_accum: int = typer.Option(16, "--grad-accum", help="Gradient accumulation steps."),
    lr: float = typer.Option(2e-4, "--lr", help="Learning rate."),
    warmup_ratio: float = typer.Option(0.03, "--warmup-ratio", help="Warmup ratio."),
    max_length: int = typer.Option(1024, "--max-length", help="Maximum tokenized sequence length."),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Use only the first N examples for smoke tests.",
    ),
) -> None:
    """QLoRA fine-tune UAI and save a LoRA adapter."""
    from obiai.training.uai_qlora import UAITrainingConfig, train_uai_qlora

    train_uai_qlora(
        UAITrainingConfig(
            base_model=base_model,
            data=data,
            output=output,
            max_steps=max_steps,
            epochs=epochs,
            batch_size=batch_size,
            grad_accum=grad_accum,
            lr=lr,
            warmup_ratio=warmup_ratio,
            max_length=max_length,
            limit=limit,
        )
    )


if __name__ == "__main__":
    app()
