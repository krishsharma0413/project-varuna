"""ASGI entry point: `uvicorn main:app`."""

from app.api.factory import create_app

app = create_app()
