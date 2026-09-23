import unittest
from unittest.mock import patch

from app.core.config import Settings
from app.domain.schemas import AIChatRequest
from app.services.ai import AIRouter, AIProviderUnavailable


class ProviderResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_is_default_and_no_fallback(self):
        router = AIRouter(Settings(_env_file=None, local_llm_enabled=False))
        with self.assertRaises(AIProviderUnavailable) as result:
            await router.complete(AIChatRequest(message="private evidence"), [])
        self.assertEqual(result.exception.attempted, ["local"])

    async def test_external_requires_explicit_enablement(self):
        router = AIRouter(Settings(_env_file=None, external_ai_enabled=False))
        with self.assertRaises(AIProviderUnavailable) as result:
            await router.complete(AIChatRequest(provider="external", message="test"), [])
        self.assertEqual(result.exception.reasons, {"external": "disabled"})

    async def test_local_completion_persists_provider_identity(self):
        router = AIRouter(Settings(_env_file=None, local_llm_enabled=True))
        async def fake(*args, **kwargs):
            yield {"type": "delta", "text": "verified"}
        with patch("app.services.ai.provider_stream", fake):
            result = await router.complete(AIChatRequest(message="private evidence"), [])
        self.assertEqual((result.provider, result.model, result.message), ("local", "selected", "verified"))
