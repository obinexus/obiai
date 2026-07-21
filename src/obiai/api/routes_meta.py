"""Meta endpoints: health, version, ontology introspection."""

from __future__ import annotations

from fastapi import APIRouter, Request

import obiai
from obiai.training.runtime import UAIModelLoadError

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/version")
def version(request: Request) -> dict[str, object]:
    registry = request.app.state.registry
    return {
        "name": "obiai-u",
        "version": obiai.__version__,
        "assistant": "U",
        "loaded_modules": sorted(registry.modules),
        "u_model": request.app.state.u_model.describe(),
    }


@router.get("/model/uagentic")
def uagentic_model(request: Request) -> dict[str, object]:
    return request.app.state.u_model.describe()


@router.get("/model/status")
def uai_model_status(request: Request) -> dict[str, object]:
    """Whether *this running process* has loaded the trained UAI adapter."""
    manager = request.app.state.service.uai_models
    if manager is None:
        return {"loaded": False, "loaded_run_id": None, "current_run_id": None, "current_status": None}
    return manager.status()


@router.post("/model/reload")
def uai_model_reload(request: Request) -> dict[str, object]:
    manager = request.app.state.service.uai_models
    if manager is None:
        return {"reloaded": False, "run_id": None, "error": "no UAI model manager configured"}
    try:
        reloaded = manager.reload_if_changed()
    except UAIModelLoadError as exc:
        return {"reloaded": False, "run_id": manager.active_run_id, "error": str(exc)}
    return {"reloaded": reloaded, "run_id": manager.active_run_id}


@router.get("/ontology/concepts")
def ontology_concepts(request: Request) -> list[dict[str, object]]:
    graph = request.app.state.service.engine.ontology.graph
    return [
        {"name": name, **{k: v for k, v in attributes.items()}}
        for name, attributes in sorted(graph.nodes(data=True))
    ]


@router.get("/ontology/relations")
def ontology_relations(request: Request) -> list[dict[str, str]]:
    graph = request.app.state.service.engine.ontology.graph
    return [
        {"subject": subject, "relation": key, "object": obj}
        for subject, obj, key in sorted(graph.edges(keys=True))
    ]
