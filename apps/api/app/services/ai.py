import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
from openai import AsyncOpenAI

from app.core.config import Settings
from app.domain.schemas import AIChatRequest, AIChatResponse


class AIProviderUnavailable(RuntimeError):
    """Raised only after all permitted configured providers have failed."""

    def __init__(self, attempted: list[str]) -> None:
        super().__init__("No configured AI provider could complete this request")
        self.attempted = attempted


class ConversationMemory:
    """Short-lived reference implementation; persist encrypted records in ai_messages in production."""

    def __init__(self) -> None:
        self._messages: dict[UUID, list[dict[str, str]]] = defaultdict(list)

    def history(self, conversation_id: UUID) -> list[dict[str, str]]:
        return self._messages[conversation_id][-12:]

    def append(self, conversation_id: UUID, role: str, content: str) -> None:
        self._messages[conversation_id].append({"role": role, "content": content})


class AIRouter:
    SYSTEM_PROMPT = """You are DarkTrace X, a defensive AI SOC assistant. Help authorized security teams
understand provided telemetry, IOCs, CVEs, and incident evidence. Be concise, label uncertainty,
never invent source evidence, and recommend safe defensive verification or containment steps. Do not
provide instructions for intrusion, credential misuse, malware deployment, evasion, or accessing illicit sources."""

    DEFAULT_MODELS = {
        "openai": "gpt-5.6",
        "gemini": "gemini-2.0-flash",
        "anthropic": "claude-sonnet-4-20250514",
        "groq": "llama-3.3-70b-versatile",
        "openrouter": "openai/gpt-4.1-mini",
        "ollama": "llama3.2",
        "lm_studio": "local-model",
        "vllm": "local-model",
        "llama_cpp": "local-model",
        "custom": "custom-model",
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.memory = ConversationMemory()

    @staticmethod
    def _secret(value) -> str | None:
        return value.get_secret_value() if value else None

    def _model_for(self, provider: str, requested: str | None) -> str:
        if requested:
            return requested
        if provider == "openai":
            return self.settings.openai_model
        return self.DEFAULT_MODELS[provider]

    def enabled_providers(self) -> list[dict[str, object]]:
        checks = {
            "openai": self._secret(self.settings.openai_api_key),
            "gemini": self._secret(self.settings.gemini_api_key),
            "anthropic": self._secret(self.settings.anthropic_api_key),
            "groq": self._secret(self.settings.groq_api_key),
            "openrouter": self._secret(self.settings.openrouter_api_key),
            "ollama": self.settings.ollama_base_url,
            "lm_studio": self.settings.lm_studio_base_url,
            "vllm": self.settings.vllm_base_url,
            "llama_cpp": self.settings.llama_cpp_base_url,
            "custom": self.settings.custom_llm_base_url,
        }
        return [
            {"id": name, "configured": bool(value), "default_model": self._model_for(name, None)}
            for name, value in checks.items()
        ]

    async def complete(self, request: AIChatRequest) -> AIChatResponse:
        conversation_id = request.conversation_id or uuid4()
        selected = request.provider.lower() if request.provider else self.settings.ai_default_provider.lower()
        candidates = [selected] + [name for name in self.settings.fallback_providers if name != selected]
        attempted: list[str] = []
        history = self.memory.history(conversation_id)
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}, *history, {"role": "user", "content": request.message}]

        for provider in candidates:
            if provider not in self.DEFAULT_MODELS:
                continue
            attempted.append(provider)
            try:
                model = self._model_for(provider, request.model if provider == selected else None)
                response = await asyncio.wait_for(self._dispatch(provider, model, messages), timeout=45)
                self.memory.append(conversation_id, "user", request.message)
                self.memory.append(conversation_id, "assistant", response)
                return AIChatResponse(
                    conversation_id=conversation_id,
                    message=response,
                    provider=provider,
                    model=model,
                    used_fallback=provider != selected,
                    source_refs=request.source_refs,
                    generated_at=datetime.now(UTC),
                )
            except (httpx.HTTPError, TimeoutError, ValueError, KeyError):
                # Provider diagnostics belong in restricted structured logs, never in the analyst response.
                continue
        raise AIProviderUnavailable(attempted)

    async def _dispatch(self, provider: str, model: str, messages: list[dict[str, str]]) -> str:
        if provider == "openai":
            key = self._secret(self.settings.openai_api_key)
            if not key:
                raise ValueError("OpenAI is not configured")
            client = AsyncOpenAI(api_key=key)
            response = await client.responses.create(model=model, input=messages)
            if not response.output_text:
                raise ValueError("Empty OpenAI response")
            return response.output_text
        if provider == "gemini":
            return await self._gemini(model, messages)
        if provider == "anthropic":
            return await self._anthropic(model, messages)
        if provider == "ollama":
            return await self._ollama(model, messages)
        base_urls = {
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "lm_studio": self.settings.lm_studio_base_url,
            "vllm": self.settings.vllm_base_url,
            "llama_cpp": self.settings.llama_cpp_base_url,
            "custom": self.settings.custom_llm_base_url,
        }
        keys = {
            "groq": self._secret(self.settings.groq_api_key),
            "openrouter": self._secret(self.settings.openrouter_api_key),
            "lm_studio": None,
            "vllm": None,
            "llama_cpp": None,
            "custom": self._secret(self.settings.custom_llm_api_key),
        }
        return await self._openai_compatible(base_urls[provider], keys[provider], model, messages)

    async def _openai_compatible(self, base_url: str | None, key: str | None, model: str, messages: list[dict[str, str]]) -> str:
        if not base_url:
            raise ValueError("Provider endpoint is not configured")
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json={"model": model, "messages": messages, "temperature": 0.2},
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])

    async def _ollama(self, model: str, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            return str(response.json()["message"]["content"])

    async def _gemini(self, model: str, messages: list[dict[str, str]]) -> str:
        key = self._secret(self.settings.gemini_api_key)
        if not key:
            raise ValueError("Gemini is not configured")
        system = next((message["content"] for message in messages if message["role"] == "system"), self.SYSTEM_PROMPT)
        contents = [{"role": "model" if message["role"] == "assistant" else "user", "parts": [{"text": message["content"]}]} for message in messages if message["role"] != "system"]
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                json={"systemInstruction": {"parts": [{"text": system}]}, "contents": contents, "generationConfig": {"temperature": 0.2}},
            )
            response.raise_for_status()
            return str(response.json()["candidates"][0]["content"]["parts"][0]["text"])

    async def _anthropic(self, model: str, messages: list[dict[str, str]]) -> str:
        key = self._secret(self.settings.anthropic_api_key)
        if not key:
            raise ValueError("Anthropic is not configured")
        system = next((message["content"] for message in messages if message["role"] == "system"), self.SYSTEM_PROMPT)
        prompt_messages = [message for message in messages if message["role"] != "system"]
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={"model": model, "max_tokens": 1200, "system": system, "messages": prompt_messages, "temperature": 0.2},
            )
            response.raise_for_status()
            return str(response.json()["content"][0]["text"])

