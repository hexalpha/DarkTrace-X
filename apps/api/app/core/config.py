from functools import lru_cache
import secrets
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All secrets remain in environment variables or a secret manager, never in source."""

    # Supports service-local overrides and the repository-root file during local development.
    # In containers, runtime environment variables take precedence over either file.
    model_config = SettingsConfigDict(env_file=(".env.local", "../../.env.local"), extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"
    jwt_secret: SecretStr | None = None
    access_token_expire_minutes: int = 30
    database_url: str = "postgresql+asyncpg://darktrace:darktrace@localhost:5432/darktracex"
    redis_url: str = "redis://localhost:6379/0"
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_username: str | None = None
    elasticsearch_password: SecretStr | None = None
    elasticsearch_ca_certs: str | None = None

    ai_default_provider: str = "local"
    ai_fallback_order: str = ""
    external_ai_enabled: bool = False
    external_ai_provider_name: str = "OpenAI-compatible"
    external_ai_base_url: str | None = "https://api.openai.com/v1"
    external_ai_model: str = "gpt-4o-mini"
    external_ai_api_key: SecretStr | None = None
    local_ai_max_output_tokens: int = Field(default=128, ge=32, le=4096)
    local_llm_enabled: bool = False
    local_llm_service_url: str = "http://127.0.0.1:8091"
    copilot_worker_key: SecretStr | None = None
    ai_secret_key: SecretStr | None = None
    project_knowledge_root: str = "../.."
    ai_endpoint_allowlist: str = "api.openai.com,host.docker.internal,local-llm"
    approved_feed_url: str | None = None
    approved_feed_api_key: SecretStr | None = None
    crawler_scheduler_enabled: bool = True
    delivery_worker_enabled: bool = True
    smtp_host: str | None = None
    smtp_port: int = Field(465, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_sender: str | None = None
    source_max_response_bytes: int = Field(2097152, ge=1024, le=8388608)
    webhook_max_response_bytes: int = Field(65536, ge=1024, le=1048576)
    outbound_timeout_seconds: int = Field(20, ge=1, le=120)
    crawler_scheduler_interval_seconds: int = Field(default=30, ge=5, le=3600)

    @model_validator(mode="after")
    def secure_production(self):
        if self.jwt_secret is None:
            if self.app_env == "development":
                self.jwt_secret = SecretStr(secrets.token_urlsafe(32))
            else:
                raise ValueError("Staging and production require an explicit JWT_SECRET of at least 32 characters")
        elif len(self.jwt_secret.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        if self.app_env in {"staging", "production"}:
            from urllib.parse import urlsplit
            from pathlib import Path
            from cryptography.fernet import Fernet
            def required_secret(value, name):
                raw = value.get_secret_value() if isinstance(value, SecretStr) else value
                if not raw or raw.lower() in {'darktrace', 'password', 'changeme', 'elastic'} or raw.lower().startswith(('replace-', 'change-me')):
                    raise ValueError(f"{name} requires a non-placeholder deployment secret")
            required_secret(self.jwt_secret, 'JWT_SECRET')
            required_secret(self.ai_secret_key, 'AI_SECRET_KEY')
            try:
                Fernet(self.ai_secret_key.get_secret_value().encode())
            except Exception:
                raise ValueError('AI_SECRET_KEY must be a valid Fernet key') from None
            required_secret(urlsplit(self.database_url).password, 'DATABASE_URL password')
            if urlsplit(self.elasticsearch_url).scheme != 'https':
                raise ValueError('Staging and production require Elasticsearch HTTPS')
            if not self.elasticsearch_username:
                raise ValueError('ELASTICSEARCH_USERNAME is required')
            required_secret(self.elasticsearch_password, 'ELASTICSEARCH_PASSWORD')
            if not self.elasticsearch_ca_certs or not Path(self.elasticsearch_ca_certs).is_file():
                raise ValueError('ELASTICSEARCH_CA_CERTS must reference a readable CA certificate')
            if self.local_llm_enabled:
                required_secret(self.copilot_worker_key, 'COPILOT_WORKER_KEY')
                if len(self.copilot_worker_key.get_secret_value()) < 32:
                    raise ValueError('COPILOT_WORKER_KEY must contain at least 32 characters')
            if not self.cors_origin_list or any(urlsplit(origin).scheme != 'https' or urlsplit(origin).path not in {'', '/'} or '*' in origin for origin in self.cors_origin_list):
                raise ValueError('Staging and production require explicit HTTPS CORS origins')
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def fallback_providers(self) -> list[str]:
        return [provider.strip().lower() for provider in self.ai_fallback_order.split(",") if provider.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
