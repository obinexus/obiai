"""Meta endpoints: health, version, ontology introspection."""

from __future__ import annotations

from fastapi import APIRouter, Request

import obiai

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
    }


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
