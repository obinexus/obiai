"""WebSocket endpoint for live sessions.

Protocol:

* connect to ``/ws/sessions/{session_id}`` (session must already exist,
  otherwise the socket closes with code 4404);
* the server immediately sends ``session.ready``;
* ``session.start`` triggers U's greeting ("Hi, I am U.");
* ``transcript.partial`` (live speech recognition, interim) is rebroadcast
  for captioning and never persisted; ``transcript.final`` is persisted and
  answered like a chat turn — see ``UService.handle_voice_transcript``;
* invalid or unknown events produce an ``error`` event and the connection
  stays open;
* the writer task is the only sender, so events are never interleaved.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from obiai.core.errors import UError
from obiai.realtime.events import (
    ChatMessage,
    ClarificationAnswer,
    ClientTranscriptFinal,
    ClientTranscriptPartial,
    ErrorEvent,
    ObservationSubmit,
    SessionEnd,
    SessionReady,
    SessionStart,
    client_event_adapter,
)

router = APIRouter()

SESSION_NOT_FOUND_CODE = 4404


@router.websocket("/ws/sessions/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str) -> None:
    service = websocket.app.state.service
    await websocket.accept()
    if service.repo.get(session_id) is None:
        await websocket.close(code=SESSION_NOT_FOUND_CODE, reason="session not found")
        return

    queue = service.bus.subscribe(session_id)
    await websocket.send_text(SessionReady(session_id=session_id).model_dump_json())

    async def writer() -> None:
        while True:
            event = await queue.get()
            await websocket.send_text(event.model_dump_json())

    async def reader() -> None:
        while True:
            text = await websocket.receive_text()
            try:
                event = client_event_adapter.validate_json(text)
            except ValidationError as exc:
                await service.bus.publish(
                    session_id,
                    ErrorEvent(message=f"invalid event: {exc.errors()[0]['msg']}"),
                )
                continue
            if isinstance(event, SessionEnd):
                return
            try:
                await _dispatch(service, session_id, event)
            except UError as exc:
                await service.bus.publish(
                    session_id, ErrorEvent(message=str(exc), code="rejected")
                )

    reader_task = asyncio.create_task(reader())
    writer_task = asyncio.create_task(writer())
    try:
        done, pending = await asyncio.wait(
            {reader_task, writer_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc is not None and not isinstance(exc, WebSocketDisconnect):
                raise exc
    except WebSocketDisconnect:
        pass
    finally:
        reader_task.cancel()
        writer_task.cancel()
        service.bus.unsubscribe(session_id, queue)
        try:
            await websocket.close()
        except RuntimeError:
            pass  # already closed / disconnected


async def _dispatch(service, session_id: str, event) -> None:
    if isinstance(event, SessionStart):
        await service.greet(session_id)
    elif isinstance(event, ChatMessage):
        await service.handle_chat(session_id, event.text)
    elif isinstance(event, ObservationSubmit):
        await service.handle_observation(session_id, event.observation)
    elif isinstance(event, ClarificationAnswer):
        await service.handle_chat(session_id, event.answer)
    elif isinstance(event, ClientTranscriptPartial):
        await service.handle_partial_transcript(session_id, event.segment)
    elif isinstance(event, ClientTranscriptFinal):
        await service.handle_voice_transcript(session_id, event.segment)
