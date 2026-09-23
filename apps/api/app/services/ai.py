"""Application AI facade with local Qwen default and one opt-in external provider."""
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import Settings
from app.domain.schemas import AIChatRequest, AIChatResponse
from app.services.copilot_gateway import ModelConfig, environment_key, provider_stream


class AIProviderUnavailable(RuntimeError):
    def __init__(self, attempted: list[str], reasons: dict[str, str] | None = None):
        super().__init__("No selected AI provider could complete this request")
        self.attempted = attempted
        self.reasons = reasons or {}


class AIRouter:
    SYSTEM_PROMPT = """You are DarkTrace X, a defensive AI SOC assistant. Help authorized security teams
understand provided telemetry, IOCs, CVEs, and incident evidence. Be concise, label uncertainty,
never invent source evidence, and recommend safe defensive verification or containment steps. Do not
provide instructions for intrusion, credential misuse, malware deployment, evasion, or accessing illicit sources."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def enabled_providers(self):
        return [
            {"id": "local", "configured": bool(self.settings.local_llm_enabled), "default_model": "Qwen3 4B Cybersecurity Heretic 16bit"},
            {"id": "external", "configured": bool(self.settings.external_ai_enabled and self.settings.external_ai_api_key), "default_model": self.settings.external_ai_model or "external-model"},
        ]

    async def scan_local_models(self):
        return []

    async def complete(self, request: AIChatRequest, persisted_history=None) -> AIChatResponse:
        provider = "external" if request.provider == "external" else "local"
        if provider == "external" and not self.settings.external_ai_enabled:
            raise AIProviderUnavailable(["external"], {"external": "disabled"})
        config = ModelConfig(
            provider=provider,
            model=(request.model or self.settings.external_ai_model or "external-model") if provider == "external" else "selected",
            endpoint=self.settings.external_ai_base_url or "" if provider == "external" else "",
            secret_env="EXTERNAL_AI_API_KEY" if provider == "external" and self.settings.external_ai_api_key else "",
        )
        record = config.model_dump()
        key = environment_key(record)
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}, *(persisted_history or []), {"role": "user", "content": request.message}]
        chunks = []
        try:
            async with asyncio.timeout(125 if provider == "local" else 45):
                async for event in provider_stream(config, messages, key):
                    if event.get("type") == "delta":
                        chunks.append(event["text"])
        except Exception as exc:
            raise AIProviderUnavailable([provider], {provider: type(exc).__name__}) from exc
        response = "".join(chunks).strip()
        if not response:
            raise AIProviderUnavailable([provider], {provider: "empty_response"})
        return AIChatResponse(conversation_id=request.conversation_id or uuid4(), message=response, provider=provider, model=config.model, used_fallback=False, source_refs=request.source_refs, generated_at=datetime.now(UTC))
