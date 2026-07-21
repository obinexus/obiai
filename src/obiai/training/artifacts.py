"""Trusted artifact manifest for trained UAI models.

Layout under the artifact root (default: ``<repo>/artifacts/uai``)::

    artifacts/uai/
      current.json                 <- points at the active, validated run
      runs/<run-id>/
        adapter/                   <- LoRA adapter (peft save_pretrained)
        tokenizer/                 <- tokenizer (save_pretrained)
        training_config.json       <- resolved UAITrainingConfig used
        metrics.json               <- loss/step summary from the trainer
        model.pkl                  <- UAIModelArtifact descriptor (trusted)

``model.pkl`` never holds a HF/PyTorch model object. It is a small, frozen
dataclass naming *where* the real adapter/tokenizer live on disk, so the
pickle stays tiny, fast, and safe to load. Loading is restricted to that one
dataclass via a allow-listing ``Unpickler`` and to paths inside the
configured artifact root -- a path from chat, the API, or an upload is never
accepted.
"""

from __future__ import annotations

import json
import os
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "ARTIFACT_SCHEMA_VERSION",
    "CurrentManifest",
    "UAIModelArtifact",
    "UntrustedArtifactPathError",
    "default_artifact_root",
    "load_artifact_descriptor",
    "read_current",
    "run_dir",
    "write_artifact_descriptor",
    "write_current",
]

ARTIFACT_SCHEMA_VERSION = 1
_CURRENT_FILENAME = "current.json"


def default_artifact_root() -> Path:
    """The artifact root, overridable for tests/alternate installs."""
    env_root = os.getenv("OBIAI_ARTIFACT_ROOT")
    if env_root:
        return Path(env_root).expanduser()
    # src/obiai/training/artifacts.py -> parents[3] is the repository root.
    return Path(__file__).resolve().parents[3] / "artifacts" / "uai"


def run_dir(artifact_root: Path, run_id: str) -> Path:
    return artifact_root / "runs" / run_id


@dataclass(frozen=True)
class UAIModelArtifact:
    """Trusted local descriptor. Paths are relative to the artifact root."""

    schema_version: int
    base_model: str
    adapter_path: str
    tokenizer_path: str
    training_config_path: str
    run_id: str


@dataclass(frozen=True)
class CurrentManifest:
    run_id: str
    model_path: str
    adapter_path: str
    tokenizer_path: str
    status: str  # "ready" | "failed"


class UntrustedArtifactPathError(ValueError):
    """Raised when an artifact path resolves outside the trusted artifact root."""


class _RestrictedUnpickler(pickle.Unpickler):
    """Only allows constructing :class:`UAIModelArtifact`.

    Ordinary ``pickle.load`` can invoke arbitrary callables named in the
    stream; since the ``.pkl`` requirement in this project means "a small
    trusted descriptor", the unpickler is allow-listed down to that single
    class so a swapped-in malicious pickle cannot execute code.
    """

    _ALLOWED = {("obiai.training.artifacts", "UAIModelArtifact")}

    def find_class(self, module: str, name: str) -> Any:
        if (module, name) not in self._ALLOWED:
            raise pickle.UnpicklingError(f"refusing to unpickle {module}.{name}")
        return super().find_class(module, name)


def _require_inside_root(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise UntrustedArtifactPathError(
            f"{resolved_path} is outside the trusted artifact root {resolved_root}"
        )
    return resolved_path


def write_artifact_descriptor(path: Path, artifact: UAIModelArtifact, *, artifact_root: Path) -> None:
    resolved = _require_inside_root(path, artifact_root)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("wb") as handle:
        pickle.dump(artifact, handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_artifact_descriptor(path: Path, *, artifact_root: Path | None = None) -> UAIModelArtifact:
    root = artifact_root if artifact_root is not None else default_artifact_root()
    resolved = _require_inside_root(path, root)
    if not resolved.is_file():
        raise FileNotFoundError(f"artifact descriptor not found: {resolved}")
    with resolved.open("rb") as handle:
        obj = _RestrictedUnpickler(handle).load()
    if not isinstance(obj, UAIModelArtifact):
        raise TypeError(f"unexpected object in {resolved}: {type(obj)!r}")
    if obj.schema_version != ARTIFACT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported artifact schema version {obj.schema_version} "
            f"(expected {ARTIFACT_SCHEMA_VERSION})"
        )
    return obj


def read_current(artifact_root: Path | None = None) -> CurrentManifest | None:
    root = artifact_root if artifact_root is not None else default_artifact_root()
    path = root / _CURRENT_FILENAME
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return CurrentManifest(**raw)


def write_current(manifest: CurrentManifest, *, artifact_root: Path | None = None) -> None:
    """Atomically publish ``current.json``.

    Only call this after the run has been validated -- this is the single
    switch that makes a run "the active model" for the runtime loader.
    """
    root = artifact_root if artifact_root is not None else default_artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    final_path = root / _CURRENT_FILENAME
    tmp_path = final_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")
    os.replace(tmp_path, final_path)
