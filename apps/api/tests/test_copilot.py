import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from pydantic import ValidationError

from app.core.config import Settings
from app.services.copilot_gateway import ModelConfig, stream
from app.services.copilot_store import redact
from app.services.copilot_tools import Knowledge, ToolCall


class CopilotSecurityTests(unittest.TestCase):
    def test_unknown_tools_and_cross_tenant_arguments_rejected(self):
        for data in ({'tool':'shell','query':'whoami'}, {'tool':'alerts','tenant_id':'other'}, {'tool':'alerts','limit':999}):
            with self.assertRaises(ValidationError):
                ToolCall(**data)

    def test_secret_redaction(self):
        data={'password':'private','text':'api_key=abcdef secret=xyz Bearer token123 sk-project-0123456789'}
        result=redact(data)
        self.assertEqual(result['password'],'[REDACTED]')
        for secret in ('abcdef','xyz','token123','sk-project-0123456789'):
            self.assertNotIn(secret,result['text'])

    def test_endpoint_allowlist(self):
        for endpoint in ('http://169.254.169.254/latest','file:///etc/passwd','http://localhost:1/?key=secret','https://user:pass@api.openai.com'):
            with self.assertRaises(ValidationError):
                ModelConfig(endpoint=endpoint)
        with self.assertRaises(ValidationError):
            ModelConfig(provider='local', endpoint='https://api.openai.com/v1')
        with self.assertRaises(ValidationError):
            ModelConfig(context_window=512, max_tokens=512)

    def test_latest_monitoring_is_not_unrelated_public_feed(self):
        from app.services.copilot_tools import initial_tools
        self.assertEqual(initial_tools('latest DarkTrace X monitoring results')[0].tool, 'mentions')

    def test_server_default_cannot_route_private_requests_to_cloud(self):
        from app.services.copilot_gateway import endpoint
        with patch('app.services.copilot_gateway.get_settings',return_value=Settings(_env_file=None,local_llm_service_url='https://api.openai.com/v1')):
            with self.assertRaises(ValueError):
                endpoint(ModelConfig(provider='local'))

    def test_knowledge_does_not_scan_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'README.md').write_text('DarkTrace architecture uses PostgreSQL',encoding='utf-8')
            (root/'.env').write_text('SECRET=DO_NOT_INDEX',encoding='utf-8')
            with patch('app.services.copilot_tools.get_settings',return_value=Settings(_env_file=None,project_knowledge_root=folder)):
                index=Knowledge();index.refresh()
                self.assertEqual(index.status()['sources'],['README.md'])
                self.assertTrue(index.search('PostgreSQL'))
                self.assertFalse(index.search('DO_NOT_INDEX'))


class RoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_cloud_requires_opt_in_and_fallback_is_bounded(self):
        cloud=ModelConfig(provider='external',model='test',enabled=False).model_dump()
        local=ModelConfig().model_dump()
        calls=[]
        async def fake(config,messages,key):
            calls.append(config.provider)
            yield {'type':'delta','text':'Observed facts'}
        with patch('app.services.copilot_gateway.configurations',AsyncMock(return_value={'primary':cloud,'fallback':local,'offline':local})), patch('app.services.copilot_gateway.store.get',AsyncMock(return_value=None)), patch('app.services.copilot_gateway.provider_stream',fake):
            with self.assertRaises(RuntimeError):
                _=[event async for event in stream(None,[{'role':'user','content':'private'}],False)]
