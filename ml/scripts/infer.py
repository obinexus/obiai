"""Load a trained QLoRA adapter and generate a response to a prompt.

Usage:
    python scripts/infer.py --adapter checkpoints/pythia-2.8b-oasst2-qlora --prompt "What is a Bayesian network?"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

ML_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ADAPTER = ML_DIR / "checkpoints" / "pythia-2.8b-oasst2-qlora"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default="EleutherAI/pythia-2.8b")
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=200)
    args = parser.parse_args()

    if not args.adapter.exists():
        raise SystemExit(f"{args.adapter} not found — run scripts/train_qlora.py first.")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(str(args.adapter))
    base = AutoModelForCausalLM.from_pretrained(
        args.base_model, quantization_config=bnb_config, device_map="auto", torch_dtype=torch.bfloat16
    )
    model = PeftModel.from_pretrained(base, str(args.adapter))
    model.eval()

    text = f"### Human: {args.prompt}\n\n### Assistant: "
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = tokenizer.decode(output[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
    print(generated.strip())


if __name__ == "__main__":
    main()
