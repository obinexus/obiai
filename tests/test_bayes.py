from obiai.demo import build_demo_agent


def test_known_evidence_produces_high_probability() -> None:
    agent = build_demo_agent()
    decision = agent.reason("wet_grass", {"rain": True, "sprinkler": False})
    assert decision.probability == 0.8
    assert decision.state.value == "YES"
