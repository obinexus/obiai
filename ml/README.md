# ml — OASST2 archive + bias-audited QLoRA fine-tuning

A separate, isolated area for downloading the OASST2 dataset and fine-tuning
a small causal LM on it, using the debiasing method from the *Unbiased AI*
papers. Deliberately kept out of `src/obiai` — the U agent's dependency tree
stays lightweight (NumPy/SciPy/FastAPI, no PyTorch). This directory is
standalone, like `poc/bayesian_debiasing`, with its own venv — but reuses
`obiai.bayes`/`obiai.bayesian` (installed editable, no torch pulled in by
that package) so the debiasing math is the exact, already-tested code from
the U agent, not a reimplementation.

**Status: pipeline verified end-to-end on this machine** (download → prepare
→ bias-audit → train → infer), with a short smoke-test run. Full training is
not yet run — see "Running a real training job" below.

## Why not the original ask (pythia-12b)?

`OpenAssistant/pythia-12b-sft-v8-rlhf-2k-steps` is a 12-billion-parameter
model. This machine has an **RTX 4060 Laptop GPU with 8GB VRAM** (~7.4GB
free in practice):

- Full fine-tuning needs ~12B × 12 bytes (fp16 weights + grads + AdamW
  state) ≈ **144GB VRAM**.
- Even 4-bit QLoRA is too tight: the quantized weights alone are ~6–7GB,
  leaving almost nothing for activations, gradients, or the optimizer.

Training targets **`EleutherAI/pythia-2.8b`** instead (same architecture
family as the OpenAssistant Pythia checkpoints, sized to actually fit in 8GB
via QLoRA — confirmed: 2.8B params, 4-bit NF4 base + LoRA adapters, 8.6s/step
on this GPU). `pythia-1.4b` is a documented fallback via `--base-model` if
2.8b OOMs once other GPU memory is in use.

## What "the method discussed" means here, concretely

Several *Unbiased AI* / OBINexus documents were provided across this
session. Per this project's standing rule (mark every claim as a formal
definition, hypothesis, or unsupported claim — never treat speculation as
proven), here is what was actually implementable and what was not:

| Source | What it is | Used here? |
|---|---|---|
| *Formal Argument for Bias in AI Systems* (May 2025) — §5 factorization `P(T\|S,C,A) = P(T\|C,S)·P′(A)`, §6 marginalization `P(θ\|D) = ∫P(θ,φ\|D)dφ` | Formal definition (valid Bayes-rule derivation) | **Yes** — `scripts/bias_audit.py` |
| *A Bayesian Network Framework for Mitigating Bias* (June 2026) — Algorithm 1 (MCMC: Metropolis-Hastings for θ, Gibbs for φ) | Design proposal | Adapted, not literal — exact discrete marginalization instead of MCMC (same substitution already made and justified in `../docs/traceability.md` for the U agent: the θ/φ spaces here are small and discrete, so exact computation is both simpler and exact rather than approximate) |
| Same paper, §7 experimental numbers ("35% → 5% misdiagnosis", "85% improvement") | **Unsupported claim** — no code, no dataset, no experiment shown in the source | **Not used.** This pipeline instead reports its *own* measured, honestly-computed demographic-parity numbers on the real OASST2 data (see below) |
| Same paper, §8 "Consciousness State Monitor" / `AuthenticationManager` pseudocode | Unrelated boilerplate (security/auth scaffolding, not a bias-mitigation technique) | Not used — has nothing to do with training or bias |
| *The Actor Class* (patent-spec, 2025) — category-theoretic "Actors", `ε ≥ 0.954` confidence threshold, "Turing-complete epistemic autonomy" | **Unsupported claim / speculative formalism** — proofs assert results without rigorous derivation (e.g. "The proof follows from functor composition preserving limits and colimits" is asserted, not shown); no concrete, implementable algorithm | **Not used** — nothing here is an algorithm that can be coded against |

### The concrete translation: `scripts/bias_audit.py`

The paper's `S, C, T, A` (legitimate risk factors, confounders, target,
protected attribute) map onto OASST2 fields:

- **A** — protected-attribute mention, via keyword lexicon over the same
  four categories `obiai.core.config.BiasSettings` already uses (age_group,
  disability, ethnicity, gender). Crude by construction — this is a
  heuristic proxy, not a validated classifier, and is documented as such in
  the script.
- **C** — a quality confound from OASST2's own reviewer labels
  (`not_appropriate` / `spam` ≥ 0.3), independent of A.
- **T** — "trustworthy training signal" (`toxicity` and `hate_speech` both
  below 0.3).

Two `obiai.bayes.BayesianNetwork` instances estimate `P(T=1|C)` — one from
the whole corpus ("raw", the traditional-MLE estimate that can be skewed by
whichever examples happen to mention protected attributes) and one from only
the A=0 examples ("corrected", insulated from that skew). `obiai.bayesian.
PhiMarginalizedNetwork` mixes them with a fixed prior favoring the corrected
estimate (0.9 vs 0.1) — the same class already proven exact in
`../tests/test_marginal.py`. Every SFT example gets a debiased weight
`w_i = P(T=1|C=c_i)`, independent of A by construction. This is a fixed
prior-weighted blend of two estimators, not a per-query Bayesian update on
A — see the docstring in `bias_audit.py` for why (the network structure
never conditions on A at query time, only at CPT-estimation time).

**Measured result on the real dataset** (37,881 examples, 3,952 with a
protected-attribute mention): demographic-parity gap 0.00174 → 0.00170 —
essentially unchanged. Read plainly: by this crude proxy, protected-attribute
mentions in OASST2 assistant responses are not meaningfully correlated with
the reviewers' own toxicity/spam flags, so there isn't much bias for this
mechanism to remove. That is a genuine, unembellished measurement, not a
cherry-picked one — contrast with the source paper's unvalidated "35%→5%"
claim, which this pipeline deliberately does not reproduce.

## Setup

```powershell
cd ml
python -m venv .venv
.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
pip install -e ..   # obiai-u editable, for obiai.bayes / obiai.bayesian
```

## 1. Archive the dataset

```bash
python scripts/download_dataset.py
```

Downloads the two "ready for export" OASST2 archive files into
`data/oasst2/` via `huggingface_hub` + `hf_xet` (the dataset's files are
Xet-backed, not plain LFS — **`hf_xet` is required**; without it every
download returns an S3 `AccessDenied` error, which is what a plain `curl`
against the resolve URL also hits):

- `2023-11-05_oasst2_ready.trees.jsonl.gz` — 13,854 message trees (~52MB)
- `2023-11-05_oasst2_ready.messages.jsonl.gz` — 135,174 flat messages (~52MB)

Neither file is committed to git (`data/` is gitignored) — local archive,
not a repo asset.

## 2. Build SFT pairs

```bash
python scripts/prepare_data.py            # English only by default
```

Walks each `ready_for_export` tree, emits one `{prompt, completion,
message_id, labels}` pair per non-deleted assistant message (conversation
path from root to that message as context, review labels carried through for
the next step). **Verified: 13,854 trees → 37,881 examples.** Output:
`data/oasst2/sft_pairs.jsonl`.

## 3. Bias audit → debiased weights

```bash
python scripts/bias_audit.py
```

See above. Output: `data/oasst2/sft_pairs_weighted.jsonl` (each example plus
a `weight` field) and `data/oasst2/bias_audit_report.json` (the measured
parity-gap numbers).

## 4. Train

```bash
# Smoke test first — proves the pipeline runs without OOM.
python scripts/train_qlora.py --limit 128 --max-steps 8 --grad-accum 4

# A real (short) run:
python scripts/train_qlora.py --epochs 1
```

**Confirmed working on this machine**: 2.8B params, 20.9M trainable
(0.75%, LoRA r=16), 4-bit NF4 + bf16 compute, gradient checkpointing,
`paged_adamw_8bit`, ~8.6s/step at batch size 1. `WeightedTrainer` (a small
`Trainer` subclass) applies each example's bias-audit weight to its
per-example mean loss before averaging across the batch — the training-time
counterpart of the paper's `P(T|C,S)`. Only the LoRA adapter is saved (tens
of MB), to `checkpoints/pythia-2.8b-oasst2-qlora/` by default (gitignored).

Key flags: `--base-model` (swap in `pythia-1.4b` if 2.8b OOMs),
`--batch-size`/`--grad-accum` (trade memory for step time), `--max-length`
(context cap, default 1024), `--warmup-ratio` (default 0.03 — needed; a
smoke test without warmup showed loss spike to ~29 on cold-start full-LR
AdamW, confirmed via a separate manual loss check to be optimizer
instability, not a bug in the weighted-loss computation — see git history
for the diagnostic), `--data` (point at plain `sft_pairs.jsonl` for
unweighted training).

### Running a real training job

A full epoch over 37,881 examples at ~8.6s/step (batch 1, grad-accum 16 ⇒
~2,368 optimizer steps) is roughly **5–6 hours** on this GPU — not run as
part of this session's verification (the smoke test proves correctness;
committing several hours of GPU time is a separate decision). Run it
yourself with `python scripts/train_qlora.py --epochs 1` (safe to
`Ctrl+C` — `save_strategy="epoch"` checkpoints at each epoch boundary, or
pass `--max-steps N` for a bounded partial run).

## 5. Try it

```bash
python scripts/infer.py --prompt "What is a Bayesian network?"
```

Confirmed working after the smoke-test adapter: coherent, on-topic
completions in the trained `### Human: / ### Assistant:` format.

## Relationship to the U agent

None, architecturally — this is a general-purpose SFT pipeline for a Pythia
model; the `obiai` U agent's reasoning stays exact/symbolic (Bayesian
networks, epistemic DAG, bias/safety audits — see the top-level
[README.md](../README.md) and [docs/traceability.md](../docs/traceability.md)).
The one deliberate link is code reuse: `obiai.bayes`/`obiai.bayesian` power
both the U agent's raised-hand reasoning *and* this pipeline's bias-audit
weights — one proven implementation of the paper's marginalization, two
applications. If a trained model here were ever wired into U as a chat
backend, that would be a new, explicit integration point (e.g. behind a
provider protocol, matching how `SpeechToTextProvider`/`TextToSpeechProvider`
are designed as swappable interfaces) — not implemented here.
