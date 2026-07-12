from pathlib import Path

import pytest

from obiai.core.config import Settings, ThresholdSettings, load_settings


def test_defaults_without_file() -> None:
    settings = Settings()
    assert settings.agent.name == "U"
    assert settings.u.thresholds.yes_threshold == 0.75
    assert settings.u.thresholds.no_threshold == 0.25
    assert settings.u.thresholds.max_uncertainty_for_action == 0.30
    assert settings.u.phi.prior == {"calibrated": 0.9, "miscalibrated": 0.1}
    assert settings.u.epistemic.alpha + settings.u.epistemic.beta == pytest.approx(1.0)


def test_privacy_defaults_are_safe() -> None:
    settings = Settings()
    assert settings.u.privacy.upload_frames is False
    assert settings.u.privacy.transcript_retention == "session"
    assert settings.u.vision.allowed_event_types == ["participant_raised_hand"]


def test_repo_config_file_loads() -> None:
    repo_config = Path(__file__).resolve().parents[1] / "config" / "obiai.yaml"
    settings = load_settings(repo_config)
    assert settings.agent.name == "U"
    assert settings.u.vision.min_confidence == 0.80
    assert settings.modules.enabled == ["echo"]


def test_yaml_overrides(tmp_path: Path) -> None:
    config = tmp_path / "u.yaml"
    config.write_text(
        "u:\n  thresholds:\n    yes_threshold: 0.9\n  privacy:\n    transcript_retention: none\n",
        encoding="utf-8",
    )
    settings = load_settings(config)
    assert settings.u.thresholds.yes_threshold == 0.9
    assert settings.u.thresholds.no_threshold == 0.25  # default preserved
    assert settings.u.privacy.transcript_retention == "none"


def test_explicit_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_settings(tmp_path / "missing.yaml")


def test_threshold_ordering_enforced() -> None:
    with pytest.raises(ValueError):
        ThresholdSettings(yes_threshold=0.2, no_threshold=0.4)
