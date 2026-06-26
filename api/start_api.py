"""Legacy launcher; prefer `uvicorn api.main:app` from the repository root."""

from __future__ import annotations

import logging
import sys
import warnings

import uvicorn

from api.main import app, create_app
from backend.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

__all__ = ["app", "create_app", "main"]


def main() -> None:
    """Start the API server with uvicorn."""
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message=(
            "pandas only supports SQLAlchemy connectable "
            "(engine/connection) or database string URI or sqlite3 DBAPI2 "
            "connection. Other DBAPI2 objects are not tested. Please "
            "consider using SQLAlchemy."))
    settings = get_settings()
    print("Starting EkstraBet API...")
    print("=" * 60)
    print(f"Server URL: http://localhost:{settings.port}")
    print(f"API docs: http://localhost:{settings.port}/docs")
    print(f"ReDoc: http://localhost:{settings.port}/redoc")
    print(f"Health check: http://localhost:{settings.port}/health")
    print("=" * 60)
    try:
        uvicorn.run(
            "api.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as exc:
        print(f"Failed to start server: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
