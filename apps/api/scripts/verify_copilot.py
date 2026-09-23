"""Container integration audit, real services, temporary tenants only; no secret values printed."""
import asyncio
import hashlib
import json
import secrets
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.storage.database import Database
from app.storage.models import Base, TenantRecord, CopilotRecord, RevokedTokenRecord


async def main():
    db=Database(get_settings());await db.connect()
    tenants=['copilot-qa-'+uuid4().hex[:12] for _ in range(2)]
    tokens=[];checks={}
    async with httpx.AsyncClient(base_url='http://nginx:8080/api/v1',timeout=310) as client:
        async def req(method,path,h=None,body=None,status=200):
            r=await client.request(method,path,headers=h,json=body)
            if r.status_code!=status:
                raise AssertionError(f'{method} {path}: HTTP {r.status_code}, expected {status}')
            return r.json() if r.content else None
        def passed(name):
            checks[name]='PASS';print('PASS '+name,flush=True)
        try:
            identities=[]
            password=secrets.token_urlsafe(24)
            for tenant in tenants:
                data=await req('POST','/auth/register',body={'tenant_id':tenant,'email':'copilot@example.com','password':password,'display_name':'Temporary Copilot QA'},status=201)
                tokens.append(data['access_token']);identities.append({'Authorization':'Bearer '+tokens[-1]})
            a,b=identities
            from websockets.asyncio.client import connect
            async with connect('ws://nginx:8080/ws/events', origin='http://localhost:8080') as socket:
                await socket.send(json.dumps({'token':tokens[0]}))
                pulse=json.loads(await asyncio.wait_for(socket.recv(),15))
                assert pulse['type']=='telemetry.pulse'
            graph=await client.post('http://nginx:8080/graphql',headers=a,json={'query':'{ dashboard { protectedAssets activeAlerts riskScore eventRate } }'})
            assert graph.status_code==200 and graph.json().get('data',{}).get('dashboard') is not None
            assert (await client.post('http://nginx:8080/graphql',json={'query':'{ dashboard { activeAlerts } }'})).status_code==401
            passed('Authenticated WebSocket and GraphQL through Nginx')
            await req('GET','/copilot/status',status=401)
            current=await req('GET','/copilot/status',a)
            assert all(v=='ONLINE' for v in current['services'].values())
            assert current['local_model']['state']=='ONLINE'
            assert current['knowledge']['chunks']>0
            passed('PostgreSQL Redis Elasticsearch and GGUF health')
            await req('POST','/copilot/tools',a,{'tool':'shell','query':'whoami'},422)
            await req('POST','/copilot/tools',a,{'tool':'alerts','tenant_id':tenants[1]},422)
            assert (await req('POST','/copilot/tools',a,{'tool':'project_knowledge','query':'architecture'}))['data']
            assert not (await req('POST','/copilot/tools',b,{'tool':'alerts'}))['data']
            passed('Strict tool schemas and allowlisted RAG')
            live=await req('POST','/copilot/tools',a,{'tool':'live_intelligence','limit':2})
            assert live['data'] and live['retrieved_at'] and live['reference'].startswith('https://www.cisa.gov/')
            passed('Live intelligence retrieval with source and timestamp')
            from app.storage.models import UserRecord
            from sqlalchemy import update
            async with db.sessions() as session:
                await session.execute(update(UserRecord).where(UserRecord.tenant_id==tenants[1]).values(role='viewer'))
                await session.commit()
            await req('PUT','/copilot/models/primary',b,{'provider':'local_gguf'},403)
            await req('POST','/copilot/knowledge/reindex',b,{},403)
            rejected=await client.put('/copilot/models/primary',headers=a,json={'provider':'bad','api_key':'never-echo-validation-secret'})
            assert rejected.status_code==422 and 'never-echo-validation-secret' not in rejected.text
            oversized=await client.post('/copilot/chat',headers=a,json={'message':'x'*33000})
            assert oversized.status_code==413
            passed('Live RBAC validation redaction and request size limits')
            cfg={'provider':'local_gguf','model':'selected','max_tokens':96,'timeout':240,'context_window':4096}
            await req('PUT','/copilot/models/primary',a,cfg)
            secret='sk-test-'+secrets.token_hex(20)
            await req('PUT','/copilot/models/fallback',a,{'provider':'openai','model':'test','api_key':secret})
            public=await req('GET','/copilot/models',a)
            assert secret not in json.dumps(public) and public['fallback']['has_key']
            async with db.sessions() as session:
                row=await session.scalar(select(CopilotRecord).where(CopilotRecord.tenant_id==tenants[0],CopilotRecord.kind=='provider',CopilotRecord.id=='fallback'))
                assert secret not in json.dumps(row.payload) and row.payload['encrypted_key']
            passed('Encrypted provider secrets and write-only key API')
            # Populate one real database alert from synthetic evidence in an isolated QA tenant.
            from app.storage.models import OperationalAlertRecord
            async with db.sessions() as session:
                alert=OperationalAlertRecord(tenant_id=tenants[0],dedupe_key='qa-only',title='Isolated verification event',severity='critical',score=90,evidence={'source':'isolated-qa','asset':'test-host','confidence':'test data'})
                session.add(alert);await session.commit();alert_id=alert.id
            first=await req('GET','/copilot/notifications',a)
            second=await req('GET','/copilot/notifications',a)
            assert len(first)==len(second)==1
            concurrent=await asyncio.gather(*(req('GET','/copilot/notifications',a) for _ in range(4)))
            assert all(len(rows)==1 for rows in concurrent)
            assert await req('GET','/copilot/notifications',b)==[]
            await req('POST','/copilot/notifications/'+first[0]['id'],b,{'action':'dismiss'},404)
            await req('POST','/copilot/notifications/'+first[0]['id'],a,{'action':'resolve'},409)
            await req('POST','/copilot/notifications/'+first[0]['id'],a,{'action':'snooze'})
            await req('POST','/copilot/notifications/'+first[0]['id'],a,{'action':'mute'})
            await req('POST','/copilot/notifications/'+first[0]['id'],a,{'action':'resolve','confirmed':True})
            passed('Proactive deduplication snooze mute and authorized resolution')
            events=[]
            async with client.stream('POST','/copilot/chat',headers=a,json={'message':'In one short sentence describe whether PostgreSQL is connected. /no_think'}) as response:
                assert response.status_code==200
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        events.append(json.loads(line[6:]))
            if not any(e['type']=='done' for e in events):
                raise AssertionError('GGUF chat did not finish: '+json.dumps([e for e in events if e['type'] in ('error','fallback')]))
            assert any(e['type']=='delta' and e.get('text') for e in events)
            done=next(e for e in events if e['type']=='done')
            assert done['stats']['provider']=='local_gguf'
            ident=done['id']
            stored=await req('GET','/copilot/sessions/'+ident,a)
            assert len(stored['messages'])==2 and stored['messages'][1]['sources']
            await req('GET','/copilot/sessions/'+ident,b,status=404)
            await req('DELETE','/copilot/sessions/'+ident,b,status=404)
            assert (await req('GET','/copilot/sessions?q=PostgreSQL',a))
            passed('Real GGUF inference streaming persistence and conversation isolation')
            print('LOCAL_INFERENCE_RESULT '+json.dumps({'latency_ms':done['stats']['latency_ms'],'text':''.join(e.get('text','') for e in events if e['type']=='delta')}),flush=True)
            # A live generation lease must prevent deletion and preference races.
            from redis.asyncio import Redis
            lease_key='copilot:active:'+hashlib.sha256(f"{tenants[0]}:{stored.get('user_id','')}".encode()).hexdigest()
            me=await req('GET','/auth/me',a)
            lease_key='copilot:active:'+hashlib.sha256(f"{tenants[0]}:{me['user_id']}".encode()).hexdigest()
            async with Redis.from_url(get_settings().redis_url) as cache:
                await cache.set(lease_key,'isolated-qa',ex=20)
                try:
                    await req('DELETE','/copilot/memory',a,status=409)
                    await req('DELETE','/copilot/sessions/'+ident,a,status=409)
                finally:
                    await cache.delete(lease_key)
            passed('In-flight generation protects memory deletion')
            await req('PUT','/copilot/preferences',a,{'memory_enabled':False,'preference':'api_key=DO_NOT_RETAIN'})
            prefs=await req('GET','/copilot/preferences',a)
            assert 'DO_NOT_RETAIN' not in prefs['preference']
            legacy=await req('POST','/ai/chat',a,{'message':'Reply with exactly: Connection verified. /no_think'})
            assert legacy['provider']=='local_gguf' and legacy['message'].strip()
            assert await req('GET','/ai/conversations/'+legacy['conversation_id'],a)==[]
            passed('Existing dashboard uses private gateway and respects disabled memory')
            await req('DELETE','/copilot/memory',a,status=204)
            assert await req('GET','/copilot/sessions',a)==[]
            passed('User memory controls deletion and redaction')
            await req('POST','/auth/logout',a,status=204)
            await req('GET','/copilot/status',a,status=401)
            passed('Logout revocation protects copilot')
            print('COPILOT_VERIFICATION '+json.dumps(checks),flush=True)
        finally:
            async with db.sessions() as session:
                for table in reversed(Base.metadata.sorted_tables):
                    if 'tenant_id' in table.c:
                        await session.execute(delete(table).where(table.c.tenant_id.in_(tenants)))
                await session.execute(delete(TenantRecord).where(TenantRecord.id.in_(tenants)))
                await session.execute(delete(RevokedTokenRecord).where(RevokedTokenRecord.digest.in_([hashlib.sha256(t.encode()).hexdigest() for t in tokens])))
                await session.commit()
            await db.close()
            print('Only temporary copilot QA workspaces removed.',flush=True)


if __name__=='__main__':
    asyncio.run(main())
