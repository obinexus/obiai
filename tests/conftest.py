"""Shared test fixtures.

Every test gets its own empty UAI artifact root. Without this, any test
that builds the real app (``create_app``) would read the repository's
actual ``artifacts/uai/current.json`` -- so running a real
``obiai train uai`` in this working copy would silently change what
already-passing seeded-chat tests observe (they would start getting real
model generations instead of the fixed seeded text they assert against).
Isolating the artifact root keeps test behavior independent of whatever
training has or hasn't happened in this checkout.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_uai_artifact_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OBIAI_ARTIFACT_ROOT", str(tmp_path / "artifacts-uai"))
