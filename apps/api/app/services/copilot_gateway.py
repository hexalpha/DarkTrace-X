"""Two-provider AI gateway: local Qwen by default, optional external OpenAI-compatible."""
import asyncio
import json
import time
from typing import Literal
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import get_settings
from app.services import copilot_store as store

Provider = Literal["local", "external", "local_gguf", "openai", "custom"]
LEGACY_LOCAL = {"local_gguf", "ollama", "lm_studio", "vllm", "llama_cpp"}
LEGACY_EXTERNAL = {"openai", "gemini", "anthropic", "groq", "openrouter", "custom"}


def canonical_provider(provider: str) -> str:
    if provider in LEGACY_LOCAL:
        return "local"
    if provider in LEGACY_EXTERNAL:
        return "external"
    return provider


def configured_endpoint(provider: str) -> str:
    settings = get_settings()
    return settings.local_llm_service_url if canonical_provider(provider) == "local" else settings.external_ai_base_url or ""


def endpoint_identity(value: str):
    parsed = urlsplit(value)
    return parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), parsed.path.rstrip("/")


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Provider = "local"
    model: str = Field("selected", min_length=1, max_length=160, pattern=r"^[a-zA-Z0-9._:/@+-]+$")
    endpoint: str = Field("", max_length=300)
    enabled: bool = True
    temperature: float = Field(0.2, ge=0, le=2)
    context_window: int = Field(4096, ge=512, le=32768)
    max_tokens: int = Field(512, ge=16, le=4096)
    timeout: int = Field(180, ge=5, le=300)
    secret_env: Literal["", "EXTERNAL_AI_API_KEY"] = ""
    api_key: str | None = Field(None, max_length=512, exclude=True)

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, value):
        return canonical_provider(str(value))

    @model_validator(mode="after")
    def validate_endpoint(self):
        if self.provider == "local":
            if self.secret_env or (self.endpoint and urlsplit(self.endpoint).hostname not in {"localhost", "127.0.0.1", "host.docker.internal", "local-llm"}):
                raise ValueError("Local Qwen cannot use external credentials or endpoints")
        elif self.secret_env not in {"", "EXTERNAL_AI_API_KEY"}:
            raise ValueError("External AI must use EXTERNAL_AI_API_KEY")
        if self.endpoint:
            parsed = urlsplit(self.endpoint)
            allowed = {item.strip().lower() for item in get_settings().ai_endpoint_allowlist.split(",")}
            if parsed.scheme not in {"http", "https"} or parsed.hostname not in allowed or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("External endpoint must be explicitly allowlisted without credentials or query parameters")
            if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "host.docker.internal", "local-llm"}:
                raise ValueError("Remote external endpoints require HTTPS")
            if self.provider == "external" and endpoint_identity(self.endpoint) != endpoint_identity(get_settings().external_ai_base_url or ""):
                raise ValueError("External endpoint must match the deployment-configured endpoint")
        if self.max_tokens >= self.context_window:
            raise ValueError("Maximum output must be smaller than the context window")
        return self


async def configurations(p):
    settings = get_settings()
    primary = await store.get(p, "provider", "primary", owner="tenant") or {}
    local = ModelConfig(provider="local", model="selected").model_dump()
    external = ModelConfig(provider="external", model=settings.external_ai_model or "external-model", endpoint=settings.external_ai_base_url or "", enabled=settings.external_ai_enabled, secret_env="EXTERNAL_AI_API_KEY" if settings.external_ai_api_key else "").model_dump()
    if primary:
        normalized = ModelConfig(**{k: v for k, v in primary.items() if k != "encrypted_key"}).model_dump()
        normalized["has_key"] = bool(primary.get("encrypted_key"))
        if normalized["provider"] == "external":
            external.update(normalized)
        else:
            local.update(normalized)
    local["has_key"] = False
    external["has_key"] = bool(external.get("has_key") or settings.external_ai_api_key)
    return {"primary": local, "fallback": local, "offline": local, "external": external}


def environment_key(record):
    if canonical_provider(record.get("provider", "")) != "external":
        return None
    secret = get_settings().external_ai_api_key
    return secret.get_secret_value() if secret else None


async def save_config(p, slot, config):
    if slot not in {"primary", "external", "offline"}:
        raise ValueError("Only local primary or external configuration is supported")
    if slot == "external":
        slot = "primary"
    data = config.model_dump()
    if config.api_key is not None:
        data["encrypted_key"] = store.cipher().encrypt(config.api_key.encode()).decode() if config.api_key else None
    else:
        old = await store.get(p, "provider", slot, owner="tenant") or {}
        data["encrypted_key"] = old.get("encrypted_key")
    await store.put(p, "provider", slot, data, owner="tenant")
    await store.audit(p, "provider.changed", {"slot": slot, "provider": canonical_provider(config.provider)})


async def local_health():
    settings = get_settings()
    if not settings.local_llm_enabled:
        return {"state": "OFFLINE", "model": "Qwen3 4B Cybersecurity Heretic 16bit", "detail": "Local Qwen disabled"}
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(settings.local_llm_service_url + "/health", headers=worker_headers())
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError):
        return {"state": "OFFLINE", "model": "Qwen3 4B Cybersecurity Heretic 16bit", "detail": "Local Qwen inference worker unavailable"}


def worker_headers():
    key = get_settings().copilot_worker_key
    return {"X-Worker-Key": key.get_secret_value() if key else ""}


def endpoint(config):
    value = config.endpoint or configured_endpoint(config.provider)
    if not value:
        raise ValueError("External AI endpoint is not configured")
    if canonical_provider(config.provider) == "local" and urlsplit(value).hostname not in {"localhost", "127.0.0.1", "host.docker.internal", "local-llm"}:
        raise ValueError("Local Qwen endpoint must resolve to the local inference worker")
    return value.rstrip("/")


async def provider_stream(config, messages, key=None):
    config = ModelConfig.model_validate(config.model_dump())
    provider = canonical_provider(config.provider)
    base = endpoint(config)
    budget = max(1024, (config.context_window - config.max_tokens) * 3)
    while len(messages) > 2 and sum(len(m["content"]) for m in messages) > budget:
        messages = [messages[0], *messages[2:]]
    if sum(len(m["content"]) for m in messages) > budget:
        raise ValueError("Context exceeds configured window; ask a narrower question")
    headers = worker_headers() if provider == "local" else ({"Authorization": "Bearer " + key} if key else {})
    path = "/generate" if provider == "local" else "/chat/completions"
    body = {"messages": messages, "temperature": config.temperature, "max_tokens": config.max_tokens} if provider == "local" else {"model": config.model, "messages": messages, "temperature": config.temperature, "max_tokens": config.max_tokens, "stream": True}
    async with httpx.AsyncClient(timeout=config.timeout, follow_redirects=False) as client:
        async with client.stream("POST", base + path, headers=headers, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or line.startswith(("event:", ":")):
                    continue
                if line.startswith("data:"):
                    line = line[5:].strip()
                if line == "[DONE]":
                    break
                data = json.loads(line)
                if provider == "local":
                    if data.get("type") == "error":
                        raise ValueError(data.get("message", "Local inference failed"))
                    yield data
                else:
                    if data.get("error"):
                        raise ValueError("External provider returned an error")
                    for choice in data.get("choices", []):
                        delta = choice.get("delta", {}).get("content")
                        if delta:
                            yield {"type": "delta", "text": delta}
                        if choice.get("finish_reason"):
                            yield {"type": "usage", "finish_reason": choice["finish_reason"], "tokens": data.get("usage", {}).get("total_tokens")}


async def stream(p, messages, allow_cloud=False, slot="primary"):
    configs = await configurations(p)
    config_data = configs["external"] if slot == "external" else configs["offline"] if slot == "offline" else configs["primary"]
    config = ModelConfig(**{k: v for k, v in config_data.items() if k != "has_key"})
    provider = canonical_provider(config.provider)
    if provider == "external":
        settings = get_settings()
        if not settings.external_ai_enabled or not config.enabled:
            raise RuntimeError("External AI is disabled. Enable it explicitly in AI settings before use.")
    config = config.model_copy(update={"provider": provider, "model": "selected" if provider == "local" else config.model})
    record = await store.get(p, "provider", "primary", owner="tenant") or config.model_dump()
    key = store.cipher().decrypt(record["encrypted_key"].encode()).decode() if record.get("encrypted_key") else environment_key(record)
    started = time.monotonic()
    yield {"type": "provider", "provider": provider, "model": config.model, "fallback": False}
    emitted = False
    try:
        async with asyncio.timeout(config.timeout):
            async for event in provider_stream(config, messages, key):
                if event.get("type") == "delta":
                    emitted = True
                yield event
        if not emitted:
            raise ValueError("Empty provider completion")
        yield {"type": "provider_done", "latency_ms": round((time.monotonic() - started) * 1000), "provider": provider, "model": config.model}
    except Exception as exc:
        await store.audit(p, "provider.failed", {"provider": provider, "reason": type(exc).__name__})
        raise RuntimeError("Local AI is unavailable" if provider == "local" else "External AI request failed safely") from None
