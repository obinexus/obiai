import pytest
from fastapi.testclient import TestClient

from obiai.api.app import create_app
from obiai.core.config import Settings


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(Settings()))


OBSERVATION = {
    "modality": "vision",
    "event_type": "participant_raised_hand",
    "value": True,
    "confidence": 0.9,
    "source": "browser_hand_classifier",
}


def _create_session(client: TestClient) -> str:
    response = client.post("/sessions")
    assert response.status_code == 201
    return response.json()["session_id"]


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_reports_modules(client: TestClient) -> None:
    payload = client.get("/version").json()
    assert payload["assistant"] == "U"
    assert payload["name"] == "obiai-u"
    assert payload["loaded_modules"] == ["echo"]
    assert payload["u_model"]["artifact_name"] == "obi-uagentic-0.1.0.pkl"


def test_uagentic_model_profile_endpoint(client: TestClient) -> None:
    payload = client.get("/model/uagentic").json()
    assert payload["model_id"] == "obi-uagentic"
    assert payload["version"] == "0.1.0"
    assert payload["training_state"] == "bootstrap-untrained"
    assert payload["source_count"] >= 5
    assert payload["concept_count"] >= 5
    assert "raw training files remain outside web/public" in payload["separation_contract"]


def test_ontology_endpoints(client: TestClient) -> None:
    concepts = {c["name"] for c in client.get("/ontology/concepts").json()}
    assert {"vision.hand_raise", "communication.request_turn", "disability"} <= concepts
    relations = client.get("/ontology/relations").json()
    assert {
        "subject": "communication.request_turn",
        "relation": "supports",
        "object": "participant_requests_turn",
    } in relations


def test_session_crud(client: TestClient) -> None:
    session_id = _create_session(client)
    fetched = client.get(f"/sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["session_id"] == session_id

    assert client.delete(f"/sessions/{session_id}").status_code == 204
    assert client.get(f"/sessions/{session_id}").status_code == 404
    assert client.delete(f"/sessions/{session_id}").status_code == 404


def test_observation_produces_decision(client: TestClient) -> None:
    session_id = _create_session(client)
    response = client.post(f"/sessions/{session_id}/observations", json=OBSERVATION)
    assert response.status_code == 201
    payload = response.json()
    decision = payload["decision"]
    assert decision["probability"] == pytest.approx(943 / 1010)
    assert decision["state"] == "YES"
    assert decision["action"]["name"] == "announce_hand_raise"
    assert decision["bias_audit"]["passed"] is True
    assert decision["safety_audit"]["passed"] is True
    assert payload["observation"]["session_id"] == session_id

    decisions = client.get(f"/sessions/{session_id}/decisions").json()
    assert len(decisions) == 1

    rerun = client.post(f"/sessions/{session_id}/reason")
    assert rerun.status_code == 200
    assert rerun.json()["probability"] == pytest.approx(943 / 1010)


def test_disallowed_event_type_is_422(client: TestClient) -> None:
    session_id = _create_session(client)
    bad = dict(OBSERVATION, event_type="participant_is_deceptive")
    response = client.post(f"/sessions/{session_id}/observations", json=bad)
    assert response.status_code == 422
    assert "allowlist" in response.json()["detail"]


def test_oversized_value_is_422(client: TestClient) -> None:
    session_id = _create_session(client)
    bad = dict(OBSERVATION, value="x" * 100_000)
    response = client.post(f"/sessions/{session_id}/observations", json=bad)
    assert response.status_code == 422


def test_reason_without_observations_is_409(client: TestClient) -> None:
    session_id = _create_session(client)
    assert client.post(f"/sessions/{session_id}/reason").status_code == 409


def test_unknown_session_is_404(client: TestClient) -> None:
    assert client.get("/sessions/ghost").status_code == 404
    assert (
        client.post("/sessions/ghost/observations", json=OBSERVATION).status_code == 404
    )


def test_legacy_reason_endpoint_still_works(client: TestClient) -> None:
    response = client.post(
        "/reason",
        json={"proposition": "wet_grass", "evidence": {"rain": True, "sprinkler": False}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["probability"] == pytest.approx(0.8)
    assert payload["state"] == "YES"


def test_chat_uses_uagentic_model_profile(client: TestClient) -> None:
    session_id = _create_session(client)
    with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
        ws.receive_json()
        ws.send_json({"type": "chat.message", "text": "What is unbiased AI?"})
        reply = ws.receive_json()
    assert reply["type"] == "agent.message"
    assert "bias/confounding parameter phi" in reply["text"]
