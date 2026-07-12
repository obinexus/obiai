from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class TruthState(str, Enum):
    YES = "YES"
    NO = "NO"
    MAYBE = "MAYBE"


class Evidence(BaseModel):
    variable: str
    value: bool | int | float | str
    source: str = "user"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Action(BaseModel):
    name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str


class BiasReport(BaseModel):
    protected_paths: list[list[str]] = Field(default_factory=list)
    parity_gap: float | None = None
    passed: bool = True
    notes: list[str] = Field(default_factory=list)


class Decision(BaseModel):
    proposition: str
    probability: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    state: TruthState
    explanation: list[str]
    evidence: list[Evidence]
    bias: BiasReport
    actions: list[Action] = Field(default_factory=list)
