"""Configuration loading for U.

Settings are plain Pydantic models with defaults that match
``config/obiai.yaml``; the YAML file overrides defaults when present.
Resolution order for the config path:

1. explicit ``path`` argument (must exist, otherwise ``FileNotFoundError``)
2. ``$UAI_CONFIG`` environment variable
3. ``config/obiai.yaml`` under the current working directory
4. ``config/obiai.yaml`` under the repository root (editable installs)

If no file is found through the implicit candidates (2-4), pure defaults are
returned so tests and wheel installs never require a config file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

__all__ = [
    "Settings",
    "load_settings",
]


class LegacyAgentSettings(BaseModel):
    name: str = "U"
    uncertainty_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    decision_threshold: float = Field(default=0.60, ge=0.0, le=1.0)


class OntologySettings(BaseModel):
    strict_relations: bool = True


class BiasSettings(BaseModel):
    protected_attributes: list[str] = Field(
        default_factory=lambda: ["age_group", "disability", "ethnicity", "gender"]
    )
    maximum_demographic_parity_gap: float = Field(default=0.10, ge=0.0, le=1.0)


class ModulesSettings(BaseModel):
    enabled: list[str] = Field(default_factory=lambda: ["echo"])


class ThresholdSettings(BaseModel):
    yes_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    no_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    max_uncertainty_for_action: float = Field(default=0.30, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _ordered(self) -> "ThresholdSettings":
        if self.no_threshold >= self.yes_threshold:
            raise ValueError("no_threshold must be strictly below yes_threshold")
        return self


class PhiSettings(BaseModel):
    """Prior over the discrete bias/confounding parameter phi (paper section 6)."""

    prior: dict[str, float] = Field(
        default_factory=lambda: {"calibrated": 0.9, "miscalibrated": 0.1}
    )


class EpistemicSettings(BaseModel):
    alpha: float = 0.6
    beta: float = 0.4
    filter_threshold: float = 2.0
    flash_threshold: float = 0.25


class VisionSettings(BaseModel):
    allowed_event_types: list[str] = Field(
        default_factory=lambda: ["participant_raised_hand"]
    )
    min_confidence: float = Field(default=0.80, ge=0.0, le=1.0)
    sustain_ms: int = Field(default=500, ge=0)
    cooldown_ms: int = Field(default=4000, ge=0)


class SafetySettings(BaseModel):
    forbidden_inference_categories: list[str] = Field(
        default_factory=lambda: [
            "medical",
            "disability",
            "ethnicity",
            "emotion",
            "identity",
            "honesty",
        ]
    )


class PrivacySettings(BaseModel):
    upload_frames: bool = False
    transcript_retention: Literal["session", "none"] = "session"


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


class USettings(BaseModel):
    thresholds: ThresholdSettings = Field(default_factory=ThresholdSettings)
    phi: PhiSettings = Field(default_factory=PhiSettings)
    epistemic: EpistemicSettings = Field(default_factory=EpistemicSettings)
    vision: VisionSettings = Field(default_factory=VisionSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    server: ServerSettings = Field(default_factory=ServerSettings)


class Settings(BaseModel):
    agent: LegacyAgentSettings = Field(default_factory=LegacyAgentSettings)
    ontology: OntologySettings = Field(default_factory=OntologySettings)
    bias: BiasSettings = Field(default_factory=BiasSettings)
    modules: ModulesSettings = Field(default_factory=ModulesSettings)
    u: USettings = Field(default_factory=USettings)


def _repo_root_candidate() -> Path:
    # src/obiai/core/config.py -> parents[3] is the repository root in editable installs.
    return Path(__file__).resolve().parents[3] / "config" / "obiai.yaml"


def load_settings(path: Path | str | None = None) -> Settings:
    if path is not None:
        config_path = Path(path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return _load_file(config_path)

    candidates: list[Path] = []
    env_path = os.environ.get("UAI_CONFIG")
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path.cwd() / "config" / "obiai.yaml")
    candidates.append(_repo_root_candidate())

    for candidate in candidates:
        if candidate.is_file():
            return _load_file(candidate)
    return Settings()


def _load_file(config_path: Path) -> Settings:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping: {config_path}")
    return Settings.model_validate(raw)
