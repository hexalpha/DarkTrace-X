import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from app.services.safe_http import public_request, public_addresses
from app.services.copilot_gateway import ModelConfig
from app.services import login_guard


class Stream(httpx.AsyncByteStream):
    def __init__(self, chunks, delay=0):
        self.chunks, self.delay = chunks, delay
    async def __aiter__(self):
        for chunk in self.chunks:
            await asyncio.sleep(self.delay)
            yield chunk


class SecurityRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_readiness_rechecks_storage_and_recovers(self):
        from app.api.v1 import routes
        database = SimpleNamespace(ready=False)
        async def connect():
            database.ready = available[0]
        database.connect = connect
        available = [False]
        search = SimpleNamespace(client=SimpleNamespace(ping=AsyncMock(return_value=True)))
        with patch.object(routes.database_module, 'database', database), patch.object(routes.search_module, 'search_service', search):
            with self.assertRaises(HTTPException) as error:
                await routes.readiness()
            self.assertEqual(error.exception.status_code, 503)
            available[0] = True
            self.assertEqual(await routes.readiness(), {'status': 'ready'})
            search.client.ping.side_effect = ConnectionError()
            with self.assertRaises(HTTPException) as error:
                await routes.readiness()
            self.assertEqual(error.exception.status_code, 503)

    def test_credentials_bound_to_provider_and_exact_endpoint(self):
        for values in [dict(provider='custom', secret_env='OPENAI_API_KEY'),
                       dict(provider='openai', endpoint='http://localhost:8888/v1'),
                       dict(provider='local_gguf', endpoint='http://localhost:9876'),
                       dict(provider='openai', endpoint='https://api.openai.com:444/v1'),
                       dict(provider='openai', endpoint='https://api.openai.com/other')]:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                ModelConfig(**values)
        ModelConfig(provider='openai', endpoint='https://api.openai.com:443/v1')

    async def test_blocked_destinations(self):
        for ip in ['127.0.0.1', '0.1.2.3', '10.1.2.3', '172.16.1.1', '192.168.1.1', '169.254.169.254', '::1', 'fc00::1', 'fe80::1']:
            with patch('app.services.safe_http.socket.getaddrinfo', return_value=[(0,0,0,'',(ip,80))]):
                with self.assertRaises(ValueError):
                    await public_addresses('attacker.example',80)
        with self.assertRaises(ValueError):
            await public_addresses('localhost',80)

    async def test_rebinding_pins_address_and_preserves_tls_identity(self):
        real = httpx.AsyncClient
        def respond(request):
            self.assertEqual(request.url.host, '8.8.8.8')
            self.assertEqual(request.headers['host'], 'source.example')
            self.assertEqual(request.extensions['sni_hostname'], 'source.example')
            return httpx.Response(200, content=b'ok')
        with patch('app.services.safe_http.public_addresses', AsyncMock(side_effect=[['8.8.8.8'], ['127.0.0.1']])) as dns, patch('app.services.safe_http.httpx.AsyncClient', side_effect=lambda **kw: real(transport=httpx.MockTransport(respond), **kw)):
            result = await public_request('GET','https://source.example',max_bytes=10)
            self.assertEqual(result.content,b'ok')
            self.assertEqual(dns.await_count,1)

    async def test_redirect_private_address_rejected(self):
        real=httpx.AsyncClient
        with patch('app.services.safe_http.public_addresses', AsyncMock(side_effect=[['8.8.8.8'], ValueError('private')])) as dns, patch('app.services.safe_http.httpx.AsyncClient', side_effect=lambda **kw: real(transport=httpx.MockTransport(lambda r: httpx.Response(302,headers={'location':'http://127.0.0.1/private'})), **kw)):
            with self.assertRaises(ValueError):
                await public_request('GET','http://source.example',max_bytes=10,redirects=3)
            self.assertEqual(dns.await_count,2)

    async def test_size_and_total_time_limits(self):
        real=httpx.AsyncClient
        for chunks,delay,expected in [([b'abcdef',b'abcdef'],0,ValueError),([b'a']*100,0.02,TimeoutError)]:
            with patch('app.services.safe_http.public_addresses',AsyncMock(return_value=['8.8.8.8'])), patch('app.services.safe_http.httpx.AsyncClient',side_effect=lambda **kw:real(transport=httpx.MockTransport(lambda r:httpx.Response(200,stream=Stream(chunks,delay))),**kw)):
                with self.assertRaises(expected):
                    await public_request('GET','https://source.example',max_bytes=10,timeout=0.05)

    async def test_graphql_aliases_rejected_before_database_work(self):
        from app import graphql
        overview=AsyncMock(return_value=SimpleNamespace(protected_assets=0,active_alerts=0,risk_score=0,event_rate=0))
        with patch.object(graphql,'operations',return_value=SimpleNamespace(overview=overview)):
            bad=await graphql.schema.execute('{ '+' '.join(f'a{i}: dashboard {{ riskScore }}' for i in range(25))+' }',context_value={'principal':object()})
            self.assertTrue(bad.errors)
            overview.assert_not_awaited()
            good=await graphql.schema.execute('{ dashboard { riskScore } }',context_value={'principal':object()})
            self.assertFalse(good.errors)

    async def test_unknown_paths_share_one_metric_label(self):
        from app.main import app
        from app.observability import LATENCY
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            for i in range(10):
                self.assertEqual((await client.get(f'/api/v1/missing-regression-{i}')).status_code,404)
        paths={s.labels.get('path') for m in LATENCY.collect() for s in m.samples}
        self.assertIn('UNMATCHED',paths)
        self.assertFalse(any('missing-regression' in (p or '') for p in paths))

    async def test_login_lockout_backoff_and_success_reset(self):
        cache=AsyncMock()
        cache.__aenter__.return_value=cache
        payload=SimpleNamespace(tenant_id='tenant',email='USER@example.com')
        with patch('app.services.login_guard.Redis.from_url',return_value=cache),patch('app.services.login_guard.asyncio.sleep',new_callable=AsyncMock) as sleep:
            cache.eval.return_value=2
            await login_guard.reserve(payload)
            sleep.assert_awaited_once()
            cache.eval.return_value=9
            with self.assertRaises(HTTPException) as exc:
                await login_guard.reserve(payload)
            self.assertEqual(exc.exception.status_code,429)
            await login_guard.finish(payload,True)
            cache.delete.assert_awaited_once_with(login_guard.account_key(payload))
            await login_guard.finish(payload,False)
            self.assertEqual(cache.delete.await_count,1)

    async def test_all_legacy_provider_choices_hit_limit_before_execution(self):
        from app.api.v1.routes import chat_with_soc_assistant
        from app.domain.schemas import AIChatRequest
        for provider in [None,'local_gguf','ollama','lm_studio','openai','gemini','custom','future']:
            with patch('app.services.copilot_store.limit',AsyncMock(side_effect=HTTPException(429,'quota'))) as limit:
                with self.assertRaises(HTTPException) as exc:
                    await chat_with_soc_assistant(AIChatRequest(message='test',provider=provider),object(),object())
                self.assertEqual(exc.exception.status_code,429)
                limit.assert_awaited_once()
