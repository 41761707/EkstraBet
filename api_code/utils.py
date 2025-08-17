"""
Moduł utils - wspólne funkcje dla wszystkich modułów API
"""

from fastapi import HTTPException
import mysql.connector
import db_module
import pandas as pd
import logging
from contextlib import contextmanager
from typing import Optional

# Konfiguracja logowania
logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """
    Context manager do zarządzania połączeniami z bazą danych
    
    Funkcja zapewnia bezpieczne zarządzanie połączeniami z bazą danych MySQL.
    Automatycznie zamyka połączenie po zakończeniu operacji lub w przypadku błędu.
    
    Yields:
        mysql.connector.connection: Połączenie z bazą danych
        
    Raises:
        HTTPException: W przypadku błędu połączenia z bazą danych
    """
    conn = None
    try:
        conn = db_module.db_connect()
        yield conn
    except mysql.connector.Error as e:
        logger.error(f"Błąd połączenia z bazą danych: {e}")
        raise HTTPException(status_code=500, detail="Błąd połączenia z bazą danych")
    finally:
        if conn and conn.is_connected():
            conn.close()

def execute_query(query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """
    Wykonuje zapytanie SQL i zwraca wynik jako DataFrame
    
    Funkcja wykonuje zapytanie SQL używając bezpiecznego context managera
    dla połączenia z bazą danych i zwraca wynik w postaci pandas DataFrame.
    
    Args:
        query (str): Zapytanie SQL do wykonania
        params (Optional[tuple]): Parametry do zapytania SQL (opcjonalne)
        
    Returns:
        pd.DataFrame: Wynik zapytania jako DataFrame
        
    Raises:
        HTTPException: W przypadku błędu wykonania zapytania
    """
    with get_db_connection() as conn:
        try:
            return pd.read_sql(query, conn, params=params)
        except Exception as e:
            logger.error(f"Błąd wykonania zapytania: {e}")
            raise HTTPException(status_code=500, detail="Błąd wykonania zapytania")
