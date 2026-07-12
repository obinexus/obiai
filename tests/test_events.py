import asyncio
import json

import pytest
from pydantic import ValidationError

from obiai.realtime import SessionEventBus, client_event_adapter, server_event_adapter
from obiai.realtime.events import AgentMessage, SessionReady


CLIENT_SAMPLES = [
    {"type": "session.start"},
    {"type": "session.end"},
    {"type": "chat.message", "text": "Can you inspect this error?"},
    {
        "type": "observation.submit",
        "observation": {
            "modality": "vision",
            "event_type": "participant_raised_hand",
            "value": True,
            "confidence": 0.9,
            "source": "browser_hand_classifier",
        },
    },
    {"type": "clarification.answer", "decision_id": "decision-1", "answer": "yes"},
]


@pytest.mark.parametrize("payload", CLIENT_SAMPLES, ids=lambda p: p["type"])
def test_client_event_round_trip(payload: dict) -> None:
    event = client_event_adapter.validate_json(json.dumps(payload))
    assert event.type == payload["type"]
    again = client_event_adapter.validate_json(event.model_dump_json())
    assert again == event


def test_unknown_client_event_rejected() -> None:
    with pytest.raises(ValidationError):
        client_event_adapter.validate_json(json.dumps({"type": "media.video.frame", "data": "x"}))


def test_missing_type_rejected() -> None:
    with pytest.raises(ValidationError):
        client_event_adapter.validate_json(json.dumps({"text": "hi"}))


def test_server_event_serialization() -> None:
    ready = SessionReady(session_id="session-1")
    parsed = server_event_adapter.validate_json(ready.model_dump_json())
    assert isinstance(parsed, SessionReady)
    assert parsed.session_id == "session-1"


def test_bus_fan_out_and_unsubscribe() -> None:
    async def scenario() -> None:
        bus = SessionEventBus()
        queue_a = bus.subscribe("s1")
        queue_b = bus.subscribe("s1")
        other = bus.subscribe("s2")

        await bus.publish("s1", AgentMessage(text="Hi, I am U."))
        assert (await queue_a.get()).text == "Hi, I am U."
        assert (await queue_b.get()).text == "Hi, I am U."
        assert other.empty()

        bus.unsubscribe("s1", queue_b)
        await bus.publish("s1", AgentMessage(text="again"))
        assert (await queue_a.get()).text == "again"
        assert queue_b.empty()

    asyncio.run(scenario())
