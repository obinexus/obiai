from __future__ import annotations
from typing import Any
from .base import AgentModule


class EchoModule(AgentModule):
    name = "echo"

    def validate(self) -> None:
        return None

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"module": self.name, "received": payload}
