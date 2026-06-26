"""Tests for backend.config."""

from __future__ import annotations
import os
import unittest
from unittest.mock import patch
from backend.config import Settings, get_database_config, get_settings


class TestSettings(unittest.TestCase):
    """Unit tests for application settings."""
    required_env = {
        "DB_PASSWORD": "test-db-password",
        "SECRET_KEY": "test-secret-key-for-unit-tests-only",
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
        )
        self.assertEqual(current.frontend_origin, "http://localhost:3000")


if __name__ == "__main__":
    unittest.main()
