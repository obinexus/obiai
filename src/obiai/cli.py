from __future__ import annotations

import json
import typer
from rich import print
from .demo import build_demo_agent

app = typer.Typer(help="OBI Ontological Bayesian Intelligence CLI")


def parse_evidence(items: list[str]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for item in items:
        key, sep, raw = item.partition("=")
        if not sep or raw.lower() not in {"true", "false"}:
            raise typer.BadParameter("Evidence must use name=true or name=false")
        result[key] = raw.lower() == "true"
    return result


@app.command()
def demo() -> None:
    agent = build_demo_agent()
    decision = agent.reason("wet_grass", {"rain": True, "sprinkler": False})
    print(json.dumps(decision.model_dump(mode="json"), indent=2))


@app.command()
def reason(
    proposition: str = typer.Option("wet_grass", help="Binary target variable"),
    evidence: list[str] = typer.Option([], "--evidence", "-e"),
) -> None:
    agent = build_demo_agent()
    decision = agent.reason(proposition, parse_evidence(evidence))
    print(json.dumps(decision.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    app()
