"""``obiai model status`` / ``obiai model reload``.

Split cleanly in two concerns: the on-disk artifact manifest (always
readable, no running server required) and a best-effort call to a live
``uai serve`` process to report whether *that* process has actually loaded
the run -- the CLI and the server are separate OS processes, so the only
honest way to know what a running service has loaded is to ask it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from rich.console import Console
from rich.table import Table

from obiai.core.config import load_settings
from obiai.training.artifacts import default_artifact_root, load_artifact_descriptor, read_current

__all__ = ["model_reload", "model_status"]

console = Console()


def _server_url(host: str | None, port: int | None) -> str:
    settings = load_settings().u.server
    return f"http://{host or settings.host}:{port or settings.port}"


def _get_json(url: str, *, timeout: float = 1.5) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 - local trusted URL
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def _post_json(url: str, *, timeout: float = 120.0) -> dict[str, Any] | None:
    request = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def model_status(*, host: str | None = None, port: int | None = None) -> None:
    artifact_root = default_artifact_root()
    current = read_current(artifact_root)

    table = Table(title="UAI trained model status")
    table.add_column("Field")
    table.add_column("Value")

    if current is None:
        table.add_row("Active run ID", "[yellow]none registered yet[/yellow]")
        table.add_row("Last training status", "no runs found - try `obiai train uai --fast`")
    else:
        table.add_row("Active run ID", current.run_id)
        table.add_row("Last training status", current.status)
        try:
            descriptor = load_artifact_descriptor(
                artifact_root / current.model_path, artifact_root=artifact_root
            )
            table.add_row("Base model", descriptor.base_model)
            table.add_row("Adapter path", str(artifact_root / descriptor.adapter_path))
            table.add_row("Tokenizer path", str(artifact_root / descriptor.tokenizer_path))
            table.add_row("Artifact schema version", str(descriptor.schema_version))
        except Exception as exc:  # noqa: BLE001 - status reports, never crashes
            table.add_row("Descriptor", f"[red]failed to load: {exc}[/red]")

    url = _server_url(host, port)
    live = _get_json(f"{url}/model/status")
    if live is None:
        table.add_row("Running service", f"[yellow]not reachable at {url}[/yellow]")
    else:
        loaded_run_id = live.get("loaded_run_id")
        matches = current is not None and loaded_run_id == current.run_id
        table.add_row(
            "Running service has loaded this run",
            "[green]yes[/green]" if matches else f"[yellow]no (loaded_run_id={loaded_run_id!r})[/yellow]",
        )

    console.print(table)


def model_reload(*, host: str | None = None, port: int | None = None) -> None:
    url = _server_url(host, port)
    result = _post_json(f"{url}/model/reload")
    if result is None:
        console.print(
            f"[red]Could not reach a running service at {url}.[/red] "
            "Start it with `uai serve` first."
        )
        raise SystemExit(1)
    if result.get("error"):
        console.print(f"[red]Reload failed:[/red] {result['error']}")
        raise SystemExit(1)
    if result.get("reloaded"):
        console.print(f"[green]Reloaded.[/green] Now serving run_id={result.get('run_id')!r}.")
    else:
        console.print(f"Already up to date (run_id={result.get('run_id')!r}).")
