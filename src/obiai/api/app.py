"""FastAPI application factory for U."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import obiai
from obiai.agents import build_u_engine
from obiai.api import routes_meta, routes_sessions, ws
from obiai.api.service import UService
from obiai.core.config import Settings, load_settings
from obiai.demo import build_demo_agent
from obiai.knowledge import load_trusted_uagentic_model
from obiai.memory import InMemorySessionRepository
from obiai.modules import KNOWN_MODULES, ModuleRegistry
from obiai.realtime import SessionEventBus
from obiai.training.runtime import UAIModelManager

__all__ = ["create_app"]


class ReasonRequest(BaseModel):
    """Legacy request body for the original OBIAI demo endpoint."""

    proposition: str
    evidence: dict[str, bool]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else load_settings()

    app = FastAPI(
        title="U — Ontological Bayesian Video Intelligence",
        version=obiai.__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.u.server.cors_origins,
        # Also allow the dev frontend from any private-LAN address (so
        # another device on the same network can load the app), on top of
        # the exact origins above.
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}):5173",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    engine = build_u_engine(settings)
    u_model = load_trusted_uagentic_model()
    # Cheap to construct: it only remembers the artifact root. The actual
    # tokenizer/base-model/adapter load is deferred to the first chat
    # message that needs it, so startup never blocks on it.
    uai_models = UAIModelManager()
    repo = InMemorySessionRepository(
        transcript_retention=settings.u.privacy.transcript_retention
    )
    bus = SessionEventBus()
    service = UService(
        repo=repo, bus=bus, engine=engine, settings=settings, u_model=u_model, uai_models=uai_models
    )

    # Dynamic module loading (Unbiased AI paper, Hypothesis III).
    registry = ModuleRegistry()
    for name in settings.modules.enabled:
        spec = KNOWN_MODULES.get(name)
        if spec is None:
            raise ValueError(f"Unknown module in modules.enabled: {name}")
        registry.load(*spec)

    app.state.settings = settings
    app.state.service = service
    app.state.registry = registry
    app.state.u_model = u_model

    app.include_router(routes_meta.router)
    app.include_router(routes_sessions.router)
    app.include_router(ws.router)

    # Legacy OBIAgent endpoint, preserved verbatim in behavior.
    legacy_agent = build_demo_agent()

    @app.post("/reason", tags=["legacy"])
    def reason(request: ReasonRequest):
        return legacy_agent.reason(request.proposition, request.evidence)

    return app
