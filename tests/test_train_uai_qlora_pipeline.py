"""End-to-end (fully faked) test of train_uai_qlora: artifact registration,
final-only checkpointing, and current.json only updating on success.

The real transformers/peft/torch/datasets stack is never imported here --
``_load_training_stack`` and ``load_dataset`` are replaced with minimal
fakes so this stays a fast unit test, not a real training run.
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from obiai.training import uai_qlora
from obiai.training.artifacts import default_artifact_root, read_current


class _FakeDataset:
    def __init__(self, records: list[dict]) -> None:
        self.records = records

    def __len__(self) -> int:
        return len(self.records)

    @property
    def column_names(self) -> list[str]:
        return list(self.records[0].keys()) if self.records else []

    def select(self, indices):
        idx = list(indices)
        return _FakeDataset([self.records[i] for i in idx])

    def map(self, fn, remove_columns=None):
        return _FakeDataset([fn(record) for record in self.records])


class _FakeTokenizer:
    pad_token = "<pad>"
    eos_token = "<eos>"
    pad_token_id = 0

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": [1] * max(1, min(len(text), 5))}

    def save_pretrained(self, path) -> None:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        (p / "tokenizer_config.json").write_text("{}", encoding="utf-8")

    @classmethod
    def from_pretrained(cls, name) -> "_FakeTokenizer":
        return cls()


class _FakePeftModel:
    def __init__(self, *, write_adapter_files: bool = True) -> None:
        self._write_adapter_files = write_adapter_files

    def print_trainable_parameters(self) -> None:
        pass

    def save_pretrained(self, path) -> None:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        if self._write_adapter_files:
            (p / "adapter_config.json").write_text("{}", encoding="utf-8")
            (p / "adapter_model.safetensors").write_bytes(b"fake-weights")


class _FakeCuda:
    @staticmethod
    def is_available() -> bool:
        return False


class _FakeTorch:
    bfloat16 = "bfloat16"
    float16 = "float16"
    float32 = "float32"
    cuda = _FakeCuda()

    class nn:  # noqa: N801 - mirrors torch.nn access pattern
        class CrossEntropyLoss:
            def __init__(self, *a, **k):
                pass


def _fake_stack(monkeypatch: pytest.MonkeyPatch, *, write_adapter_files: bool, captured_args: list) -> None:
    def fake_load_dataset(fmt, data_files, split):
        records = [
            {"prompt": "### Human: what is OBIAI?\n\n### Assistant: ", "completion": "OBIAI is ..."},
            {"prompt": "### Human: hello\n\n### Assistant: ", "completion": "hi there"},
        ]
        return _FakeDataset(records)

    class _FakeTrainingArguments:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            captured_args.append(self)

    class _FakeTrainerBase:
        def __init__(self, model, args, train_dataset, data_collator):
            self.model = model
            self.args = args
            self.train_dataset = train_dataset
            self.data_collator = data_collator
            self.state = types.SimpleNamespace(
                log_history=[{"loss": 3.2, "epoch": 0.5}, {"loss": 2.1, "epoch": 1.0}],
                global_step=uai_qlora.FAST_MAX_STEPS,
            )

        def train(self):
            return None

    def fake_load_training_stack() -> dict:
        return {
            "torch": _FakeTorch(),
            "load_dataset": fake_load_dataset,
            "LoraConfig": lambda **kwargs: kwargs,
            "get_peft_model": lambda model, lora_config: _FakePeftModel(
                write_adapter_files=write_adapter_files
            ),
            "prepare_model_for_kbit_training": lambda model, use_gradient_checkpointing: model,
            "AutoModelForCausalLM": types.SimpleNamespace(
                from_pretrained=lambda name, torch_dtype=None: types.SimpleNamespace()
            ),
            "AutoTokenizer": _FakeTokenizer,
            "BitsAndBytesConfig": lambda **kwargs: kwargs,
            "Trainer": _FakeTrainerBase,
            "TrainingArguments": _FakeTrainingArguments,
        }

    monkeypatch.setattr(uai_qlora, "_load_training_stack", fake_load_training_stack)


def test_successful_fast_run_registers_artifact_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    captured_args: list = []
    _fake_stack(monkeypatch, write_adapter_files=True, captured_args=captured_args)

    data_path = tmp_path / "data.jsonl"
    data_path.write_text('{"prompt": "x", "completion": "y"}\n', encoding="utf-8")

    config = uai_qlora.resolve_uai_training_config(fast=True, data=data_path)
    uai_qlora.train_uai_qlora(config)

    out = capsys.readouterr().out
    assert "Training completed." in out
    assert "Adapter validated: yes" in out
    assert "Tokenizer validated: yes" in out
    assert "Runtime manifest updated: yes" in out
    assert "Final training loss: 2.1000" in out

    # Final-only checkpointing: the trainer must never be asked to save its
    # own mid-run checkpoints -- the run dir is saved explicitly instead.
    assert captured_args[-1].save_strategy == "no"
    assert captured_args[-1].gradient_accumulation_steps == uai_qlora.FAST_GRAD_ACCUM
    assert captured_args[-1].per_device_train_batch_size == uai_qlora.FAST_BATCH_SIZE
    assert captured_args[-1].dataloader_num_workers == 0
    assert captured_args[-1].gradient_checkpointing is False

    artifact_root = default_artifact_root()
    current = read_current(artifact_root)
    assert current is not None
    assert current.status == "ready"

    adapter_dir = artifact_root / current.adapter_path
    tokenizer_dir = artifact_root / current.tokenizer_path
    assert (adapter_dir / "adapter_config.json").is_file()
    assert (tokenizer_dir / "tokenizer_config.json").is_file()

    run_output = adapter_dir.parent
    assert (run_output / "training_config.json").is_file()
    assert (run_output / "metrics.json").is_file()


def test_failed_artifact_validation_does_not_touch_current_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    captured_args: list = []
    _fake_stack(monkeypatch, write_adapter_files=False, captured_args=captured_args)

    data_path = tmp_path / "data.jsonl"
    data_path.write_text('{"prompt": "x", "completion": "y"}\n', encoding="utf-8")

    config = uai_qlora.resolve_uai_training_config(fast=True, data=data_path)

    with pytest.raises(SystemExit, match="Artifact validation failed"):
        uai_qlora.train_uai_qlora(config)

    out = capsys.readouterr().out
    assert "Adapter validated: no" in out
    assert "Runtime manifest updated: no" in out

    assert read_current(default_artifact_root()) is None
