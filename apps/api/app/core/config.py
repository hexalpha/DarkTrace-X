from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All secrets remain in environment variables or a secret manager, never in source."""

    # Supports service-local overrides and the repository-root file during local development.
    # In containers, runtime environment variables take precedence over either file.
    model_config = SettingsConfigDict(env_file=(".env.local", "../../.env.local"), extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"
    jwt_secret: SecretStr = Field(default=SecretStr("change-me-before-production"))
    access_token_expire_minutes: int = 30
    database_url: str = "postgresql+asyncpg://darktrace:darktrace@localhost:5432/darktracex"
    redis_url: str = "redis://localhost:6379/0"
    elasticsearch_url: str = "http://localhost:9200"

    ai_default_provider: str = "openai"
    ai_fallback_order: str = "openai,groq,openrouter,ollama"
    openai_model: str = "gpt-5.6"
    openai_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None
    ollama_base_url: str = "http://localhost:11434"
    lm_studio_base_url: str = "http://localhost:1234/v1"
    vllm_base_url: str = "http://localhost:8000/v1"
    llama_cpp_base_url: str = "http://localhost:8080/v1"
    custom_llm_base_url: str | None = None
    custom_llm_api_key: SecretStr | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def fallback_providers(self) -> list[str]:
        return [provider.strip().lower() for provider in self.ai_fallback_order.split(",") if provider.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
