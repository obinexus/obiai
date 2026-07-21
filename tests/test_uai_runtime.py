"""Tests for UAIModelManager (src/obiai/training/runtime.py).

No real torch/transformers/peft install is exercised: fake stand-ins are
injected into ``sys.modules`` so the runtime's actual load/cache/generate
control flow is tested without downloading or running a real model.
"""

from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from pathlib import Path

import pytest

from obiai.training.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    CurrentManifest,
    UAIModelArtifact,
    write_artifact_descriptor,
    write_current,
)
from obiai.training.runtime import UAIModelLoadError, UAIModelManager


# --- Fake torch/peft/transformers -------------------------------------------


class _Seq:
    def __init__(self, values: list[int]) -> None:
        self.values = values

    def __getitem__(self, item):
        if isinstance(item, slice):
            return _Seq(self.values[item])
        return self.values[item]

    def __add__(self, other):
        return self.values + list(other)


class _Batch:
    def __init__(self, rows: list[list[int]]) -> None:
        self.rows = rows

    @property
    def shape(self):
        return (len(self.rows), len(self.rows[0]))

    def __getitem__(self, i):
        return _Seq(self.rows[i])


class _FakeTokenizer:
    pad_token_id = 0
    eos_token_id = 0

    def __init__(self, path: str) -> None:
        self.path = path

    @classmethod
    def from_pretrained(cls, path):
        return cls(str(path))

    def __call__(self, text, return_tensors=None):
        return {"input_ids": _Batch([[1, 2, 3]])}

    def decode(self, seq, skip_special_tokens=True):
        return " fake reply "


class _FakeBaseModel:
    def __init__(self, name: str) -> None:
        self.name = name

    def eval(self):
        return self

    def generate(self, *, input_ids, max_new_tokens, do_sample, pad_token_id):
        row = input_ids[0]
        extended = row[:] + [9, 9]
        return _Batch([extended])


class _FakeAutoModelForCausalLM:
    @staticmethod
    def from_pretrained(name, torch_dtype=None):
        return _FakeBaseModel(name)


class _FakePeftModel:
    @staticmethod
    def from_pretrained(base, adapter_path):
        base.adapter_path = adapter_path
        return base


@contextmanager
def _no_grad():
    yield


def _install_fake_ml_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_torch = types.ModuleType("torch")
    fake_torch.no_grad = _no_grad
    fake_torch.float32 = "float32"

    fake_transformers = types.ModuleType("transformers")
    fake_transformers.AutoModelForCausalLM = _FakeAutoModelForCausalLM
    fake_transformers.AutoTokenizer = _FakeTokenizer

    fake_peft = types.ModuleType("peft")
    fake_peft.PeftModel = _FakePeftModel

    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setitem(sys.modules, "peft", fake_peft)


# --- Fixtures ----------------------------------------------------------------


def _register_run(artifact_root: Path, run_id: str) -> None:
    run_path = artifact_root / "runs" / run_id
    (run_path / "adapter").mkdir(parents=True)
    (run_path / "tokenizer").mkdir(parents=True)
    descriptor = UAIModelArtifact(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        base_model="EleutherAI/pythia-2.8b",
        adapter_path=f"runs/{run_id}/adapter",
        tokenizer_path=f"runs/{run_id}/tokenizer",
        training_config_path=f"runs/{run_id}/training_config.json",
        run_id=run_id,
    )
    descriptor_path = run_path / "model.pkl"
    write_artifact_descriptor(descriptor_path, descriptor, artifact_root=artifact_root)
    write_current(
        CurrentManifest(
            run_id=run_id,
            model_path=f"runs/{run_id}/model.pkl",
            adapter_path=descriptor.adapter_path,
            tokenizer_path=descriptor.tokenizer_path,
            status="ready",
        ),
        artifact_root=artifact_root,
    )


# --- Tests ---------------------------------------------------------------


def test_load_active_raises_when_nothing_registered(tmp_path: Path) -> None:
    manager = UAIModelManager(tmp_path)
    with pytest.raises(UAIModelLoadError, match="No trained UAI model"):
        manager.load_active()


def test_load_active_raises_when_status_not_ready(tmp_path: Path) -> None:
    write_current(
        CurrentManifest(
            run_id="r1", model_path="runs/r1/model.pkl", adapter_path="runs/r1/adapter",
            tokenizer_path="runs/r1/tokenizer", status="failed",
        ),
        artifact_root=tmp_path,
    )
    manager = UAIModelManager(tmp_path)
    with pytest.raises(UAIModelLoadError, match="not ready"):
        manager.load_active()


def test_load_active_raises_when_adapter_dir_missing(tmp_path: Path) -> None:
    descriptor = UAIModelArtifact(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        base_model="EleutherAI/pythia-2.8b",
        adapter_path="runs/r1/adapter",
        tokenizer_path="runs/r1/tokenizer",
        training_config_path="runs/r1/training_config.json",
        run_id="r1",
    )
    write_artifact_descriptor(tmp_path / "runs" / "r1" / "model.pkl", descriptor, artifact_root=tmp_path)
    write_current(
        CurrentManifest(
            run_id="r1", model_path="runs/r1/model.pkl", adapter_path="runs/r1/adapter",
            tokenizer_path="runs/r1/tokenizer", status="ready",
        ),
        artifact_root=tmp_path,
    )
    manager = UAIModelManager(tmp_path)
    with pytest.raises(UAIModelLoadError, match="Adapter directory missing"):
        manager.load_active()


def test_load_active_succeeds_and_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_ml_stack(monkeypatch)
    _register_run(tmp_path, "run-1")

    manager = UAIModelManager(tmp_path)
    loaded = manager.load_active()

    assert loaded.run_id == "run-1"
    assert manager.active_run_id == "run-1"
    assert manager.status()["loaded"] is True


def test_generate_uses_cached_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_ml_stack(monkeypatch)
    _register_run(tmp_path, "run-1")

    manager = UAIModelManager(tmp_path)
    text = manager.generate("what is OBIAI")

    assert text == "fake reply"


def test_reload_if_changed_false_when_same_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_ml_stack(monkeypatch)
    _register_run(tmp_path, "run-1")

    manager = UAIModelManager(tmp_path)
    manager.load_active()

    assert manager.reload_if_changed() is False


def test_reload_if_changed_true_when_run_id_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_ml_stack(monkeypatch)
    _register_run(tmp_path, "run-1")

    manager = UAIModelManager(tmp_path)
    manager.load_active()

    _register_run(tmp_path, "run-2")
    assert manager.reload_if_changed() is True
    assert manager.active_run_id == "run-2"


def test_try_generate_returns_none_and_does_not_raise_when_unregistered(tmp_path: Path) -> None:
    manager = UAIModelManager(tmp_path)
    assert manager.try_generate("hello") is None


def test_try_generate_returns_text_and_run_id_on_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_ml_stack(monkeypatch)
    _register_run(tmp_path, "run-1")

    manager = UAIModelManager(tmp_path)
    result = manager.try_generate("what is OBIAI")

    assert result == ("fake reply", "run-1")
