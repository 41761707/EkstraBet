# Konfiguracja API EkstraBet
# Plik zawiera ustawienia konfiguracyjne dla API
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Klasa konfiguracji API z wykorzystaniem Pydantic BaseSettings"""
    
    # Ustawienia bazy danych
    db_host: str = Field(default="localhost", description="Host bazy danych")
    db_user: str = Field(default="root", description="Użytkownik bazy danych")
    db_password: str = Field(..., description="Hasło do bazy danych - WYMAGANE jako zmienna środowiskowa")
    db_name: str = Field(default="ekstrabet", description="Nazwa bazy danych")
    db_port: int = Field(default=3306, description="Port bazy danych")
    
    # Ustawienia API
    api_title: str = Field(default="EkstraBet Teams API", description="Tytuł API")
    api_description: str = Field(default="API do zarządzania danymi drużyn w systemie EkstraBet", description="Opis API")
    api_version: str = Field(default="1.0.0", description="Wersja API")
    
    # Ustawienia serwera
    host: str = Field(default="0.0.0.0", description="Host serwera")
    port: int = Field(default=8000, description="Port serwera")
    debug: bool = Field(default=False, description="Tryb debug")
    
    # Ustawienia paginacji
    default_page_size: int = Field(default=50, description="Domyślny rozmiar strony")
    max_page_size: int = Field(default=500, description="Maksymalny rozmiar strony")
    
    # Ustawienia logowania
    log_level: str = Field(default="INFO", description="Poziom logowania")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Format logów"
    )
    
    # Ustawienia CORS (na przyszłość)
    cors_origins: list = Field(default=["*"], description="Dozwolone origins dla CORS")
    cors_methods: list = Field(default=["GET", "POST", "PUT", "DELETE"], description="Dozwolone metody CORS")
    
    # Ustawienia uwierzytelniania (na przyszłość)
    secret_key: str = Field(..., description="Klucz tajny - WYMAGANY jako zmienna środowiskowa")
    access_token_expire_minutes: int = Field(default=30, description="Czas życia tokenu w minutach")
    
    # Ustawienia cache (na przyszłość)
    cache_ttl: int = Field(default=300, description="Czas życia cache w sekundach")
    enable_cache: bool = Field(default=False, description="Włączenie cache")
    
    class Config:
        """Konfiguracja Pydantic"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
# Instancja ustawień - do importowania w innych modułach
settings = Settings()

def get_database_url() -> str:
    """Zwraca URL połączenia z bazą danych"""
    return f"mysql+pymysql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"

def get_database_config() -> dict:
    """Zwraca konfigurację bazy danych jako słownik"""
    return {
        "host": settings.db_host,
        "user": settings.db_user,
        "password": settings.db_password,
        "database": settings.db_name,
        "port": settings.db_port,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci"
    }
