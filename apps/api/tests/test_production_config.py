import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from pydantic import ValidationError
from app.core.config import Settings
from app.search.service import SearchService


class ProductionConfigurationTests(unittest.TestCase):
    def config(self):
        return dict(_env_file=None, app_env='production',
            jwt_secret='test-only-jwt-secret-with-more-than-32-bytes',
            ai_secret_key=Fernet.generate_key().decode(),
            database_url='postgresql+asyncpg://test:unique-test-password@postgres/test',
            elasticsearch_url='https://elasticsearch:9200',
            elasticsearch_username='elastic', elasticsearch_password='unique-test-password',
            elasticsearch_ca_certs='/external/ca.crt', cors_origins='https://soc.example.org',
            local_llm_enabled=True, copilot_worker_key='test-only-worker-key-with-more-than-32-bytes')

    def test_missing_and_placeholder_secrets_fail_closed(self):
        with patch('pathlib.Path.is_file', return_value=True):
            for field, value in [('jwt_secret', None), ('ai_secret_key', None),
                    ('copilot_worker_key', None), ('elasticsearch_password', None),
                    ('database_url', 'postgresql+asyncpg://darktrace:darktrace@postgres/db'),
                    ('jwt_secret', 'replace-with-a-32-byte-minimum-random-secret'),
                    ('elasticsearch_url', 'http://elasticsearch:9200'),
                    ('cors_origins', '*')]:
                for environment in ('staging', 'production'):
                    with self.subTest(field=field, environment=environment), self.assertRaises(ValidationError):
                        Settings(**(self.config() | {field: value, 'app_env': environment}))

    def test_verified_tls_client_and_optional_external_integrations(self):
        with patch('pathlib.Path.is_file', return_value=True):
            settings = Settings(**(self.config() | dict(external_ai_enabled=False, external_ai_api_key=None,
                smtp_host=None, smtp_password=None, smtp_sender=None)))
        self.assertFalse(settings.external_ai_enabled)
        self.assertEqual(settings.ai_default_provider, 'local')
        with patch('app.search.service.AsyncElasticsearch') as client:
            SearchService(settings)
            self.assertTrue(client.call_args.kwargs['verify_certs'])
            self.assertEqual(client.call_args.kwargs['ca_certs'], '/external/ca.crt')

    def test_missing_ca_fails_closed(self):
        with patch('pathlib.Path.is_file', return_value=False), self.assertRaises(ValidationError):
            Settings(**self.config())

    def test_deployment_credentials_redacted_from_logs(self):
        import logging
        from app.core.logging import SafeJSONFormatter
        settings = Settings(_env_file=None, smtp_password='test-smtp-credential',
            elasticsearch_password='test-search-credential')
        record = logging.LogRecord('app', logging.ERROR, '', 0,
            'connection test-smtp-credential test-search-credential postgresql://user:test-database-credential@db/name', (), None)
        with patch('app.services.copilot_store.get_settings', return_value=settings):
            output = SafeJSONFormatter().format(record)
        for secret in ('test-smtp-credential', 'test-search-credential', 'test-database-credential'):
            self.assertNotIn(secret, output)
