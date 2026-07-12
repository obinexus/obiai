"""U API package.

``app`` is created at import time so ``uvicorn obiai.api:app`` (the original
Makefile invocation) keeps working; ``create_app`` stays side-effect-free for
tests and embedding.
"""

from obiai.api.app import create_app

app = create_app()

__all__ = ["app", "create_app"]
