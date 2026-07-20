"""QLoRA fine-tuning entrypoint for UAI.

The heavy ML dependencies are imported only when training starts so ordinary
CLI commands such as ``obiai demo`` and ``uai serve`` remain lightweight.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

DEFAULT_BASE_MODEL = "EleutherAI/pythia-2.8b"
DEFAULT_OUTPUT_NAME = "pythia-2.8b-oasst2-qlora"
DEFAULT_DATA_NAME = "sft_pairs_weighted.jsonl"
MAX_LENGTH = 1024


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


def default_output_path() -> Path:
    return default_ml_dir() / "checkpoints" / DEFAULT_OUTPUT_NAME


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


def build_model_and_tokenizer(base_model: str, stack: dict[str, Any]) -> tuple[Any, Any]:
    torch = stack["torch"]
    bnb_config = stack["BitsAndBytesConfig"](
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = stack["AutoTokenizer"].from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = stack["AutoModelForCausalLM"].from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model = stack["prepare_model_for_kbit_training"](
        model, use_gradient_checkpointing=True
    )

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


def train_uai_qlora(config: UAITrainingConfig) -> None:
    data = config.data or default_data_path()
    output = config.output or default_output_path()

    if not data.exists():
        raise SystemExit(
            f"{data} not found - run ml/scripts/prepare_data.py then "
            "ml/scripts/bias_audit.py first, or pass --data pointing at "
            "sft_pairs.jsonl for unweighted training."
        )

    stack = _load_training_stack()
    torch = stack["torch"]
    model, tokenizer = build_model_and_tokenizer(config.base_model, stack)

    dataset = stack["load_dataset"]("json", data_files=str(data), split="train")
    if config.limit:
        dataset = dataset.select(range(min(config.limit, len(dataset))))
    dataset = dataset.map(
        lambda ex: tokenize_example(ex, tokenizer, config.max_length),
        remove_columns=dataset.column_names,
    )

    collator = WeightedDataCollator(tokenizer, torch)
    training_args = stack["TrainingArguments"](
        output_dir=str(output),
        per_device_train_batch_size=config.batch_size,
        gradient_accumulation_steps=config.grad_accum,
        num_train_epochs=config.epochs,
        max_steps=config.max_steps,
        learning_rate=config.lr,
        warmup_ratio=config.warmup_ratio,
        bf16=True,
        logging_steps=5,
        save_strategy="epoch" if config.max_steps == -1 else "no",
        report_to=[],
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        remove_unused_columns=False,
    )

    trainer_cls = _weighted_trainer_class(stack["Trainer"], torch)
    trainer = trainer_cls(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collator,
    )
    trainer.train()

    output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output))
    tokenizer.save_pretrained(str(output))
    print(f"LoRA adapter saved to {output}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--max-steps", type=int, default=-1, help="-1 = train --epochs instead.")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--max-length", type=int, default=MAX_LENGTH)
    parser.add_argument("--limit", type=int, default=None, help="Use only the first N examples.")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    train_uai_qlora(
        UAITrainingConfig(
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
        )
    )

