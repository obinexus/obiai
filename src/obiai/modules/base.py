from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AgentModule(ABC):
    name: str

    @abstractmethod
    def validate(self) -> None: ...

    @abstractmethod
    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]: ...
