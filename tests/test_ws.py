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


def test_chat_raised_hand_prompt_runs_governed_decision_trace(client: TestClient) -> None:
    session_id = _session(client)
    with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
        ws.receive_json()  # session.ready

        ws.send_json(
            {
                "type": "chat.message",
                "text": (
                    "U, a participant raises their hand with 0.90 confidence. "
                    "Explain your decision using observable evidence only, then show "
                    "the posterior, uncertainty, semantic path, bias audit, safety audit, "
                    "and final action."
                ),
            }
        )
        events = [ws.receive_json() for _ in range(5)]

    assert [event["type"] for event in events] == [
        "observation.created",
        "reasoning.started",
        "decision.created",
        "audit.created",
        "agent.message",
    ]
    decision = events[2]["decision"]
    reply = events[4]["text"]
    assert decision["probability"] == pytest.approx(943 / 1010)
    assert decision["action"]["name"] == "announce_hand_raise"
    assert "Observable evidence only" in reply
    assert "Posterior P(participant_requests_turn) = 0.9337" in reply
    assert "uncertainty = 0.1327" in reply
    assert "Semantic path: observation.hand_raised -> communication.request_turn" in reply
    assert "Bias audit: passed" in reply
    assert "Safety audit: passed" in reply
    assert "Final action: announce_hand_raise" in reply
    assert events[4]["response_source"] == "governance_pipeline"
    assert events[4]["adapter_loaded"] is False


def test_chat_general_question_reports_seeded_fallback_when_no_trained_model(
    client: TestClient,
) -> None:
    """No trained UAI model is registered in the isolated test artifact root.

    A general question must be answered by the seeded router, and must
    honestly report that -- never claim response_source="trained_uai" when
    no adapter was actually loaded.
    """
    session_id = _session(client)
    with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
        ws.receive_json()  # session.ready
        ws.send_json({"type": "chat.message", "text": "what is OBI"})
        reply = ws.receive_json()

    assert reply["type"] == "agent.message"
    assert reply["response_source"] == "seeded_uagentic"
    assert reply["adapter_loaded"] is False
    assert reply["model_run_id"] is None


def test_chat_with_ready_trained_model_reports_thinking_before_reply() -> None:
    class _FakeUAIModels:
        active_run_id = "run-1"

        def status(self):
            return {
                "current_run_id": "run-1",
                "current_status": "ready",
                "loaded_run_id": "run-1",
                "loaded": True,
            }

        def try_generate(self, prompt: str):
            return (f"trained reply for {prompt}", "run-1")

    app = create_app(Settings())
    app.state.service.uai_models = _FakeUAIModels()
    client = TestClient(app)

    session_id = _session(client)
    with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
        ws.receive_json()  # session.ready
        ws.send_json({"type": "chat.message", "text": "what is OBIAI"})
        thinking = ws.receive_json()
        reply = ws.receive_json()

    assert thinking["type"] == "agent.thinking"
    assert thinking["model_run_id"] == "run-1"
    assert reply["type"] == "agent.message"
    assert reply["response_source"] == "trained_uai"
    assert reply["adapter_loaded"] is True
    assert reply["model_run_id"] == "run-1"


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


def test_voice_transcript_flow(client: TestClient) -> None:
    session_id = _session(client)
    with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
        ws.receive_json()  # session.ready
        ws.send_json({"type": "session.start"})
        ws.receive_json()  # greeting

        ws.send_json(
            {
                "type": "transcript.partial",
                "segment": {
                    "text": "can you inspect",
                    "start_ms": 0,
                    "end_ms": 800,
                    "confidence": 0.7,
                    "final": False,
                },
            }
        )
        partial_echo = ws.receive_json()
        assert partial_echo["type"] == "transcript.partial"
        assert partial_echo["segment"]["text"] == "can you inspect"

        ws.send_json(
            {
                "type": "transcript.final",
                "segment": {
                    "text": "can you inspect this error",
                    "start_ms": 0,
                    "end_ms": 1600,
                    "confidence": 0.92,
                    "final": True,
                },
            }
        )
        final_echo = ws.receive_json()
        assert final_echo["type"] == "transcript.final"
        assert final_echo["segment"]["text"] == "can you inspect this error"

        reply = ws.receive_json()
        assert reply["type"] == "agent.message"

    # Partial transcripts are never persisted; final ones are, alongside the
    # greeting and U's reply.
    transcript = client.get(f"/sessions/{session_id}").json()["transcript"]
    assert [entry["text"] for entry in transcript] == [
        "Hi, I am U.",
        "can you inspect this error",
        reply["text"],
    ]
    assert [entry["role"] for entry in transcript] == ["u", "user", "u"]


def test_unknown_session_closes_with_4404(client: TestClient) -> None:
    with client.websocket_connect("/ws/sessions/ghost") as ws:
        with pytest.raises(Exception) as excinfo:
            ws.receive_json()
        assert "4404" in str(excinfo.value) or getattr(excinfo.value, "code", None) == 4404
