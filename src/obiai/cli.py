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
model_app = typer.Typer(help="Inspect or reload the trained UAI model the chat runtime uses.")
app.add_typer(model_app, name="model")


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
    fast: bool = typer.Option(
        False,
        "--fast",
        help=(
            "Fast development profile: small OBIAI/OBINexus dataset slice, "
            "8 steps, no mid-run checkpoints, minimal logging."
        ),
    ),
    base_model: Optional[str] = typer.Option(
        None,
        "--base-model",
        help="Base causal LM to QLoRA fine-tune. Default: EleutherAI/pythia-2.8b.",
    ),
    data: Optional[Path] = typer.Option(
        None,
        "--data",
        help=(
            "Training JSONL path; defaults to ml/data/oasst2/sft_pairs_weighted.jsonl "
            "(ml/data/uai/uai_fast_pairs.jsonl with --fast)."
        ),
    ),
    hf_dataset: Optional[str] = typer.Option(
        None,
        "--hf-dataset",
        help="Online Hugging Face dataset ID to train from, e.g. xDAN-datasets/ChatQA-Training-Data.",
    ),
    hf_subset: Optional[str] = typer.Option(
        None,
        "--hf-subset",
        help="Optional Hugging Face dataset subset/config name, e.g. drop.",
    ),
    hf_split: str = typer.Option(
        "train",
        "--hf-split",
        help="Hugging Face dataset split to load when --hf-dataset is set.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help=(
            "LoRA adapter output directory. Leave unset to register the run in the "
            "artifacts/uai manifest so the chat runtime picks it up automatically."
        ),
    ),
    max_steps: Optional[int] = typer.Option(
        None,
        "--max-steps",
        help="-1 trains by epoch count; positive values run a fixed-step job.",
    ),
    epochs: Optional[float] = typer.Option(None, "--epochs", help="Number of training epochs."),
    batch_size: Optional[int] = typer.Option(None, "--batch-size", help="Per-device train batch size."),
    grad_accum: Optional[int] = typer.Option(None, "--grad-accum", help="Gradient accumulation steps."),
    lr: Optional[float] = typer.Option(None, "--lr", help="Learning rate."),
    warmup_ratio: Optional[float] = typer.Option(None, "--warmup-ratio", help="Warmup ratio."),
    max_length: Optional[int] = typer.Option(
        None, "--max-length", help="Maximum tokenized sequence length."
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Use only the first N examples for smoke tests.",
    ),
    precision: str = typer.Option(
        "auto",
        "--precision",
        help="Training precision: auto, bf16, fp16, or fp32.",
    ),
    dataloader_workers: Optional[int] = typer.Option(
        None,
        "--dataloader-workers",
        help="Dataset loading worker processes. Default: 0 (safest on Windows).",
    ),
    gradient_checkpointing: Optional[bool] = typer.Option(
        None,
        "--gradient-checkpointing/--no-gradient-checkpointing",
        help="Default: on for a full run, off for --fast (not needed at that scale).",
    ),
) -> None:
    """QLoRA fine-tune UAI and register the result in the artifact manifest."""
    from obiai.training.uai_qlora import resolve_uai_training_config, train_uai_qlora

    config = resolve_uai_training_config(
        fast=fast,
        base_model=base_model,
        data=data,
        hf_dataset=hf_dataset,
        hf_subset=hf_subset,
        hf_split=hf_split,
        output=output,
        max_steps=max_steps,
        epochs=epochs,
        batch_size=batch_size,
        grad_accum=grad_accum,
        lr=lr,
        warmup_ratio=warmup_ratio,
        max_length=max_length,
        limit=limit,
        precision=precision,
        dataloader_workers=dataloader_workers,
        gradient_checkpointing=gradient_checkpointing,
    )
    train_uai_qlora(config)


@model_app.command("status")
def model_status_command(
    host: Optional[str] = typer.Option(None, help="Override the configured host."),
    port: Optional[int] = typer.Option(None, help="Override the configured port."),
) -> None:
    """Show the active trained UAI run and whether a running service has loaded it."""
    from obiai.training.model_cli import model_status

    model_status(host=host, port=port)


@model_app.command("reload")
def model_reload_command(
    host: Optional[str] = typer.Option(None, help="Override the configured host."),
    port: Optional[int] = typer.Option(None, help="Override the configured port."),
) -> None:
    """Ask the running service to reload the active trained UAI model."""
    from obiai.training.model_cli import model_reload

    model_reload(host=host, port=port)


if __name__ == "__main__":
    app()
