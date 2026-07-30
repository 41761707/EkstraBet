"""Application settings loaded from environment variables."""

from __future__ import annotations

import ipaddress
import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent

# JWT i sekrety produkcyjne: minimum 32 bajty/znaki
MIN_SECRET_KEY_LENGTH = 32
MIN_DB_PASSWORD_LENGTH = 8

# exact z .env.example i typowych placeholderów — bez substringów typu "password"
_EXAMPLE_SECRET_EXACT = frozenset({
    "changeme",
    "change-me",
    "replace_me",
    "replace-me",
    "secret",
    "secret_key",
    "secret-key",
    "your-secret",
    "your_secret",
    "generate_a_strong_random_key_at_least_32_chars",
    "test-secret-key-for-unit-tests-only",
    "changeme_to_a_random_secret_at_least_32_chars"
})
_EXAMPLE_SECRET_PREFIXES = (
    "changeme",
    "change-me",
    "replace_me",
    "replace-me",
    "replace_with",
    "generate_a_strong",
    "your-secret",
    "your_secret",
    "test-secret")

_EXAMPLE_PASSWORD_EXACT = frozenset({
    "changeme",
    "change-me",
    "replace_me",
    "replace-me",
    "password",
    "your_database_password",
    "your-database-password",
    "changeme_to_strong_db_password"
})
_EXAMPLE_PASSWORD_PREFIXES = (
    "changeme",
    "change-me",
    "replace_me",
    "replace-me",
    "replace_with",
    "your_database_password",
    "your-database-password")


class Settings(BaseSettings):
    """Shared application configuration for API, backend, and batch jobs."""

    model_config = SettingsConfigDict(
        env_file=(
            REPO_ROOT / ".env",
            REPO_ROOT / "api" / ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore")
    environment: str = Field(
        default="development",
        description="Runtime environment (development/production/test)")
    db_host: str = Field(default="localhost", description="Database host")
    # brak fallbacku root — w produkcji użytkownik musi być jawny i nie-root
    db_user: str = Field(default="", description="Database user")
    db_password: SecretStr = Field(
        ...,
        description="Database password (required environment variable)")
    db_name: str = Field(default="ekstrabet", description="Database name")
    db_port: int = Field(default=3306, description="Database port")
    api_title: str = Field(
        default="EkstraBet Teams API",
        description="API title")
    api_description: str = Field(
        default="API for managing team data in the EkstraBet system",
        description="API description")
    api_version: str = Field(default="1.0.0", description="API version")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    openapi_enabled: bool = Field(
        default=False,
        description="Whether OpenAPI docs endpoints are exposed")
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default=["*"],
        description="Allowed Host header values")
    default_page_size: int = Field(
        default=50,
        description="Default pagination page size")
    max_page_size: int = Field(
        default=500,
        description="Maximum pagination page size")
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string")
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["*"],
        description="Allowed CORS origins")
    cors_methods: Annotated[list[str], NoDecode] = Field(
        default=["GET", "POST", "PUT", "DELETE"],
        description="Allowed CORS methods")
    frontend_origin: str = Field(
        default="http://localhost:3000",
        description="Primary frontend origin for CORS")
    secret_key: SecretStr = Field(
        ...,
        description="Secret key (required environment variable)")
    access_token_expire_minutes: int = Field(
        default=1440,
        description="Access token lifetime in minutes (24h)")
    auth_enabled: bool = Field(
        default=True,
        description="Whether API and UI require authentication")
    auth_cookie_name: str = Field(
        default="ekstrabet_token",
        description="HttpOnly cookie name for the JWT session")
    auth_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm")
    cache_ttl: int = Field(
        default=300,
        description="Cache TTL in seconds")
    enable_cache: bool = Field(
        default=False,
        description="Whether response caching is enabled")
    ekstrabet_ml_preview: bool = Field(
        default=False,
        description="Whether synchronous ML prediction preview is enabled")

    @field_validator(
        "cors_origins",
        "cors_methods",
        "trusted_hosts",
        mode="before")
    @classmethod
    def parse_list_field(cls, value: Any) -> list[str]:
        """Parse comma-separated or JSON list values from .env."""
        if isinstance(value, list):
            return value
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            return [str(item) for item in parsed]
        if stripped == "*":
            return ["*"]
        return [item.strip() for item in stripped.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_production_safety(self) -> Self:
        """Reject unsafe configuration when ENVIRONMENT=production."""
        if self.environment.strip().lower() != "production":
            return self
        errors = _collect_production_errors(self)
        if errors:
            joined = "; ".join(errors)
            raise ValueError(
                f"Unsafe production configuration: {joined}")
        return self


def _looks_like_example_secret(
    value: str,
    exact_values: frozenset[str],
    prefixes: tuple[str, ...]
) -> bool:
    """Return True for known placeholders (exact or prefix), not substrings."""
    lowered = value.strip().lower()
    if not lowered:
        return True
    if lowered in exact_values:
        return True
    return any(lowered.startswith(prefix) for prefix in prefixes)


def _is_public_db_host(host: str) -> bool:
    """Return True when host is a publicly routable IP address."""
    normalized = host.strip().lower()
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return False
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        # nazwa usługi (np. mysql) nie jest publicznym IP
        return False
    return bool(address.is_global)


def _collect_production_errors(settings: Settings) -> list[str]:
    """Build a list of production safety violations."""
    errors: list[str] = []
    secret = settings.secret_key.get_secret_value()
    db_password = settings.db_password.get_secret_value()
    db_user = settings.db_user.strip()

    if not secret:
        errors.append("SECRET_KEY is required")
    elif len(secret) < MIN_SECRET_KEY_LENGTH:
        errors.append(
            f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters")
    elif _looks_like_example_secret(
        secret,
        _EXAMPLE_SECRET_EXACT,
        _EXAMPLE_SECRET_PREFIXES):
        errors.append("SECRET_KEY looks like an example or placeholder value")

    if not db_password:
        errors.append("DB_PASSWORD is required")
    elif len(db_password) < MIN_DB_PASSWORD_LENGTH:
        errors.append(
            f"DB_PASSWORD must be at least {MIN_DB_PASSWORD_LENGTH} characters")
    elif _looks_like_example_secret(
        db_password,
        _EXAMPLE_PASSWORD_EXACT,
        _EXAMPLE_PASSWORD_PREFIXES):
        errors.append("DB_PASSWORD looks like an example or placeholder value")

    if not settings.auth_enabled:
        errors.append("AUTH_ENABLED must be true in production")

    if "*" in settings.cors_origins:
        errors.append("CORS_ORIGINS must not contain '*' in production")

    if settings.debug:
        errors.append("DEBUG must be false in production")

    if settings.openapi_enabled:
        errors.append("OPENAPI_ENABLED must be false in production")

    if settings.ekstrabet_ml_preview:
        errors.append(
            "EKSTRABET_ML_PREVIEW must be false in production")

    if not db_user:
        errors.append("DB_USER must be set explicitly in production")
    elif db_user.lower() == "root":
        errors.append("DB_USER must not be 'root' in production")

    if _is_public_db_host(settings.db_host):
        errors.append(
            "DB_HOST must not be a public IP address in production")

    if not settings.trusted_hosts:
        errors.append("TRUSTED_HOSTS must be set in production")
    elif "*" in settings.trusted_hosts:
        errors.append("TRUSTED_HOSTS must not contain '*' in production")

    return errors


class _LazySettings:
    """Defer settings validation until the first attribute access."""

    def __getattr__(self, name: str) -> object:
        return getattr(get_settings(), name)

    def __repr__(self) -> str:
        return repr(get_settings())


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


settings = _LazySettings()


def get_database_url() -> str:
    """Return SQLAlchemy-style MySQL connection URL."""
    current = get_settings()
    password = current.db_password.get_secret_value()
    return (
        f"mysql+pymysql://{current.db_user}:{password}"
        f"@{current.db_host}:{current.db_port}/{current.db_name}"
    )


def get_database_config() -> dict[str, Any]:
    """Return mysql-connector connection parameters."""
    current = get_settings()
    return {
        "host": current.db_host,
        "user": current.db_user,
        "password": current.db_password.get_secret_value(),
        "database": current.db_name,
        "port": current.db_port,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci"
    }
