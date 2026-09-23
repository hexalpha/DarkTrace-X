"""Focused live checks; inserts and deletes only a uniquely named verification index."""
import asyncio
import json
import ssl
from uuid import uuid4
import httpx
from elasticsearch import AsyncElasticsearch
from app.core.config import get_settings
from app.search.service import SearchService
from app.services.copilot_gateway import local_health, provider_stream, ModelConfig


async def main():
    settings = get_settings()
    assert settings.elasticsearch_url.startswith('https://'), 'TLS is not active'
    service = SearchService(settings)
    index = 'dtx-tls-verification-' + uuid4().hex
    created = False
    try:
        await service.connect()
        assert service.ready, 'Authenticated HTTPS health failed'
        client = service.client
        await client.indices.create(index=index, settings={'number_of_replicas': 0})
        created = True
        await client.index(index=index, id='verification', document={'purpose': 'tls-verification'}, refresh='wait_for')
        result = await client.search(index=index, query={'term': {'purpose.keyword': 'tls-verification'}})
        assert result['hits']['total']['value'] == 1
        health = await client.cluster.health()
        assert health['status'] in {'green', 'yellow'}
        async with httpx.AsyncClient(verify=ssl.create_default_context(cafile=settings.elasticsearch_ca_certs)) as anonymous:
            assert (await anonymous.get(settings.elasticsearch_url)).status_code == 401
        # The local verification CA is deliberately absent from system trust.
        async with httpx.AsyncClient() as untrusted:
            try:
                await untrusted.get(settings.elasticsearch_url)
            except httpx.ConnectError:
                pass
            else:
                raise AssertionError('Untrusted certificate was accepted')
        print('VERIFIED Elasticsearch authenticated HTTPS, certificate rejection, unauthenticated rejection, indexing, search, health', flush=True)
        model = await local_health()
        for attempt in range(36):
            if model['state'] in {'ONLINE', 'ERROR'}:
                break
            if attempt % 6 == 0:
                print('Waiting for restarted local model:', model['state'], flush=True)
            await asyncio.sleep(5)
            model = await local_health()
        assert model['state'] == 'ONLINE', 'Local model not online'
        text = ''
        async for part in provider_stream(ModelConfig(provider='local', max_tokens=64), [{'role':'user','content':'Reply with one short sentence explaining what a firewall does.'}]):
            if part.get('type') == 'delta':
                text += part.get('text', '')
        assert text.strip(), 'Local inference returned no text'
        print('VERIFIED local Qwen inference; output characters:', len(text), flush=True)
        print(json.dumps({'smtp': 'configured' if settings.smtp_host and settings.smtp_sender else 'smtp_unavailable',
            'external_ai': 'enabled' if settings.external_ai_enabled and settings.external_ai_api_key else 'BLOCKED BY EXTERNAL CONFIGURATION'}), flush=True)
    finally:
        if created:
            await service.client.indices.delete(index=index)
        await service.close()


asyncio.run(main())
