import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.search.service import SearchService


class SecurityConfigurationTests(unittest.TestCase):
    def test_staging_requires_explicit_strong_jwt_secret(self):
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, app_env="staging")
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, app_env="production", jwt_secret="short")

    def test_development_secret_is_ephemeral_and_not_known(self):
        settings = Settings(_env_file=None, app_env="development")
        self.assertIsNotNone(settings.jwt_secret)
        self.assertGreaterEqual(len(settings.jwt_secret.get_secret_value()), 32)
        self.assertNotEqual(settings.jwt_secret.get_secret_value(), "change-me-before-production")

    def test_compose_requires_postgres_and_elasticsearch_credentials(self):
        compose = Path(__file__).parents[3] / "docker-compose.yml"
        content = compose.read_text(encoding="utf-8")
        self.assertIn("POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD", content)
        self.assertNotIn("POSTGRES_PASSWORD: darktrace", content)
        self.assertIn("ELASTIC_PASSWORD:?Set ELASTIC_PASSWORD", content)
        self.assertIn('xpack.security.enabled: "true"', content)
        self.assertNotIn('xpack.security.enabled: "false"', content)

    @patch("app.search.service.AsyncElasticsearch")
    def test_elasticsearch_client_uses_configured_basic_auth(self, client):
        settings = Settings(
            _env_file=None,
            jwt_secret="test-only-secret-that-is-at-least-32-bytes",
            elasticsearch_username="elastic",
            elasticsearch_password=SecretStr("test-elasticsearch-password"),
        )
        SearchService(settings)
        self.assertEqual(client.call_args.kwargs["basic_auth"], ("elastic", "test-elasticsearch-password"))


if __name__ == "__main__":
    unittest.main()