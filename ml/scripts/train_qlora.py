"""QLoRA fine-tune a small causal LM on the OASST2 SFT pairs.

Sized for an 8GB-VRAM laptop GPU: 4-bit NF4 base weights (bitsandbytes),
LoRA adapters on the attention/MLP projections, gradient checkpointing,
batch size 1 with gradient accumulation. Default base model is
EleutherAI/pythia-2.8b (same architecture family as the OpenAssistant Pythia
checkpoints, sized to actually fit); pass --base-model to use a different one
(pythia-1.4b is a safe fallback if this OOMs).

Only the LoRA adapter is saved — a few tens of MB, not a full model copy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
)

ML_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ML_DIR / "data" / "oasst2" / "sft_pairs.jsonl"
DEFAULT_OUTPUT = ML_DIR / "checkpoints" / "pythia-2.8b-oasst2-qlora"

MAX_LENGTH = 1024


def build_model_and_tokenizer(base_model: str):
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        # GPT-NeoX (Pythia) attention/MLP projection module names.
        target_modules=["query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model, tokenizer


def tokenize_example(example: dict, tokenizer, max_length: int) -> dict:
    prompt_ids = tokenizer(example["prompt"], add_special_tokens=False)["input_ids"]
    completion_ids = tokenizer(example["completion"], add_special_tokens=False)["input_ids"]

    input_ids = (prompt_ids + completion_ids)[:max_length]
    # Mask the prompt from the loss — only the completion should be predicted.
    labels = ([-100] * len(prompt_ids) + completion_ids)[:max_length]
    return {"input_ids": input_ids, "labels": labels, "attention_mask": [1] * len(input_ids)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default="EleutherAI/pythia-2.8b")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-steps", type=int, default=-1, help="-1 = train --epochs instead.")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--max-length", type=int, default=MAX_LENGTH)
    parser.add_argument("--limit", type=int, default=None, help="Use only the first N examples (smoke tests).")
    args = parser.parse_args()

    if not args.data.exists():
        raise SystemExit(f"{args.data} not found — run scripts/prepare_data.py first.")

    model, tokenizer = build_model_and_tokenizer(args.base_model)

    dataset = load_dataset("json", data_files=str(args.data), split="train")
    if args.limit:
        dataset = dataset.select(range(min(args.limit, len(dataset))))
    dataset = dataset.map(
        lambda ex: tokenize_example(ex, tokenizer, args.max_length),
        remove_columns=dataset.column_names,
    )

    collator = DataCollatorForSeq2Seq(
        tokenizer, model=model, padding=True, label_pad_token_id=-100
    )

    training_args = TrainingArguments(
        output_dir=str(args.output),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        learning_rate=args.lr,
        bf16=True,
        logging_steps=5,
        save_strategy="epoch" if args.max_steps == -1 else "no",
        report_to=[],
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collator,
    )
    trainer.train()

    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(args.output))
    tokenizer.save_pretrained(str(args.output))
    print(f"LoRA adapter saved to {args.output}")


if __name__ == "__main__":
    main()
