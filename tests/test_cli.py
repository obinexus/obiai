from pathlib import Path

from typer.testing import CliRunner

from obiai.cli import app
from obiai.training import uai_qlora


runner = CliRunner()


def test_obiai_train_uai_help() -> None:
    result = runner.invoke(app, ["train", "uai", "--help"])

    assert result.exit_code == 0
    assert "--base-model" in result.stdout
    assert "--grad-accum" in result.stdout
    assert "--hf-dataset" in result.stdout


def test_obiai_train_uai_forwards_options(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_train(config: uai_qlora.UAITrainingConfig) -> None:
        captured["config"] = config

    monkeypatch.setattr(uai_qlora, "train_uai_qlora", fake_train)

    data = tmp_path / "sft_pairs.jsonl"
    output = tmp_path / "adapter"
    result = runner.invoke(
        app,
        [
            "train",
            "uai",
            "--base-model",
            "local-model",
            "--data",
            str(data),
            "--output",
            str(output),
            "--max-steps",
            "8",
            "--epochs",
            "2",
            "--batch-size",
            "2",
            "--grad-accum",
            "4",
            "--lr",
            "0.001",
            "--warmup-ratio",
            "0.1",
            "--max-length",
            "128",
            "--limit",
            "16",
            "--precision",
            "fp16",
        ],
    )

    assert result.exit_code == 0
    config = captured["config"]
    assert config.base_model == "local-model"
    assert config.data == data
    assert config.output == output
    assert config.max_steps == 8
    assert config.epochs == 2
    assert config.batch_size == 2
    assert config.grad_accum == 4
    assert config.lr == 0.001
    assert config.warmup_ratio == 0.1
    assert config.max_length == 128
    assert config.limit == 16
    assert config.precision == "fp16"


def test_obiai_train_uai_fast_flag_selects_fast_profile(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_train(config: uai_qlora.UAITrainingConfig) -> None:
        captured["config"] = config

    monkeypatch.setattr(uai_qlora, "train_uai_qlora", fake_train)

    result = runner.invoke(app, ["train", "uai", "--fast"])

    assert result.exit_code == 0
    config = captured["config"]
    assert config.fast is True
    assert config.max_steps == uai_qlora.FAST_MAX_STEPS
    assert config.grad_accum == uai_qlora.FAST_GRAD_ACCUM
    assert config.batch_size == uai_qlora.FAST_BATCH_SIZE
    assert config.limit == uai_qlora.FAST_LIMIT
    assert config.max_length == uai_qlora.FAST_MAX_LENGTH
    assert config.gradient_checkpointing is False
    assert config.dataloader_workers == 0
    assert config.data == uai_qlora.default_fast_data_path()


def test_obiai_train_uai_fast_flag_still_overridable(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_train(config: uai_qlora.UAITrainingConfig) -> None:
        captured["config"] = config

    monkeypatch.setattr(uai_qlora, "train_uai_qlora", fake_train)

    data = tmp_path / "custom.jsonl"
    result = runner.invoke(app, ["train", "uai", "--fast", "--max-steps", "3", "--data", str(data)])

    assert result.exit_code == 0
    config = captured["config"]
    assert config.fast is True
    assert config.max_steps == 3
    assert config.data == data


def test_obiai_train_uai_forwards_hugging_face_dataset_options(monkeypatch) -> None:
    captured = {}

    def fake_train(config: uai_qlora.UAITrainingConfig) -> None:
        captured["config"] = config

    monkeypatch.setattr(uai_qlora, "train_uai_qlora", fake_train)

    result = runner.invoke(
        app,
        [
            "train",
            "uai",
            "--fast",
            "--hf-dataset",
            "xDAN-datasets/ChatQA-Training-Data",
            "--hf-subset",
            "drop",
            "--hf-split",
            "train",
        ],
    )

    assert result.exit_code == 0
    config = captured["config"]
    assert config.data is None
    assert config.hf_dataset == "xDAN-datasets/ChatQA-Training-Data"
    assert config.hf_subset == "drop"
    assert config.hf_split == "train"


def test_obiai_model_status_reports_unregistered_and_unreachable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OBIAI_ARTIFACT_ROOT", str(tmp_path))

    result = runner.invoke(app, ["model", "status", "--port", "59321"])

    assert result.exit_code == 0
    assert "none registered yet" in result.stdout
    assert "not reachable" in result.stdout


def test_obiai_model_reload_fails_clearly_when_service_unreachable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OBIAI_ARTIFACT_ROOT", str(tmp_path))

    result = runner.invoke(app, ["model", "reload", "--port", "59321"])

    assert result.exit_code != 0
    assert "Could not reach a running service" in result.stdout


class _FakeCuda:
    def __init__(self, available: bool, bf16_supported: bool) -> None:
        self._available = available
        self._bf16_supported = bf16_supported

    def is_available(self) -> bool:
        return self._available

    def is_bf16_supported(self) -> bool:
        return self._bf16_supported


class _FakeTorch:
    bfloat16 = "bfloat16"
    float16 = "float16"
    float32 = "float32"

    def __init__(self, *, cuda_available: bool, bf16_supported: bool) -> None:
        self.cuda = _FakeCuda(cuda_available, bf16_supported)


def test_auto_precision_uses_fp16_on_cuda_without_bf16() -> None:
    runtime = uai_qlora.resolve_training_runtime(
        _FakeTorch(cuda_available=True, bf16_supported=False), "auto"
    )

    assert runtime.precision == "fp16"
    assert runtime.compute_dtype == "float16"
    assert runtime.fp16 is True
    assert runtime.bf16 is False
    assert runtime.use_cpu is False


def test_bf16_precision_exits_when_unsupported() -> None:
    try:
        uai_qlora.resolve_training_runtime(
            _FakeTorch(cuda_available=True, bf16_supported=False), "bf16"
        )
    except SystemExit as exc:
        assert "BF16 training is not supported" in str(exc)
    else:
        raise AssertionError("expected unsupported bf16 runtime to exit")
