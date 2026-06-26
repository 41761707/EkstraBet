"""Shared helpers for API routers."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from fastapi import HTTPException

from backend.database import get_db_connection

logger = logging.getLogger(__name__)


def execute_query(query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """Run SQL and return the result as a DataFrame."""
    with get_db_connection() as conn:
        try:
            return pd.read_sql(query, conn, params=params)
        except Exception as exc:
            logger.error("Query execution failed: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="Database query failed") from exc
