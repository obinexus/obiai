"""QLoRA fine-tuning entrypoint for UAI.

The heavy ML dependencies are imported only when training starts so ordinary
CLI commands such as ``obiai demo`` and ``uai serve`` remain lightweight.

Every successful run is registered in the trusted artifact manifest under
``artifacts/uai`` (see :mod:`obiai.training.artifacts`) so the chat runtime
can find and load it automatically -- see :mod:`obiai.training.runtime`.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from obiai.training.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    CurrentManifest,
    UAIModelArtifact,
    default_artifact_root,
    run_dir,
    write_artifact_descriptor,
    write_current,
)

DEFAULT_BASE_MODEL = "EleutherAI/pythia-2.8b"
DEFAULT_OUTPUT_NAME = "pythia-2.8b-oasst2-qlora"
DEFAULT_DATA_NAME = "sft_pairs_weighted.jsonl"
MAX_LENGTH = 1024
PRECISION_CHOICES = ("auto", "bf16", "fp16", "fp32")

# The template every prompt is wrapped in, both for training examples and at
# generation time (see obiai.training.runtime) -- it must match on both sides.
CHAT_TEMPLATE = "### Human: {prompt}\n\n### Assistant: "

# Fast development profile (see ``obiai train uai --fast``): the smallest
# stable configuration that still exercises the real training path.
FAST_LIMIT = 128
FAST_MAX_STEPS = 8
FAST_GRAD_ACCUM = 1
FAST_BATCH_SIZE = 1
FAST_MAX_LENGTH = 256


@dataclass(frozen=True)
class UAITrainingConfig:
    base_model: str = DEFAULT_BASE_MODEL
    data: Path | None = None
    output: Path | None = None
    max_steps: int = -1
    epochs: float = 1.0
    batch_size: int = 1
    grad_accum: int = 16
    lr: float = 2e-4
    warmup_ratio: float = 0.03
    max_length: int = MAX_LENGTH
    limit: int | None = None
    precision: str = "auto"
    dataloader_workers: int = 0
    gradient_checkpointing: bool = True
    logging_steps: int = 5
    fast: bool = False


@dataclass(frozen=True)
class TrainingRuntime:
    precision: str
    compute_dtype: Any
    bf16: bool
    fp16: bool
    use_cpu: bool
    optim: str
    quantize: bool


def default_ml_dir() -> Path:
    """Find the repository's ``ml`` directory from common invocation paths."""
    env_dir = os.getenv("OBIAI_ML_DIR")
    if env_dir:
        return Path(env_dir).expanduser()

    cwd = Path.cwd()
    if (cwd / "data" / "oasst2").exists() or (cwd / "scripts" / "train_qlora.py").exists():
        return cwd
    if (cwd / "ml").exists():
        return cwd / "ml"

    return Path(__file__).resolve().parents[3] / "ml"


def default_data_path() -> Path:
    return default_ml_dir() / "data" / "oasst2" / DEFAULT_DATA_NAME


def default_fast_data_path() -> Path:
    """The small OBIAI/OBINexus-focused dataset used by ``--fast``.

    Deliberately not the general-purpose OASST2 chat corpus: the fast
    profile exists to exercise and sanity-check UAI's own terminology,
    identity, and transcript-handling behaviour, not to teach it to make
    mayonnaise.
    """
    return default_ml_dir() / "data" / "uai" / "uai_fast_pairs.jsonl"


def default_output_path() -> Path:
    return default_ml_dir() / "checkpoints" / DEFAULT_OUTPUT_NAME


def resolve_uai_training_config(
    *,
    fast: bool = False,
    base_model: str | None = None,
    data: Path | None = None,
    output: Path | None = None,
    max_steps: int | None = None,
    epochs: float | None = None,
    batch_size: int | None = None,
    grad_accum: int | None = None,
    lr: float | None = None,
    warmup_ratio: float | None = None,
    max_length: int | None = None,
    limit: int | None = None,
    precision: str = "auto",
    dataloader_workers: int | None = None,
    gradient_checkpointing: bool | None = None,
) -> UAITrainingConfig:
    """Build a training config, layering explicit overrides onto a profile.

    ``--fast`` selects the smallest stable defaults for a dev-loop smoke
    run; any option the caller passed explicitly always wins over both
    profiles.
    """
    if fast:
        base = UAITrainingConfig(
            data=default_fast_data_path(),
            max_steps=FAST_MAX_STEPS,
            epochs=1.0,
            batch_size=FAST_BATCH_SIZE,
            grad_accum=FAST_GRAD_ACCUM,
            warmup_ratio=0.0,
            max_length=FAST_MAX_LENGTH,
            limit=FAST_LIMIT,
            precision=precision,
            dataloader_workers=0,
            gradient_checkpointing=False,
            logging_steps=FAST_MAX_STEPS,
            fast=True,
        )
    else:
        base = UAITrainingConfig(precision=precision, fast=False)

    overrides: dict[str, Any] = {
        "base_model": base_model,
        "data": data,
        "output": output,
        "max_steps": max_steps,
        "epochs": epochs,
        "batch_size": batch_size,
        "grad_accum": grad_accum,
        "lr": lr,
        "warmup_ratio": warmup_ratio,
        "max_length": max_length,
        "limit": limit,
        "dataloader_workers": dataloader_workers,
        "gradient_checkpointing": gradient_checkpointing,
    }
    changes = {key: value for key, value in overrides.items() if value is not None}
    return dataclasses.replace(base, **changes) if changes else base


def _load_training_stack() -> dict[str, Any]:
    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        missing = exc.name or str(exc)
        raise RuntimeError(
            f"Missing UAI training dependency: {missing}. "
            'Install the training extras with: pip install -e ".[train]"'
        ) from exc

    return {
        "torch": torch,
        "load_dataset": load_dataset,
        "LoraConfig": LoraConfig,
        "get_peft_model": get_peft_model,
        "prepare_model_for_kbit_training": prepare_model_for_kbit_training,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
        "BitsAndBytesConfig": BitsAndBytesConfig,
        "Trainer": Trainer,
        "TrainingArguments": TrainingArguments,
    }


def _cuda_available(torch_module: Any) -> bool:
    return bool(getattr(torch_module, "cuda", None) and torch_module.cuda.is_available())


def _cuda_supports_bf16(torch_module: Any) -> bool:
    cuda = getattr(torch_module, "cuda", None)
    is_supported = getattr(cuda, "is_bf16_supported", None)
    return bool(_cuda_available(torch_module) and callable(is_supported) and is_supported())


def resolve_training_runtime(torch_module: Any, requested_precision: str) -> TrainingRuntime:
    precision = requested_precision.lower()
    if precision not in PRECISION_CHOICES:
        choices = ", ".join(PRECISION_CHOICES)
        raise SystemExit(f"Unsupported precision {requested_precision!r}; choose one of: {choices}.")

    has_cuda = _cuda_available(torch_module)
    if precision == "auto":
        if _cuda_supports_bf16(torch_module):
            precision = "bf16"
        elif has_cuda:
            precision = "fp16"
        else:
            precision = "fp32"

    if precision == "bf16" and not _cuda_supports_bf16(torch_module):
        raise SystemExit(
            "BF16 training is not supported by this runtime. "
            "Use --precision auto or --precision fp16 on older CUDA GPUs."
        )
    if precision == "fp16" and not has_cuda:
        raise SystemExit("FP16 training requires CUDA. Use --precision fp32 for CPU training.")

    compute_dtype = {
        "bf16": torch_module.bfloat16,
        "fp16": torch_module.float16,
        "fp32": torch_module.float32,
    }[precision]
    return TrainingRuntime(
        precision=precision,
        compute_dtype=compute_dtype,
        bf16=precision == "bf16",
        fp16=precision == "fp16",
        use_cpu=not has_cuda,
        optim="paged_adamw_8bit" if has_cuda else "adamw_torch",
        # bitsandbytes 4-bit quantization needs a CUDA kernel; on CPU it
        # silently produces broken (non-converging) gradients rather than
        # a clean error, so QLoRA-style 4-bit quantization is CUDA-only
        # here and CPU runs train the adapter over a plain fp32/bf16 base
        # model instead.
        quantize=has_cuda,
    )


def build_model_and_tokenizer(
    base_model: str,
    stack: dict[str, Any],
    runtime: TrainingRuntime,
    *,
    use_gradient_checkpointing: bool = True,
) -> tuple[Any, Any]:
    tokenizer = stack["AutoTokenizer"].from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if runtime.quantize:
        bnb_config = stack["BitsAndBytesConfig"](
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=runtime.compute_dtype,
            bnb_4bit_use_double_quant=True,
        )
        model = stack["AutoModelForCausalLM"].from_pretrained(
            base_model,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=runtime.compute_dtype,
        )
        model = stack["prepare_model_for_kbit_training"](
            model, use_gradient_checkpointing=use_gradient_checkpointing
        )
    else:
        model = stack["AutoModelForCausalLM"].from_pretrained(
            base_model, torch_dtype=runtime.compute_dtype
        )
        if use_gradient_checkpointing:
            model.gradient_checkpointing_enable()
            model.enable_input_require_grads()

    lora_config = stack["LoraConfig"](
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        # GPT-NeoX (Pythia) attention/MLP projection module names.
        target_modules=["query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h"],
    )
    model = stack["get_peft_model"](model, lora_config)
    model.print_trainable_parameters()
    return model, tokenizer


def tokenize_example(example: dict[str, Any], tokenizer: Any, max_length: int) -> dict[str, Any]:
    prompt_ids = tokenizer(example["prompt"], add_special_tokens=False)["input_ids"]
    completion_ids = tokenizer(example["completion"], add_special_tokens=False)["input_ids"]

    input_ids = (prompt_ids + completion_ids)[:max_length]
    # Mask the prompt from the loss: only the completion should be predicted.
    labels = ([-100] * len(prompt_ids) + completion_ids)[:max_length]
    return {
        "input_ids": input_ids,
        "labels": labels,
        "attention_mask": [1] * len(input_ids),
        "weight": example.get("weight", 1.0),
    }


class WeightedDataCollator:
    """Pad model inputs and stack debiased per-example weights."""

    def __init__(self, tokenizer: Any, torch_module: Any):
        self.tokenizer = tokenizer
        self.torch = torch_module

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        weights = self.torch.tensor(
            [f.pop("weight") for f in features], dtype=self.torch.float32
        )
        max_len = max(len(f["input_ids"]) for f in features)
        pad_id = self.tokenizer.pad_token_id

        input_ids, labels, attention_mask = [], [], []
        for feature in features:
            pad_len = max_len - len(feature["input_ids"])
            input_ids.append(feature["input_ids"] + [pad_id] * pad_len)
            labels.append(feature["labels"] + [-100] * pad_len)
            attention_mask.append(feature["attention_mask"] + [0] * pad_len)

        return {
            "input_ids": self.torch.tensor(input_ids, dtype=self.torch.long),
            "labels": self.torch.tensor(labels, dtype=self.torch.long),
            "attention_mask": self.torch.tensor(attention_mask, dtype=self.torch.long),
            "weight": weights,
        }


def _weighted_trainer_class(trainer_base: type, torch_module: Any) -> type:
    class WeightedTrainer(trainer_base):
        """Scale per-example loss by the debiased training weight."""

        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            weights = inputs.pop("weight")
            outputs = model(**inputs)
            logits = outputs.logits
            labels = inputs["labels"]

            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss_fct = torch_module.nn.CrossEntropyLoss(
                reduction="none", ignore_index=-100
            )
            per_token_loss = loss_fct(
                shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1)
            ).view(shift_labels.size())

            mask = (shift_labels != -100).float()
            per_example_loss = (per_token_loss * mask).sum(dim=1) / mask.sum(
                dim=1
            ).clamp(min=1)
            loss = (per_example_loss * weights.to(per_example_loss.device)).mean()
            return (loss, outputs) if return_outputs else loss

    return WeightedTrainer


def estimate_training_steps(
    dataset_size: int, batch_size: int, grad_accum: int, epochs: float, max_steps: int
) -> int:
    if max_steps > 0:
        return max_steps
    effective_batch = max(1, batch_size) * max(1, grad_accum)
    steps_per_epoch = math.ceil(dataset_size / effective_batch)
    return max(1, math.ceil(steps_per_epoch * epochs))


def _new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def _validate_run_artifact(
    adapter_dir: Path, tokenizer_dir: Path, stack: dict[str, Any]
) -> tuple[bool, bool]:
    """Cheap, local-only validation: no base model or network access needed."""
    adapter_ok = (adapter_dir / "adapter_config.json").is_file() and any(
        adapter_dir.glob("adapter_model.*")
    )
    tokenizer_ok = False
    if adapter_ok:
        try:
            stack["AutoTokenizer"].from_pretrained(str(tokenizer_dir))
            tokenizer_ok = True
        except Exception:  # noqa: BLE001 - validation reports, does not raise
            tokenizer_ok = False
    return adapter_ok, tokenizer_ok


def train_uai_qlora(config: UAITrainingConfig) -> None:
    data = config.data or default_data_path()
    artifact_root = default_artifact_root()

    if not data.exists():
        raise SystemExit(
            f"{data} not found - run ml/scripts/prepare_data.py then "
            "ml/scripts/bias_audit.py first, or pass --data pointing at "
            "sft_pairs.jsonl for unweighted training."
        )

    stack = _load_training_stack()
    torch = stack["torch"]
    runtime = resolve_training_runtime(torch, config.precision)
    print(
        f"Training precision: {runtime.precision}; "
        f"use_cpu={runtime.use_cpu}; optimizer={runtime.optim}; "
        f"quantize={runtime.quantize}"
    )
    model, tokenizer = build_model_and_tokenizer(
        config.base_model, stack, runtime, use_gradient_checkpointing=config.gradient_checkpointing
    )

    dataset = stack["load_dataset"]("json", data_files=str(data), split="train")
    if config.limit:
        dataset = dataset.select(range(min(config.limit, len(dataset))))
    dataset = dataset.map(
        lambda ex: tokenize_example(ex, tokenizer, config.max_length),
        remove_columns=dataset.column_names,
    )

    collator = WeightedDataCollator(tokenizer, torch)
    total_steps = estimate_training_steps(
        len(dataset), config.batch_size, config.grad_accum, config.epochs, config.max_steps
    )
    warmup_steps = math.ceil(total_steps * config.warmup_ratio)

    run_id = _new_run_id()
    run_output = config.output or run_dir(artifact_root, run_id)

    training_args = stack["TrainingArguments"](
        output_dir=str(run_output),
        per_device_train_batch_size=config.batch_size,
        gradient_accumulation_steps=config.grad_accum,
        num_train_epochs=config.epochs,
        max_steps=config.max_steps,
        learning_rate=config.lr,
        warmup_steps=warmup_steps,
        bf16=runtime.bf16,
        fp16=runtime.fp16,
        use_cpu=runtime.use_cpu,
        logging_steps=max(1, config.logging_steps),
        # The trainer never writes its own mid-run checkpoints; the final
        # adapter/tokenizer are saved explicitly below and registered in the
        # artifact manifest instead.
        save_strategy="no",
        report_to=[],
        gradient_checkpointing=config.gradient_checkpointing,
        optim=runtime.optim,
        dataloader_num_workers=config.dataloader_workers,
        remove_unused_columns=False,
    )

    trainer_cls = _weighted_trainer_class(stack["Trainer"], torch)
    trainer = trainer_cls(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collator,
    )
    started = time.perf_counter()
    trainer.train()
    elapsed_seconds = time.perf_counter() - started

    adapter_dir = run_output / "adapter" if config.output is None else run_output
    tokenizer_dir = run_output / "tokenizer" if config.output is None else run_output
    adapter_dir.mkdir(parents=True, exist_ok=True)
    tokenizer_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(tokenizer_dir))
    print(f"LoRA adapter saved to {adapter_dir}")

    if config.output is not None:
        # Explicit --output bypasses the artifact manifest entirely: this is
        # the legacy/manual path for scripts that manage their own location.
        print("--output was set explicitly; skipping artifact manifest registration.")
        return

    final_loss = None
    for entry in reversed(trainer.state.log_history):
        if "loss" in entry:
            final_loss = entry["loss"]
            break

    training_config_path = run_output / "training_config.json"
    training_config_path.write_text(
        json.dumps(
            {**dataclasses.asdict(config), "data": str(data), "output": None, "run_id": run_id},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    metrics_path = run_output / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "final_loss": final_loss,
                "global_step": trainer.state.global_step,
                "train_runtime_seconds": elapsed_seconds,
                "log_history": trainer.state.log_history,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    adapter_ok, tokenizer_ok = _validate_run_artifact(adapter_dir, tokenizer_dir, stack)
    manifest_updated = False
    if adapter_ok and tokenizer_ok:
        descriptor = UAIModelArtifact(
            schema_version=ARTIFACT_SCHEMA_VERSION,
            base_model=config.base_model,
            adapter_path=str(adapter_dir.relative_to(artifact_root)),
            tokenizer_path=str(tokenizer_dir.relative_to(artifact_root)),
            training_config_path=str(training_config_path.relative_to(artifact_root)),
            run_id=run_id,
        )
        descriptor_path = run_output / "model.pkl"
        write_artifact_descriptor(descriptor_path, descriptor, artifact_root=artifact_root)
        write_current(
            CurrentManifest(
                run_id=run_id,
                model_path=str(descriptor_path.relative_to(artifact_root)),
                adapter_path=descriptor.adapter_path,
                tokenizer_path=descriptor.tokenizer_path,
                status="ready",
            ),
            artifact_root=artifact_root,
        )
        manifest_updated = True

    try:
        from obiai.core.config import load_settings

        server = load_settings().u.server
        restart_required = _port_in_use(server.host, server.port)
    except OSError:
        restart_required = False

    print()
    print("Training completed." if adapter_ok and tokenizer_ok else "Training completed with validation failures.")
    print(f"Run ID: {run_id}")
    print(f"Active artifact: {run_output}")
    print(f"Adapter validated: {'yes' if adapter_ok else 'no'}")
    print(f"Tokenizer validated: {'yes' if tokenizer_ok else 'no'}")
    print(f"Runtime manifest updated: {'yes' if manifest_updated else 'no'}")
    print(f"Restart required: {'yes' if restart_required else 'no'}")
    if final_loss is not None:
        print(f"Final training loss: {final_loss:.4f}")
    if not manifest_updated:
        raise SystemExit(
            "Artifact validation failed; current.json was left untouched so "
            "the runtime keeps using the last known-good model."
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast dev profile: tiny OBIAI/OBINexus dataset slice, 8 steps, no mid-run checkpoints.",
    )
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--max-steps", type=int, default=None, help="-1 = train --epochs instead.")
    parser.add_argument("--epochs", type=float, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--grad-accum", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--warmup-ratio", type=float, default=None)
    parser.add_argument("--max-length", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None, help="Use only the first N examples.")
    parser.add_argument(
        "--precision",
        choices=PRECISION_CHOICES,
        default="auto",
        help="Training precision: auto selects bf16, fp16, or fp32 for this runtime.",
    )
    parser.add_argument("--dataloader-workers", type=int, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    train_uai_qlora(
        resolve_uai_training_config(
            fast=args.fast,
            base_model=args.base_model,
            data=args.data,
            output=args.output,
            max_steps=args.max_steps,
            epochs=args.epochs,
            batch_size=args.batch_size,
            grad_accum=args.grad_accum,
            lr=args.lr,
            warmup_ratio=args.warmup_ratio,
            max_length=args.max_length,
            limit=args.limit,
            precision=args.precision,
            dataloader_workers=args.dataloader_workers,
        )
    )
