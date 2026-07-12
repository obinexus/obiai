"""Per-session fan-out of server events to any number of listeners."""

from __future__ import annotations

import asyncio

from obiai.realtime.events import ServerEvent

__all__ = ["SessionEventBus"]


class SessionEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[ServerEvent]]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue[ServerEvent]:
        queue: asyncio.Queue[ServerEvent] = asyncio.Queue()
        self._subscribers.setdefault(session_id, set()).add(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue[ServerEvent]) -> None:
        listeners = self._subscribers.get(session_id)
        if listeners is None:
            return
        listeners.discard(queue)
        if not listeners:
            self._subscribers.pop(session_id, None)

    async def publish(self, session_id: str, event: ServerEvent) -> None:
        for queue in list(self._subscribers.get(session_id, ())):
            await queue.put(event)

    def drop_session(self, session_id: str) -> None:
        self._subscribers.pop(session_id, None)
