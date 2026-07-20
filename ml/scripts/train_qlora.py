"""Compatibility wrapper for the UAI QLoRA trainer.

Prefer:

    obiai train uai

This script is kept so existing notes and shell history that call
``python scripts/train_qlora.py`` still work from the ``ml`` directory.
"""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

REPO_SRC = Path(__file__).resolve().parents[2] / "src"
if REPO_SRC.exists() and str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

main = import_module("obiai.training.uai_qlora").main


if __name__ == "__main__":
    main()
