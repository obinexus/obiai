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
