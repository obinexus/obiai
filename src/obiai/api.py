from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from .demo import build_demo_agent

app = FastAPI(title="OBIAI Agent API", version="0.1.0")
agent = build_demo_agent()


class ReasonRequest(BaseModel):
    proposition: str
    evidence: dict[str, bool]


@app.post("/reason")
def reason(request: ReasonRequest):
    return agent.reason(request.proposition, request.evidence)
