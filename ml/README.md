# ml — OASST2 archive + QLoRA fine-tuning

A separate, isolated area for downloading the OASST2 dataset and fine-tuning
a small causal LM on it. Deliberately kept out of `src/obiai` — the U agent's
dependency tree stays lightweight (NumPy/SciPy/FastAPI, no PyTorch), matching
the rest of this repo's "no heavy ML deps in the core package" policy. This
directory is standalone, like `poc/bayesian_debiasing`, with its own venv.

## Why not the original ask (pythia-12b)?

`OpenAssistant/pythia-12b-sft-v8-rlhf-2k-steps` is a 12-billion-parameter
model. This machine has an **RTX 4060 Laptop GPU with 8GB VRAM**:

- Full fine-tuning needs ~12B × 12 bytes (fp16 weights + grads + AdamW
  state) ≈ **144GB VRAM**.
- Even 4-bit QLoRA is too tight: the quantized weights alone are ~6–7GB,
  leaving almost nothing for activations, gradients, or the optimizer.

So training targets **`EleutherAI/pythia-2.8b`** instead (same architecture
family as the OpenAssistant Pythia checkpoints, sized to actually fit in 8GB
via QLoRA). `pythia-1.4b` is a documented fallback if 2.8b still OOMs on this
machine once other GPU memory (browser, VCam, etc.) is accounted for. The
dataset and pipeline are unchanged — only the base model size is scoped to
the hardware.

## Setup

```powershell
cd ml
python -m venv .venv
.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
```

## 1. Archive the dataset

```bash
python scripts/download_dataset.py
```

Downloads the two "ready for export" OASST2 archive files (via
`huggingface_hub`, which handles the LFS/redirect flow correctly — a plain
`curl` against the resolve URL returns an S3 `AccessDenied` error) into
`data/oasst2/`:

- `2023-11-05_oasst2_ready.trees.jsonl.gz` — 13,854 message trees
- `2023-11-05_oasst2_ready.messages.jsonl.gz` — 135,174 flat messages

Neither file is committed to git (`data/` is gitignored) — this is a local
archive, not a repo asset.

## 2. Build SFT pairs

```bash
python scripts/prepare_data.py            # English only by default
python scripts/prepare_data.py --lang all # keep every language
```

Walks each `ready_for_export` tree and emits one `{prompt, completion}` pair
per non-deleted assistant message, using the conversation path from the root
to that message as context. Light quality filtering drops messages flagged
spam/not-appropriate above 0.5. Output: `data/oasst2/sft_pairs.jsonl`.

## 3. Train

```bash
# Smoke test first — a handful of steps, proves the pipeline runs without OOM.
python scripts/train_qlora.py --limit 32 --max-steps 5

# A real (short) run:
python scripts/train_qlora.py --epochs 1
```

4-bit NF4 quantized base weights (bitsandbytes) + LoRA adapters on the
attention/MLP projections (`peft`), gradient checkpointing, batch size 1 with
16-step gradient accumulation, 8-bit paged AdamW. Only the adapter is saved
(tens of MB), not a full model copy — to `checkpoints/pythia-2.8b-oasst2-qlora/`
by default (gitignored).

Key flags: `--base-model` (swap in `pythia-1.4b` if this OOMs),
`--batch-size`/`--grad-accum` (trade memory for step time), `--max-length`
(context window cap, default 1024).

## 4. Try it

```bash
python scripts/infer.py --prompt "What is a Bayesian network?"
```

## Relationship to the U agent

None, architecturally. This is a general-purpose SFT pipeline for a Pythia
model; the `obiai` U agent's reasoning stays exact/symbolic (Bayesian
networks, epistemic DAG, bias/safety audits — see the top-level
[README.md](../README.md) and [docs/traceability.md](../docs/traceability.md)).
If a trained model here were ever wired into U as a chat backend, that would
be a new, explicit integration point (e.g. behind a provider protocol,
matching how `SpeechToTextProvider`/`TextToSpeechProvider` are designed as
swappable interfaces) — not implemented here.
