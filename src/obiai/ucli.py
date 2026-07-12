"""``uai`` — the U command line.

The CLI executable is ``uai``; the conversational assistant it serves is
named U.
"""

from __future__ import annotations

import importlib
import json
import socket
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

import obiai
from obiai.agents import build_u_engine, render_agent_message
from obiai.core.config import Settings, load_settings
from obiai.core.models import Observation

app = typer.Typer(help="U — Ontological Bayesian Video Intelligence", no_args_is_help=True)
console = Console()

EXPECTED_DEMO_POSTERIOR = 943 / 1010


def _settings(config: Optional[Path]) -> Settings:
    return load_settings(config) if config else load_settings()


@app.command()
def serve(
    config: Optional[Path] = typer.Option(None, help="Path to a config YAML."),
    host: Optional[str] = typer.Option(None, help="Override the configured host."),
    port: Optional[int] = typer.Option(None, help="Override the configured port."),
    reload: bool = typer.Option(False, help="Auto-reload on code changes (dev only)."),
) -> None:
    """Start the U backend (REST + WebSocket)."""
    import uvicorn

    settings = _settings(config)
    uvicorn.run(
        "obiai.api:app",
        host=host or settings.u.server.host,
        port=port or settings.u.server.port,
        reload=reload,
    )


@app.command()
def demo(config: Optional[Path] = typer.Option(None, help="Path to a config YAML.")) -> None:
    """Run the raised-hand vertical slice end to end and print the decision."""
    engine = build_u_engine(_settings(config))
    observation = Observation(
        session_id="demo-session",
        modality="vision",
        event_type="participant_raised_hand",
        value=True,
        confidence=0.9,
        source="browser_hand_classifier",
    )
    decision = engine.reason("demo-session", observation)
    console.print_json(json.dumps(decision.model_dump(mode="json"), indent=2))
    message = render_agent_message(decision)
    if message:
        console.print(f"\n[bold]U:[/bold] {message}")


@app.command()
def reason(
    event_type: str = typer.Option("participant_raised_hand", help="Observable event type."),
    value: bool = typer.Option(True, help="Observed value."),
    confidence: float = typer.Option(0.9, min=0.0, max=1.0, help="Classifier confidence."),
    config: Optional[Path] = typer.Option(None, help="Path to a config YAML."),
) -> None:
    """Reason over a single observation and print the auditable decision."""
    engine = build_u_engine(_settings(config))
    observation = Observation(
        session_id="cli-session",
        modality="vision",
        event_type=event_type,
        value=value,
        confidence=confidence,
        source="cli",
    )
    decision = engine.reason("cli-session", observation)
    console.print_json(json.dumps(decision.model_dump(mode="json"), indent=2))


@app.command()
def doctor(config: Optional[Path] = typer.Option(None, help="Path to a config YAML.")) -> None:
    """Check that the environment can run U."""
    table = Table(title=f"uai doctor — obiai-u {obiai.__version__}")
    table.add_column("Check")
    table.add_column("Result")
    failures = 0

    def check(name: str, ok: bool, detail: str = "", warn_only: bool = False) -> None:
        nonlocal failures
        if ok:
            table.add_row(name, f"[green]OK[/green] {detail}")
        elif warn_only:
            table.add_row(name, f"[yellow]WARN[/yellow] {detail}")
        else:
            failures += 1
            table.add_row(name, f"[red]FAIL[/red] {detail}")

    check(
        "Python >= 3.11",
        sys.version_info >= (3, 11),
        f"({sys.version.split()[0]})",
    )

    for module in ("numpy", "scipy", "networkx", "pydantic", "fastapi", "uvicorn", "yaml"):
        try:
            importlib.import_module(module)
            check(f"import {module}", True)
        except ImportError as exc:
            check(f"import {module}", False, str(exc))

    try:
        settings = _settings(config)
        check("config loads", True, f"(assistant: {settings.agent.name})")
    except Exception as exc:  # noqa: BLE001 — doctor reports, never crashes
        settings = Settings()
        check("config loads", False, str(exc))

    try:
        engine = build_u_engine(settings)
        observation = Observation(
            session_id="doctor",
            modality="vision",
            event_type="participant_raised_hand",
            value=True,
            confidence=0.9,
            source="doctor",
        )
        posterior = engine.reason("doctor", observation).probability
        check(
            "demo posterior sanity",
            abs(posterior - EXPECTED_DEMO_POSTERIOR) < 1e-9,
            f"(P={posterior:.6f}, expected {EXPECTED_DEMO_POSTERIOR:.6f})",
        )
    except Exception as exc:  # noqa: BLE001
        check("demo posterior sanity", False, str(exc))

    host, port = settings.u.server.host, settings.u.server.port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        in_use = sock.connect_ex((host, port)) == 0
    check(
        f"port {host}:{port} free",
        not in_use,
        "(something is already listening)" if in_use else "",
        warn_only=True,
    )

    import shutil

    for tool in ("node", "npm"):
        check(f"{tool} on PATH", shutil.which(tool) is not None, "(needed for web UI)", warn_only=True)

    console.print(table)
    if failures:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
