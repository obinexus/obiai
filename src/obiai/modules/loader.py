from __future__ import annotations

import importlib
from .base import AgentModule


class ModuleRegistry:
    def __init__(self) -> None:
        self.modules: dict[str, AgentModule] = {}

    def load(self, import_path: str, class_name: str) -> AgentModule:
        module = importlib.import_module(import_path)
        cls = getattr(module, class_name)
        instance: AgentModule = cls()
        instance.validate()
        self.modules[instance.name] = instance
        return instance

    def invoke(self, name: str, payload: dict[str, object]) -> dict[str, object]:
        if name not in self.modules:
            raise KeyError(f"Module not loaded: {name}")
        return self.modules[name].invoke(payload)
