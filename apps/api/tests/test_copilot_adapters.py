import unittest
from unittest.mock import AsyncMock, patch

from app.services.copilot_gateway import ModelConfig, stream


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_stream_is_single_provider(self):
        local = ModelConfig(provider="local").model_dump()
        async def fake(*args):
            yield {"type": "delta", "text": "verified"}
        with patch("app.services.copilot_gateway.configurations", AsyncMock(return_value={"primary": local, "offline": local, "fallback": local})), patch("app.services.copilot_gateway.store.get", AsyncMock(return_value=None)), patch("app.services.copilot_gateway.provider_stream", fake):
            output = [event async for event in stream(None, [])]
        self.assertEqual("".join(event.get("text", "") for event in output), "verified")
        self.assertFalse(any(event.get("fallback") for event in output))

    async def test_external_is_never_used_when_disabled(self):
        external = ModelConfig(provider="external", enabled=False).model_dump()
        with patch("app.services.copilot_gateway.configurations", AsyncMock(return_value={"primary": external, "offline": external, "fallback": external})):
            with self.assertRaises(RuntimeError):
                _ = [event async for event in stream(None, [])]
