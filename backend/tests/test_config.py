"""Tests for backend.config."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from backend.config import Settings, get_database_config, get_settings


_VALID_PRODUCTION_ENV = {
    "ENVIRONMENT": "production",
    "DEBUG": "false",
    "OPENAPI_ENABLED": "false",
    "AUTH_ENABLED": "true",
    "EKSTRABET_ML_PREVIEW": "false",
    "DB_HOST": "mysql",
    "DB_USER": "ekstrabet_api",
    "DB_PASSWORD": "strong-db-pass-9f3a",
    "SECRET_KEY": "a" * 32 + "-prod-secret-value",
    "CORS_ORIGINS": '["https://example.com"]',
    "TRUSTED_HOSTS": '["api","localhost"]'
}


class TestSettings(unittest.TestCase):
    """Unit tests for application settings."""

    required_env = {
        "DB_PASSWORD": "test-db-password",
        "SECRET_KEY": "test-secret-key-for-unit-tests-only"
    }

    def tearDown(self) -> None:
        get_settings.cache_clear()

    def test_loads_required_fields_from_environment(self) -> None:
        with patch.dict(os.environ, self.required_env, clear=False):
            get_settings.cache_clear()
            current = get_settings()
            self.assertEqual(current.db_host, "localhost")
            self.assertEqual(current.db_name, "ekstrabet")
            self.assertEqual(current.default_page_size, 50)
            self.assertEqual(current.max_page_size, 500)
            self.assertEqual(current.cache_ttl, 300)
            self.assertFalse(current.enable_cache)
            self.assertEqual(current.environment, "development")
            self.assertFalse(current.openapi_enabled)

    def test_parses_cors_origins_from_comma_separated_string(self) -> None:
        env = {
            **self.required_env,
            "CORS_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000"
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            current = get_settings()
            self.assertEqual(
                current.cors_origins,
                ["http://localhost:3000", "http://127.0.0.1:3000"])

    def test_secrets_are_not_exposed_in_repr(self) -> None:
        with patch.dict(os.environ, self.required_env, clear=False):
            get_settings.cache_clear()
            current = get_settings()
            rendered = repr(current)
            self.assertNotIn("test-db-password", rendered)
            self.assertNotIn("test-secret-key-for-unit-tests-only", rendered)

    def test_get_database_config_returns_connection_parameters(self) -> None:
        env = {
            **self.required_env,
            "DB_HOST": "db.example.com",
            "DB_USER": "app_user",
            "DB_NAME": "ekstrabet_test",
            "DB_PORT": "3307"
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            config = get_database_config()
            self.assertEqual(config["host"], "db.example.com")
            self.assertEqual(config["user"], "app_user")
            self.assertEqual(config["password"], "test-db-password")
            self.assertEqual(config["database"], "ekstrabet_test")
            self.assertEqual(config["port"], 3307)
            self.assertEqual(config["charset"], "utf8mb4")

    def test_settings_model_can_be_instantiated_directly(self) -> None:
        current = Settings(
            db_password="direct-password",
            secret_key="direct-secret-key",
            db_user="app_user")
        self.assertEqual(current.frontend_origin, "http://localhost:3000")
        self.assertEqual(current.db_user, "app_user")
        self.assertFalse(current.openapi_enabled)

    def test_production_accepts_safe_configuration(self) -> None:
        with patch.dict(os.environ, _VALID_PRODUCTION_ENV, clear=False):
            get_settings.cache_clear()
            current = get_settings()
            self.assertEqual(current.environment, "production")
            self.assertTrue(current.auth_enabled)
            self.assertFalse(current.debug)
            self.assertFalse(current.openapi_enabled)
            self.assertEqual(current.db_user, "ekstrabet_api")

    def test_production_rejects_wildcard_cors(self) -> None:
        env = {**_VALID_PRODUCTION_ENV, "CORS_ORIGINS": '["*"]'}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("CORS_ORIGINS", str(ctx.exception))

    def test_production_rejects_root_db_user(self) -> None:
        env = {**_VALID_PRODUCTION_ENV, "DB_USER": "root"}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("DB_USER", str(ctx.exception))

    def test_production_rejects_missing_db_user(self) -> None:
        env = {**_VALID_PRODUCTION_ENV, "DB_USER": ""}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("DB_USER", str(ctx.exception))

    def test_production_rejects_disabled_auth(self) -> None:
        env = {**_VALID_PRODUCTION_ENV, "AUTH_ENABLED": "false"}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("AUTH_ENABLED", str(ctx.exception))

    def test_production_rejects_debug(self) -> None:
        env = {**_VALID_PRODUCTION_ENV, "DEBUG": "true"}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("DEBUG", str(ctx.exception))

    def test_production_rejects_openapi_enabled(self) -> None:
        env = {**_VALID_PRODUCTION_ENV, "OPENAPI_ENABLED": "true"}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("OPENAPI_ENABLED", str(ctx.exception))

    def test_production_rejects_ml_preview_enabled(self) -> None:
        env = {**_VALID_PRODUCTION_ENV, "EKSTRABET_ML_PREVIEW": "true"}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("EKSTRABET_ML_PREVIEW", str(ctx.exception))

    def test_default_access_token_expire_minutes_is_1440(self) -> None:
        with patch.dict(os.environ, self.required_env, clear=False):
            get_settings.cache_clear()
            current = get_settings()
            self.assertEqual(current.access_token_expire_minutes, 1440)

    def test_production_rejects_short_secret_key(self) -> None:
        env = {**_VALID_PRODUCTION_ENV, "SECRET_KEY": "too-short"}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("SECRET_KEY", str(ctx.exception))

    def test_production_rejects_example_secret_key(self) -> None:
        env = {
            **_VALID_PRODUCTION_ENV,
            "SECRET_KEY": "generate_a_strong_random_key_at_least_32_chars"
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("SECRET_KEY", str(ctx.exception))

    def test_production_rejects_example_db_password(self) -> None:
        env = {
            **_VALID_PRODUCTION_ENV,
            "DB_PASSWORD": "your_database_password"
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("DB_PASSWORD", str(ctx.exception))

    def test_production_accepts_password_containing_word_password(self) -> None:
        env = {
            **_VALID_PRODUCTION_ENV,
            "DB_PASSWORD": "MySecurePassword2024!"
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            current = get_settings()
            self.assertEqual(
                current.db_password.get_secret_value(),
                "MySecurePassword2024!")

    def test_production_accepts_secret_containing_word_example(self) -> None:
        secret = "x7kQ2mNp9vLr4sWt8yHb3cDf6gHj1exampleZ"
        env = {**_VALID_PRODUCTION_ENV, "SECRET_KEY": secret}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            current = get_settings()
            self.assertEqual(current.secret_key.get_secret_value(), secret)

    def test_production_rejects_public_db_host(self) -> None:
        env = {**_VALID_PRODUCTION_ENV, "DB_HOST": "8.8.8.8"}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("DB_HOST", str(ctx.exception))

    def test_production_rejects_wildcard_trusted_hosts(self) -> None:
        env = {**_VALID_PRODUCTION_ENV, "TRUSTED_HOSTS": "*"}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            with self.assertRaises(ValidationError) as ctx:
                get_settings()
            self.assertIn("TRUSTED_HOSTS", str(ctx.exception))

    def test_non_production_allows_dev_defaults(self) -> None:
        env = {
            **self.required_env,
            "ENVIRONMENT": "development",
            "AUTH_ENABLED": "false",
            "CORS_ORIGINS": "*",
            "DEBUG": "true",
            "OPENAPI_ENABLED": "true",
            "DB_USER": "root"
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            current = get_settings()
            self.assertFalse(current.auth_enabled)
            self.assertEqual(current.cors_origins, ["*"])
            self.assertTrue(current.debug)
            self.assertTrue(current.openapi_enabled)
            self.assertEqual(current.db_user, "root")


if __name__ == "__main__":
    unittest.main()
