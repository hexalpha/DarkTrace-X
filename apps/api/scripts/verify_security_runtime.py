"""Disposable tenant checks against the running API; never print credentials."""
import asyncio
import os
import secrets
from uuid import uuid4
import httpx
from sqlalchemy import delete
from app.core.config import get_settings
from app.storage.database import Database
from app.storage.models import Base, TenantRecord, BrowserSessionRecord


async def main():
    tenant = 'security-check-' + uuid4().hex[:12]
    password = secrets.token_urlsafe(24)
    db = Database(get_settings()); await db.connect()
    async with httpx.AsyncClient(base_url='http://nginx:8080/api/v1',timeout=60) as client:
        try:
            payload={'tenant_id':tenant,'email':'security@example.com','password':password,'display_name':'Disposable security verification'}
            r=await client.post('/auth/register',json=payload,headers={'X-Browser-Session':'1'})
            assert r.status_code==201, r.status_code
            cookie_headers=r.headers.get_list('set-cookie')
            assert any(c.startswith('dtx_access=') and 'HttpOnly' in c for c in cookie_headers)
            assert any(c.startswith('dtx_refresh=') and 'HttpOnly' in c for c in cookie_headers)
            assert (await client.get('/auth/me')).status_code==200
            print('PASS HttpOnly browser login and authenticated cookie session',flush=True)
            old_refresh=client.cookies.get('dtx_refresh'); old_csrf=client.cookies.get('dtx_csrf')
            assert (await client.post('/auth/refresh')).status_code==403
            assert (await client.post('/auth/refresh',headers={'X-CSRF-Token':old_csrf})).status_code==204
            assert client.cookies.get('dtx_refresh')!=old_refresh
            assert (await client.get('/auth/me')).status_code==200
            async with httpx.AsyncClient(base_url='http://nginx:8080/api/v1') as replay:
                replay.cookies.set('dtx_refresh',old_refresh);replay.cookies.set('dtx_csrf',old_csrf)
                assert (await replay.post('/auth/refresh',headers={'X-CSRF-Token':old_csrf})).status_code==401
            assert (await client.get('/auth/me')).status_code==401
            print('PASS CSRF rejection, refresh rotation, replay revokes access-token family',flush=True)
            client.cookies.clear()
            login={k:v for k,v in payload.items() if k!='display_name'}
            r=await client.post('/auth/login',json=login)
            assert r.status_code==200
            bearer={'Authorization':'Bearer '+r.json()['access_token']}
            assert (await client.get('/auth/me',headers=bearer)).status_code==200
            assert (await client.put('/copilot/models/primary',headers=bearer,json={'provider':'custom','secret_env':'OPENAI_API_KEY','endpoint':'http://host.docker.internal:9999'})).status_code==422
            gql=await client.post('http://nginx:8080/graphql',headers=bearer,json={'query':'{ '+' '.join(f'a{i}: dashboard {{ riskScore }}' for i in range(25))+' }'})
            assert gql.json().get('errors')
            print('PASS bearer compatibility, unsafe credential binding rejection, GraphQL alias rejection',flush=True)
            bad={**login,'password':'wrong-password'}
            statuses=[(await client.post('/auth/login',json=bad)).status_code for _ in range(9)]
            assert statuses[:8]==[401]*8 and statuses[8]==429,statuses
            print('PASS Redis-backed account lockout after eight failed attempts',flush=True)
        finally:
            async with db.sessions() as session:
                await session.execute(delete(BrowserSessionRecord).where(BrowserSessionRecord.tenant_id==tenant))
                for table in reversed(Base.metadata.sorted_tables):
                    if 'tenant_id' in table.c:
                        await session.execute(delete(table).where(table.c.tenant_id==tenant))
                await session.execute(delete(TenantRecord).where(TenantRecord.id==tenant));await session.commit()
    await db.close()
asyncio.run(main())
