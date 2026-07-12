"""Session lifecycle and observation/reasoning REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from obiai.core.errors import (
    DisallowedEventTypeError,
    NoObservationsError,
    SessionNotFoundError,
    UnknownEventTypeError,
)
from obiai.core.models import Decision, Observation, ObservationIn
from obiai.memory import Session

router = APIRouter(tags=["sessions"])


class SessionCreated(BaseModel):
    session_id: str


class ObservationAccepted(BaseModel):
    observation: Observation
    decision: Decision


def _service(request: Request):
    return request.app.state.service


@router.post("/sessions", status_code=status.HTTP_201_CREATED, response_model=SessionCreated)
def create_session(request: Request) -> SessionCreated:
    session = _service(request).create_session()
    return SessionCreated(session_id=session.session_id)


@router.get("/sessions/{session_id}", response_model=Session)
def get_session(session_id: str, request: Request) -> Session:
    try:
        return _service(request).get_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, request: Request) -> Response:
    try:
        _service(request).delete_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sessions/{session_id}/observations",
    status_code=status.HTTP_201_CREATED,
    response_model=ObservationAccepted,
)
async def submit_observation(
    session_id: str, observation_in: ObservationIn, request: Request
) -> ObservationAccepted:
    try:
        observation, decision = await _service(request).handle_observation(
            session_id, observation_in
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (DisallowedEventTypeError, UnknownEventTypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ObservationAccepted(observation=observation, decision=decision)


@router.post("/sessions/{session_id}/reason", response_model=Decision)
def rereason(session_id: str, request: Request) -> Decision:
    try:
        return _service(request).rereason_latest(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoObservationsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/decisions", response_model=list[Decision])
def list_decisions(session_id: str, request: Request) -> list[Decision]:
    try:
        return _service(request).get_session(session_id).decisions
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
