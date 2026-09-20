"""FastAPI application entrypoint for the PixelArt Trip Planner backend.

Foundation scaffolding: creates the FastAPI app, loads settings from the
environment, and wires in the route modules. The health endpoint itself is
implemented in Task 12.2; the router is included here so wiring is complete and
the app boots cleanly.

Run locally with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.api.routes import health
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

# Route includes. health.router is an empty router in the Foundation stub and
# gains GET /health in Task 12.2 — including it here keeps main.py stable.
app.include_router(health.router)
