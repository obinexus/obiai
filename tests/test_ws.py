import pytest
from fastapi.testclient import TestClient

from obiai.api.app import create_app
from obiai.core.config import Settings


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(Settings()))


OBSERVATION_SUBMIT = {
    "type": "observation.submit",
    "observation": {
        "modality": "vision",
        "event_type": "participant_raised_hand",
        "value": True,
        "confidence": 0.9,
        "source": "browser_hand_classifier",
    },
}


def _session(client: TestClient) -> str:
    return client.post("/sessions").json()["session_id"]


def test_ready_greeting_and_observation_flow(client: TestClient) -> None:
    session_id = _session(client)
    with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
        ready = ws.receive_json()
        assert ready == {"type": "session.ready", "session_id": session_id}

        ws.send_json({"type": "session.start"})
        greeting = ws.receive_json()
        assert greeting["type"] == "agent.message"
        assert greeting["text"] == "Hi, I am U."

        ws.send_json(OBSERVATION_SUBMIT)
        events = [ws.receive_json() for _ in range(5)]
        assert [e["type"] for e in events] == [
            "observation.created",
            "reasoning.started",
            "decision.created",
            "audit.created",
            "agent.message",
        ]
        decision = events[2]["decision"]
        assert decision["state"] == "YES"
        assert decision["probability"] == pytest.approx(943 / 1010)
        assert events[4]["text"] == "A participant appears to be requesting a turn to speak."


def test_invalid_event_keeps_connection_alive(client: TestClient) -> None:
    session_id = _session(client)
    with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
        ws.receive_json()  # session.ready

        ws.send_text("not json at all")
        error = ws.receive_json()
        assert error["type"] == "error"

        ws.send_json({"type": "media.video.frame", "data": "zzz"})
        error = ws.receive_json()
        assert error["type"] == "error"

        # Still alive: a valid event flows normally.
        ws.send_json({"type": "chat.message", "text": "hello"})
        reply = ws.receive_json()
        assert reply["type"] == "agent.message"


def test_disallowed_observation_yields_error_event(client: TestClient) -> None:
    session_id = _session(client)
    with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
        ws.receive_json()  # session.ready
        bad = {
            "type": "observation.submit",
            "observation": dict(
                OBSERVATION_SUBMIT["observation"], event_type="participant_is_deceptive"
            ),
        }
        ws.send_json(bad)
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "rejected"


def test_unknown_session_closes_with_4404(client: TestClient) -> None:
    with client.websocket_connect("/ws/sessions/ghost") as ws:
        with pytest.raises(Exception) as excinfo:
            ws.receive_json()
        assert "4404" in str(excinfo.value) or getattr(excinfo.value, "code", None) == 4404
