"""Tests for the trusted UAI artifact manifest (src/obiai/training/artifacts.py)."""

from __future__ import annotations

import pickle
from pathlib import Path

import pytest

from obiai.training.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    CurrentManifest,
    UAIModelArtifact,
    UntrustedArtifactPathError,
    load_artifact_descriptor,
    read_current,
    write_artifact_descriptor,
    write_current,
)


def _descriptor(run_id: str = "2026-07-21T192400Z") -> UAIModelArtifact:
    return UAIModelArtifact(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        base_model="EleutherAI/pythia-2.8b",
        adapter_path=f"runs/{run_id}/adapter",
        tokenizer_path=f"runs/{run_id}/tokenizer",
        training_config_path=f"runs/{run_id}/training_config.json",
        run_id=run_id,
    )


def test_current_json_missing_returns_none(tmp_path: Path) -> None:
    assert read_current(tmp_path) is None


def test_write_and_read_current_roundtrip(tmp_path: Path) -> None:
    manifest = CurrentManifest(
        run_id="run-1",
        model_path="runs/run-1/model.pkl",
        adapter_path="runs/run-1/adapter",
        tokenizer_path="runs/run-1/tokenizer",
        status="ready",
    )
    write_current(manifest, artifact_root=tmp_path)

    loaded = read_current(tmp_path)
    assert loaded == manifest


def test_write_and_load_artifact_descriptor_roundtrip(tmp_path: Path) -> None:
    descriptor = _descriptor()
    path = tmp_path / "runs" / descriptor.run_id / "model.pkl"
    write_artifact_descriptor(path, descriptor, artifact_root=tmp_path)

    loaded = load_artifact_descriptor(path, artifact_root=tmp_path)
    assert loaded == descriptor


def test_load_artifact_descriptor_rejects_path_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "artifacts" / "uai"
    outside = tmp_path / "elsewhere" / "model.pkl"
    outside.parent.mkdir(parents=True)
    with outside.open("wb") as handle:
        pickle.dump(_descriptor(), handle)

    with pytest.raises(UntrustedArtifactPathError):
        load_artifact_descriptor(outside, artifact_root=root)


def test_load_artifact_descriptor_rejects_schema_mismatch(tmp_path: Path) -> None:
    bad = UAIModelArtifact(
        schema_version=ARTIFACT_SCHEMA_VERSION + 1,
        base_model="EleutherAI/pythia-2.8b",
        adapter_path="runs/x/adapter",
        tokenizer_path="runs/x/tokenizer",
        training_config_path="runs/x/training_config.json",
        run_id="x",
    )
    path = tmp_path / "runs" / "x" / "model.pkl"
    write_artifact_descriptor(path, bad, artifact_root=tmp_path)

    with pytest.raises(ValueError, match="schema version"):
        load_artifact_descriptor(path, artifact_root=tmp_path)


def test_load_artifact_descriptor_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_artifact_descriptor(tmp_path / "runs" / "nope" / "model.pkl", artifact_root=tmp_path)


def test_restricted_unpickler_rejects_arbitrary_objects(tmp_path: Path) -> None:
    """A pickle naming anything other than UAIModelArtifact must never load.

    This is the actual safety property the ``.pkl`` requirement depends on:
    plain ``pickle.load`` can invoke arbitrary callables recorded in the
    stream, so a swapped-in malicious pickle must be refused, not executed.
    """
    import os

    path = tmp_path / "runs" / "x" / "model.pkl"
    path.parent.mkdir(parents=True)
    with path.open("wb") as handle:
        # A GLOBAL reference to os.system: never called, because
        # find_class() must refuse it before unpickling can finish.
        pickle.dump(os.system, handle)

    with pytest.raises(pickle.UnpicklingError):
        load_artifact_descriptor(path, artifact_root=tmp_path)


def test_write_current_is_atomic_leaves_no_tmp_file(tmp_path: Path) -> None:
    manifest = CurrentManifest(
        run_id="run-1",
        model_path="runs/run-1/model.pkl",
        adapter_path="runs/run-1/adapter",
        tokenizer_path="runs/run-1/tokenizer",
        status="ready",
    )
    write_current(manifest, artifact_root=tmp_path)
    assert not (tmp_path / "current.json.tmp").exists()
    assert (tmp_path / "current.json").exists()
