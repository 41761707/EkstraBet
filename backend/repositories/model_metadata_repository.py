"""SQL queries for prediction model metadata (not ML pipeline artifacts).

This module reads from the database MODELS table and related event-family
tables. It is intentionally named model_metadata to avoid confusion with
the repository-level ``models/`` directory used for ML training.
"""

from __future__ import annotations

import pandas as pd

from backend.database import get_db_connection


def fetch_event_families(sport_id: int | None = None) -> pd.DataFrame:
    """Return event families with optional sport filter."""
    query = """
        SELECT
            ef.id,
            ef.sport_id,
            ef.name,
            ef.description,
            s.name AS sport_name
        FROM event_families ef
        LEFT JOIN sports s ON ef.sport_id = s.id
    """
    params: tuple[object, ...] | None = None
    if sport_id is not None:
        query += " WHERE ef.sport_id = %s"
        params = (sport_id,)
    query += " ORDER BY ef.id"
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_family_events(family_id: int) -> pd.DataFrame:
    """Return events mapped to the given event family."""
    query = """
        SELECT
            efm.id,
            efm.event_id,
            efm.event_family_id,
            e.name AS event_name,
            ef.name AS family_name
        FROM event_family_mappings efm
        LEFT JOIN events e ON efm.event_id = e.id
        LEFT JOIN event_families ef ON efm.event_family_id = ef.id
        WHERE efm.event_family_id = %s
        ORDER BY e.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(family_id,))


def fetch_models() -> pd.DataFrame:
    """Return all prediction models with sport metadata."""
    query = """
        SELECT
            m.id,
            m.name,
            m.active,
            m.sport_id,
            s.name AS sport_name
        FROM models m
        LEFT JOIN sports s ON m.sport_id = s.id
        ORDER BY m.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn)


def fetch_model_by_id(model_id: int) -> pd.DataFrame:
    """Return a single model row or an empty frame."""
    query = """
        SELECT
            m.id,
            m.name,
            m.active,
            m.sport_id,
            s.name AS sport_name
        FROM models m
        LEFT JOIN sports s ON m.sport_id = s.id
        WHERE m.id = %s
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(model_id,))


def fetch_model_event_families(model_id: int) -> pd.DataFrame:
    """Return event families supported by the model."""
    query = """
        SELECT
            ef.id,
            ef.name,
            ef.sport_id
        FROM event_families ef
        JOIN event_model_families emf ON ef.id = emf.event_family_id
        WHERE emf.model_id = %s
        ORDER BY ef.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(model_id,))


def fetch_model_supported_events(model_id: int) -> pd.DataFrame:
    """Return events supported by the model through family mappings."""
    query = """
        SELECT DISTINCT
            e.id,
            e.name,
            ef.name AS family_name,
            ef.id AS family_id
        FROM events e
        JOIN event_family_mappings efm ON e.id = efm.event_id
        JOIN event_families ef ON efm.event_family_id = ef.id
        JOIN event_model_families emf ON ef.id = emf.event_family_id
        WHERE emf.model_id = %s
        ORDER BY ef.name, e.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(model_id,))
