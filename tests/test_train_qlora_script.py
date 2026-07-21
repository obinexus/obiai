"""Compatibility: ml/scripts/train_qlora.py must keep forwarding to the real trainer."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from obiai.training import uai_qlora

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "ml" / "scripts" / "train_qlora.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("train_qlora_script", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_compat_wrapper_main_is_the_real_trainer_main() -> None:
    script = _load_script()
    assert script.main is uai_qlora.main


def test_build_arg_parser_supports_fast_flag() -> None:
    args = uai_qlora.build_arg_parser().parse_args(["--fast"])
    assert args.fast is True


def test_build_arg_parser_defaults_fast_to_false() -> None:
    args = uai_qlora.build_arg_parser().parse_args([])
    assert args.fast is False
    assert args.max_steps is None
    assert args.limit is None
