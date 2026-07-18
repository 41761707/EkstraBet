"""Główny punkt wejścia FastAPI dla warstwy HTTP EkstraBet."""

from __future__ import annotations

import datetime
import logging
import mysql.connector
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.deps import require_auth
from api.routers.analytics import router as analytics_router
from api.routers.auth import router as auth_router
from api.routers.bets import router as bets_router
from api.routers.helper import router as helper_router
from api.routers.leagues import router as leagues_router
from api.routers.matches import router as matches_router
from api.routers.models import router as models_router
from api.routers.odds import router as odds_router
from api.routers.players import router as players_router
from api.routers.predictions import router as predictions_router
from api.routers.teams import router as teams_router
from backend.config import get_settings
from backend.database import test_connection

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Tworzy i konfiguruje aplikację FastAPI z wszystkimi routerami."""
    settings = get_settings()
    cors_origins = settings.cors_origins
    allow_credentials = "*" not in cors_origins

    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
        dependencies=[Depends(require_auth)])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=["*"])

    @app.get("/", tags=["System"])
    async def root() -> dict[str, object]:
        """Zwraca podstawowe metadane API i zarejestrowane moduły."""
        return {
            "message": "EkstraBet API",
            "version": settings.api_version,
            "description": settings.api_description,
            "modules": [
                "auth - Login and session status",
                "leagues - League navigation and metadata",
                "teams - Team management",
                "helper - Reference data (countries, sports, seasons)",
                "models - Prediction model metadata",
                "matches - Match management",
                "odds - Bookmaker odds",
                "predictions - Model predictions",
                "bets - Bet recommendations and EV",
                "analytics - Model effectiveness statistics",
                "players - Player statistics by sport",
                "standings - League tables via /leagues/{id}/standings",
            ],
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
            },
        }

    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        """Zwraca status aplikacji i bazy danych."""
        db_status = "healthy" if test_connection() else "unhealthy"
        status = "healthy" if db_status == "healthy" else "unhealthy"
        return {
            "status": status,
            "database": db_status,
            "timestamp": datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
        }

    app.include_router(auth_router)
    app.include_router(leagues_router)
    app.include_router(teams_router)
    app.include_router(helper_router)
    app.include_router(models_router)
    app.include_router(matches_router)
    app.include_router(odds_router)
    app.include_router(predictions_router)
    app.include_router(bets_router)
    app.include_router(analytics_router)
    app.include_router(players_router)

    @app.exception_handler(mysql.connector.Error)
    async def mysql_exception_handler(request, exc):
        """Mapuje błędy MySQL do HTTP 500."""
        logger.error("MySQL error: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Mapuje nieoczekiwane błędy do HTTP 500."""
        logger.error("Unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")

    return app


app = create_app()
