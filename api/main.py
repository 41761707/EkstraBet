"""FastAPI application entry point for the EkstraBet HTTP layer."""

from __future__ import annotations

import datetime
import logging
import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.routers.helper import router as helper_router
from api.routers.leagues import router as leagues_router
from api.routers.matches import router as matches_router
from api.routers.models import router as models_router
from api.routers.odds import router as odds_router
from api.routers.predictions import router as predictions_router
from api.routers.teams import router as teams_router
from backend.config import get_settings
from backend.database import test_connection

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with all routers."""
    settings = get_settings()
    cors_origins = settings.cors_origins
    allow_credentials = "*" not in cors_origins

    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=["*"])

    @app.get("/", tags=["System"])
    async def root() -> dict[str, object]:
        """Return basic API metadata and registered modules."""
        return {
            "message": "EkstraBet API",
            "version": settings.api_version,
            "description": settings.api_description,
            "modules": [
                "leagues - League navigation and metadata",
                "teams - Team management",
                "helper - Reference data (countries, sports, seasons)",
                "models - Prediction model metadata",
                "matches - Match management",
                "odds - Bookmaker odds",
                "predictions - Model predictions",
                "standings - League tables via /leagues/{id}/standings",
            ],
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
            },
        }

    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        """Return application and database health status."""
        db_status = "healthy" if test_connection() else "unhealthy"
        status = "healthy" if db_status == "healthy" else "unhealthy"
        return {
            "status": status,
            "database": db_status,
            "timestamp": datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
        }

    app.include_router(leagues_router)
    app.include_router(teams_router)
    app.include_router(helper_router)
    app.include_router(models_router)
    app.include_router(matches_router)
    app.include_router(odds_router)
    app.include_router(predictions_router)

    @app.exception_handler(mysql.connector.Error)
    async def mysql_exception_handler(request, exc):
        """Map MySQL errors to HTTP 500 responses."""
        logger.error("MySQL error: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Map unexpected errors to HTTP 500 responses."""
        logger.error("Unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")

    return app


app = create_app()
