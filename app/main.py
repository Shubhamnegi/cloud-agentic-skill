"""
FastAPI application — the single entrypoint for the backend.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_orchestrator, init_services
from app.api.routes import api_keys, auth, mcp, skills
from app.core.config import get_settings
from app.services.orchestrator import SkillOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)-30s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    init_services()
    logger.info("Backend ready.")
    yield
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="Recursive Agentic Skill Management API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — allow Streamlit and other local UIs
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(skills.router)
    app.include_router(auth.router)
    app.include_router(mcp.router)
    app.include_router(api_keys.router)

    # Health-check
    @app.get("/health", tags=["system"])
    def health(orch: SkillOrchestrator = Depends(get_orchestrator)):
        return orch.health()

    return app


app = create_app()
