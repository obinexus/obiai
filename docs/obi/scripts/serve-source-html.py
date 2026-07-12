#!/usr/bin/env python3
"""Serve docs/source so generated HTML can link to source PDFs and assets."""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "source"


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class SourceHtmlRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        emit(f"{self.address_string()} - {format % args}")


def emit(message: str) -> None:
    try:
        print(message)
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    handler = functools.partial(SourceHtmlRequestHandler, directory=str(SOURCE))
    with ReusableTCPServer((args.host, args.port), handler) as server:
        emit(f"Serving OBI source HTML at http://{args.host}:{args.port}/html/")
        emit("Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            emit("\nServer stopped.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        error_log = ROOT / ".codex-source-html-server.err.log"
        error_log.write_text(traceback.format_exc(), encoding="utf-8")
        raise
