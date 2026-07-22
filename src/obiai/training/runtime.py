"""Runtime loader for the trained UAI adapter.

This is the only place the *trained language model* (as opposed to the
deterministic governance pipeline, or the seeded :class:`UAgenticModel`
rule-based router) gets loaded into a running process. It is deliberately
lazy: constructing a :class:`UAIModelManager` is cheap (it only reads a
manifest path), and the actual tokenizer/base-model/adapter load only
happens on first use, then stays cached in memory.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from obiai.training.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    default_artifact_root,
    load_artifact_descriptor,
    read_current,
)
from obiai.training.uai_qlora import CHAT_TEMPLATE

__all__ = ["LoadedUAIModel", "UAIModelLoadError", "UAIModelManager"]

logger = logging.getLogger("obiai.uai_runtime")


class UAIModelLoadError(RuntimeError):
    """Raised when the active trained UAI model cannot be loaded.

    Callers must not treat a caught instance of this as "answered by the
    trained model" -- it means the opposite, and any fallback response must
    be labelled accordingly.
    """


@dataclass
class LoadedUAIModel:
    run_id: str
    base_model: str
    tokenizer: Any
    model: Any
    device: str


class UAIModelManager:
    def __init__(self, artifact_root: Path | None = None, *, max_new_tokens: int | None = None) -> None:
        self.artifact_root = artifact_root if artifact_root is not None else default_artifact_root()
        self.max_new_tokens = max_new_tokens or int(os.getenv("OBIAI_UAI_MAX_NEW_TOKENS", "64"))
        self._loaded: LoadedUAIModel | None = None
        self._lock = threading.RLock()

    @property
    def active_run_id(self) -> str | None:
        return self._loaded.run_id if self._loaded is not None else None

    def status(self) -> dict[str, Any]:
        current = read_current(self.artifact_root)
        return {
            "artifact_root": str(self.artifact_root),
            "current_run_id": current.run_id if current is not None else None,
            "current_status": current.status if current is not None else None,
            "loaded_run_id": self.active_run_id,
            "loaded": self._loaded is not None,
            "loaded_device": self._loaded.device if self._loaded is not None else None,
            "max_new_tokens": self.max_new_tokens,
        }

    def load_active(self) -> LoadedUAIModel:
        with self._lock:
            return self._load_active_unlocked()

    def _load_active_unlocked(self) -> LoadedUAIModel:
        current = read_current(self.artifact_root)
        if current is None:
            raise UAIModelLoadError(
                "No trained UAI model has been registered yet "
                f"({self.artifact_root / 'current.json'} is missing). Run `obiai train uai --fast` first."
            )
        if current.status != "ready":
            raise UAIModelLoadError(
                f"Latest training run {current.run_id!r} is not ready (status={current.status!r})."
            )

        descriptor = load_artifact_descriptor(
            self.artifact_root / current.model_path, artifact_root=self.artifact_root
        )
        if descriptor.schema_version != ARTIFACT_SCHEMA_VERSION:
            raise UAIModelLoadError(f"Unsupported artifact schema version {descriptor.schema_version}.")

        adapter_path = self.artifact_root / descriptor.adapter_path
        tokenizer_path = self.artifact_root / descriptor.tokenizer_path
        if not adapter_path.is_dir():
            raise UAIModelLoadError(f"Adapter directory missing for run {descriptor.run_id!r}: {adapter_path}")
        if not tokenizer_path.is_dir():
            raise UAIModelLoadError(f"Tokenizer directory missing for run {descriptor.run_id!r}: {tokenizer_path}")

        try:
            _prepare_runtime_environment()
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise UAIModelLoadError(
                f"Training/runtime dependency missing: {exc.name or exc}. "
                'Install with: pip install -e ".[train]"'
            ) from exc

        try:
            device = _runtime_device(torch)
            dtype = _runtime_dtype(torch, device)
            tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path))
            try:
                base = AutoModelForCausalLM.from_pretrained(
                    descriptor.base_model,
                    torch_dtype=dtype,
                    low_cpu_mem_usage=True,
                )
            except TypeError:
                base = AutoModelForCausalLM.from_pretrained(
                    descriptor.base_model,
                    torch_dtype=dtype,
                )
            model = PeftModel.from_pretrained(base, str(adapter_path))
            if device != "cpu" and callable(getattr(model, "to", None)):
                model.to(device)
            model.eval()
        except Exception as exc:  # noqa: BLE001 - surfaced as a single clear load error
            raise UAIModelLoadError(
                f"Failed to load trained UAI model for run {descriptor.run_id!r}: {exc}"
            ) from exc

        loaded = LoadedUAIModel(
            run_id=descriptor.run_id,
            base_model=descriptor.base_model,
            tokenizer=tokenizer,
            model=model,
            device=device,
        )
        self._loaded = loaded
        logger.info(
            "uai runtime: loaded trained adapter run_id=%s device=%s",
            descriptor.run_id,
            device,
        )
        return loaded

    def reload_if_changed(self) -> bool:
        with self._lock:
            current = read_current(self.artifact_root)
            latest_run_id = current.run_id if current is not None else None
            if self._loaded is not None and latest_run_id == self._loaded.run_id:
                return False
            self._load_active_unlocked()
            return True

    def generate(self, prompt: str) -> str:
        with self._lock:
            if self._loaded is None:
                self._load_active_unlocked()
            loaded = self._loaded
            assert loaded is not None

            import torch

            formatted = CHAT_TEMPLATE.format(prompt=prompt)
            inputs = _move_inputs_to_device(loaded.tokenizer(formatted, return_tensors="pt"), loaded.device)
            inference_mode = getattr(torch, "inference_mode", torch.no_grad)
            with inference_mode():
                output_ids = loaded.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                    pad_token_id=loaded.tokenizer.pad_token_id or loaded.tokenizer.eos_token_id,
                )
            generated = output_ids[0][inputs["input_ids"].shape[1] :]
            return loaded.tokenizer.decode(generated, skip_special_tokens=True).strip()

    def try_generate(self, prompt: str) -> tuple[str, str] | None:
        """Best-effort generation. Returns ``(text, run_id)`` or ``None``.

        ``None`` means the caller must fall back to a different response
        source -- and must label that fallback honestly, never as
        ``trained_uai``. The reason is always logged.
        """
        try:
            self.reload_if_changed()
            text = self.generate(prompt)
            if not text.strip():
                raise UAIModelLoadError("trained model generated an empty response")
        except UAIModelLoadError as exc:
            logger.warning("uai runtime: trained model unavailable, falling back: %s", exc)
            return None
        except Exception as exc:  # noqa: BLE001 - chat falls back rather than dropping the socket
            logger.exception("uai runtime: trained generation failed, falling back: %s", exc)
            return None
        run_id = self.active_run_id
        assert run_id is not None
        return text, run_id


def _prepare_runtime_environment() -> None:
    if sys.platform == "win32":
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


def _runtime_device(torch_module: Any) -> str:
    cuda = getattr(torch_module, "cuda", None)
    return "cuda" if cuda is not None and cuda.is_available() else "cpu"


def _runtime_dtype(torch_module: Any, device: str) -> Any:
    if device == "cuda":
        cuda = getattr(torch_module, "cuda", None)
        bf16_supported = getattr(cuda, "is_bf16_supported", None)
        if callable(bf16_supported) and bf16_supported():
            return torch_module.bfloat16
        return torch_module.float16
    return torch_module.float32


def _move_inputs_to_device(inputs: Any, device: str) -> Any:
    move = getattr(inputs, "to", None)
    if callable(move):
        return move(device)
    if isinstance(inputs, dict):
        return {
            key: value.to(device) if callable(getattr(value, "to", None)) else value
            for key, value in inputs.items()
        }
    return inputs
