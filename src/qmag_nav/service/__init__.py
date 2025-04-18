"""Public service API – re‑export FastAPI *app* for easy uvicorn usage."""

from qmag_nav.service.api import app

__all__ = ["app"]
