# Główny moduł startowy API EkstraBet
# Plik odpowiedzialny za inicjalizację aplikacji FastAPI i wszystkich modułów

import os
import sys
import uvicorn
import logging
import datetime
import mysql.connector
from pathlib import Path
import warnings
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api_teams import router as teams_router
from api_helper import router as helper_router
from api_models import router as models_router
from api_matches import router as matches_router
from api_odds import router as odds_router
from api_predictions import router as predictions_router

# Dodaj bieżący katalog do ścieżki Python
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Tworzy i konfiguruje aplikację FastAPI z wszystkimi modułami"""
    
    # Inicjalizacja głównej aplikacji FastAPI
    app = FastAPI(
        title="EkstraBet API",
        description="Kompleksowe API systemu EkstraBet do zarządzania danymi sportowymi",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Konfiguracja CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://localhost:8000",
            "http://127.0.0.1",
            "http://127.0.0.1:8000"
        ],  # W produkcji należy ograniczyć do domeny produkcyjnej
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Endpoint główny
    @app.get("/", tags=["System"])
    async def root():
        """Endpoint główny - informacje o API"""
        return {
            "message": "EkstraBet API",
            "version": "1.0.0",
            "description": "Kompleksowe API systemu EkstraBet",
            "modules": [
                "teams - Zarządzanie drużynami",
                "helper - Dane pomocnicze (kraje, sporty, sezony)",
                "models - Lista modeli",
                "matches - Zarządzanie meczami",
                "odds - Kursy bukmacherskie",
                "predictions - Predykcje modeli",
                # Tutaj będą dodawane kolejne moduły
                # "leagues - Zarządzanie ligami",
            ],
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc"
            }
        }
    
    @app.get("/health", tags=["System"])
    async def health_check():
        """Sprawdzenie stanu aplikacji i połączenia z bazą danych"""
        try:
            # Test połączenia z bazą danych
            import db_module
            conn = db_module.db_connect()
            if conn.is_connected():
                conn.close()
                db_status = "healthy"
            else:
                db_status = "unhealthy"
        except Exception as e:
            logger.error(f"Błąd połączenia z bazą danych: {e}")
            db_status = "unhealthy"
        
        return {
            "status": "healthy" if db_status == "healthy" else "unhealthy",
            "database": db_status,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    
    # Rejestracja routerów modułów
    app.include_router(teams_router)
    app.include_router(helper_router)
    app.include_router(models_router)
    app.include_router(matches_router)
    app.include_router(odds_router)
    app.include_router(predictions_router)
    
    # Tutaj będą dodawane kolejne moduły:
    # app.include_router(leagues_router)
    
    # Globalna obsługa błędów
    @app.exception_handler(mysql.connector.Error)
    async def mysql_exception_handler(request, exc):
        """Obsługa błędów MySQL"""
        logger.error(f"Błąd MySQL: {exc}")
        raise HTTPException(status_code=500, detail="Błąd bazy danych")

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Obsługa ogólnych błędów"""
        logger.error(f"Nieoczekiwany błąd: {exc}")
        raise HTTPException(status_code=500, detail="Wewnętrzny błąd serwera")
    
    return app

# Utworzenie globalnej instancji aplikacji dla uvicorn
app = create_app()

def main():
    """Główna funkcja startowa"""
    # Wyłączenie ostrzeżenia Pandas o SQLAlchemy connectable
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message="pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy."
    )
    print("Uruchamianie EkstraBet API...")
    print("=" * 60)
    
    # Konfiguracja serwera
    config = {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,  # Automatyczne przeładowanie przy zmianach
        "log_level": "info",
        "access_log": True
    }
    
    print(f"Serwer będzie dostępny pod adresem: http://localhost:{config['port']}")
    print(f"Dokumentacja API: http://localhost:{config['port']}/docs")
    print(f"ReDoc: http://localhost:{config['port']}/redoc")
    print(f"Health Check: http://localhost:{config['port']}/health")
    print("Dostępne moduły:")
    print("   • /teams - Zarządzanie drużynami")
    print("   • /helper - Informacje z tabel pomocniczych (kraje, sezony itd.)")
    print("   • /models - Lista modeli")
    print("   • /matches - Zarządzanie meczami")
    print("   • /odds - Kursy bukmacherskie")
    print("   • /predictions - Predykcje modeli")
    # print("   • /leagues - Zarządzanie ligami")  # Przyszłe moduły
    print("=" * 60)
    
    try:
        # Uruchomienie serwera z string importem dla reload
        uvicorn.run("start_api:app", **config)
    except KeyboardInterrupt:
        print("\n👋 Zamykanie serwera...")
    except Exception as e:
        print(f"❌ Błąd uruchomienia serwera: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
