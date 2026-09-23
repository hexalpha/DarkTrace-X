"""Live integration verification; temporary tenants are removed in finally."""
import asyncio
import hashlib
import os
import secrets
from uuid import uuid4
import httpx
from sqlalchemy import delete
if os.environ.get("DARKTRACE_TEST_USE_ENV") != "1":
    from scripts.local_runtime import environment
    os.environ.update(environment())
from app.core.config import get_settings
from app.storage.database import Database
from app.storage.models import Base, TenantRecord, RevokedTokenRecord
from app.search.service import SearchService
from tests.test_advanced import events


async def main():
    settings=get_settings(); db=Database(settings); await db.connect()
    search=SearchService(settings); await search.connect()
    tenants=[f"verification-{uuid4().hex[:16]}" for _ in range(2)]
    tokens=[]
    async with httpx.AsyncClient(base_url=os.environ.get("DARKTRACE_TEST_API_URL", "http://127.0.0.1:8000/api/v1"), timeout=180) as client:
        async def request(method,path,headers=None,body=None,expected=200):
            r=await client.request(method,path,headers=headers,json=body)
            if r.status_code!=expected:
                detail=r.json().get('detail','') if 'json' in r.headers.get('content-type','') else ''
                raise AssertionError(f"{method} {path}: expected {expected}, got {r.status_code}; {str(detail)[:300]}")
            return r
        try:
            password=secrets.token_urlsafe(24)
            identities=[]
            for tenant in tenants:
                r=await request('POST','/auth/register',body={'email':'qa@example.com','display_name':'Verification','password':password,'tenant_id':tenant},expected=201)
                token=r.json()['access_token']; tokens.append(token); identities.append({'Authorization':f'Bearer {token}'})
            a,b=identities
            await request('POST','/auth/login',body={'email':'qa@example.com','password':'incorrect','tenant_id':tenants[0]},expected=401)
            await request('GET','/auth/me',headers=a)
            print('PASS registration, login, authenticated tenant identity',flush=True)
            user=(await request('POST','/tenants/users',headers=a,body={'email':'viewer@example.com','display_name':'Viewer','password':password,'role':'viewer'},expected=201)).json()
            viewer=(await request('POST','/auth/login',body={'email':'viewer@example.com','password':password,'tenant_id':tenants[0]})).json()['access_token']; tokens.append(viewer)
            vh={'Authorization':f'Bearer {viewer}'}
            await request('GET','/tenants/users',headers=vh,expected=403)
            await request('PATCH',f"/tenants/users/{user['id']}/role",headers=a,body={'role':'analyst'})
            assert (await request('GET','/auth/me',headers=vh)).json()['role']=='analyst'
            print('PASS RBAC and immediate role change on existing session',flush=True)
            ioc=(await request('POST','/iocs',headers=a,body={'type':'domain','value':'verification.example','source':'isolated integration test','confidence':80,'risk_score':70,'tags':['qa']},expected=201)).json()
            assert (await request('GET','/iocs',headers=b)).json()==[]
            await request('POST','/assets',headers=a,body={'hostname':'qa-host','owner':'QA','risk_score':10},expected=201)
            assert len((await request('GET','/assets',headers=a)).json())==1
            unknown=(await request('POST','/reputation/domain',headers=b,body={'value':'verification.example'})).json()
            assert unknown['verdict']=='unknown' and unknown['confidence']==0
            hunt=(await request('POST','/hunts',headers=a,body={'hypothesis':'Find the isolated verification indicator','query':'verification','time_range_hours':24})).json()
            assert hunt['findings']==1
            await request('POST','/intelligence/reindex',headers=a,body={})
            correlated=(await request('GET','/intelligence/iocs/correlate?indicator_type=domain&value=verification.example',headers=a)).json()
            assert correlated['correlation_count']==1
            assert (await request('GET','/intelligence/graph',headers=b)).json()['nodes']==[]
            await request('POST','/threat-actors',headers=a,body={'name':'Verification cluster','summary':'Isolated test attribution record, not a real threat actor.','sources':['https://example.com/qa'],'techniques':['T1566']},expected=201)
            assert len((await request('GET','/threat-actors/verified',headers=a)).json())==1
            assert (await request('GET','/threat-actors/verified',headers=b)).json()==[]
            print('PASS persistent IOCs, assets, hunts, Elasticsearch correlation, graph and actor isolation',flush=True)
            payload={'events':events([2]*25+[20]*5)}
            payload['events'][0]['location']={'latitude':28.6,'longitude':77.2,'name':'Synthetic QA location','source':'isolated verification collector'}
            payload['events'][1]['location']=payload['events'][0]['location']
            result=(await request('POST','/telemetry',headers=a,body=payload,expected=201)).json()
            assert result['inserted']==30 and result['created_alerts']==5
            again=(await request('POST','/telemetry',headers=a,body=payload,expected=201)).json()
            assert again['duplicates']==30 and again['created_alerts']==0
            regions=(await request('GET','/dashboard/overview',headers=a)).json()['regions']
            assert len(regions)==1 and regions[0]['events']==2 and regions[0]['latitude']==28.6
            assert regions[0]['source']=='isolated verification collector'
            assert (await request('GET','/dashboard/overview',headers=b)).json()['regions']==[]
            print('PASS reported geography, provenance, replay counts and tenant isolation',flush=True)
            detection=(await request('GET','/detection/overview',headers=a)).json()
            assert len(detection['anomalies'])==5 and detection['predictions']
            alert=(await request('GET','/operational-alerts',headers=a)).json()[0]
            await request('PATCH',f"/operational-alerts/{alert['id']}",headers=b,body={'status':'resolved'},expected=404)
            await request('PATCH',f"/operational-alerts/{alert['id']}",headers=a,body={'status':'resolved'})
            print('PASS anomaly detection, forecast, replay protection and alert triage',flush=True)
            await request('POST','/monitors/keywords',headers=a,body={'term':'verification-keyword'},expected=201)
            from datetime import UTC,datetime
            source={'source':'isolated QA','source_type':'internal','legal_basis':'Synthetic integration test in temporary tenant','items':[{'external_id':'qa-one','title':'verification-keyword observed','summary':'Isolated test evidence.','source_url':'https://example.com/qa','observed_at':datetime.now(UTC).isoformat()}]}
            assert (await request('POST','/exposure/ingest',headers=a,body=source,expected=201)).json()['created_alerts']==1
            assert (await request('POST','/exposure/ingest',headers=a,body=source,expected=201)).json()['created_alerts']==0
            assert len((await request('GET','/exposure/mentions',headers=a)).json())==1
            assert (await request('GET','/exposure/mentions',headers=b)).json()==[]
            print('PASS source ingestion, keyword matches, provenance and tenant isolation',flush=True)
            await request('PUT','/marketplace/behavior-analyzer',headers=a,body={'enabled':True})
            assert len((await request('POST','/marketplace/behavior-analyzer/run',headers=a,body={})).json()['anomalies'])==5
            await request('POST','/marketplace/behavior-analyzer/run',headers=b,body={},expected=409)
            await request('PUT','/marketplace/behavior-analyzer',headers=a,body={'enabled':False})
            await request('POST','/marketplace/behavior-analyzer/run',headers=a,body={},expected=409)
            await request('DELETE','/marketplace/behavior-analyzer',headers=a,expected=204)
            mcp=(await request('POST','/mcp',headers=a,body={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'telemetry_health','arguments':{}}})).json()
            assert not mcp['result']['isError']
            print('PASS plugin lifecycle and authenticated MCP execution',flush=True)
            feed=(await request('POST','/threat-feeds/cisa-kev/ingest',headers=a,body={})).json()
            assert feed['received']>0
            assert (await request('GET','/cve/dashboard',headers=a)).json()
            print(f"PASS live CISA feed and CVE dashboard ({feed['received']} source records)",flush=True)
            for fmt,magic in [('pdf',b'%PDF'),('docx',b'PK'),('xlsx',b'PK')]:
                report=await request('POST',f'/reports/{fmt}',headers=a,body={'title':'Verification <safe> & sourced report'})
                assert report.content.startswith(magic)
            print('PASS authenticated PDF, DOCX and spreadsheet exports',flush=True)
            ai_provider=os.environ.get('DARKTRACE_TEST_AI_PROVIDER','local_gguf' if settings.local_llm_enabled else 'lm_studio')
            ai=(await request('POST','/ai/chat',headers=a,body={'provider':ai_provider,'message':'Summarize the recorded evidence in two short sentences. State that this is verification data. /no_think'})).json()
            assert ai['message'].strip() and ai['provider']==ai_provider
            assert (await request('GET',f"/ai/conversations/{ai['conversation_id']}",headers=b)).json()==[]
            print('PASS live local AI completion, source context and conversation isolation',flush=True)
            await request('POST','/auth/logout',headers=a,expected=204)
            await request('GET','/auth/me',headers=a,expected=401)
            print('PASS logout invalidates token; full workflow complete',flush=True)
        finally:
            if search.ready:
                for index in [search.IOC_INDEX,search.ACTOR_INDEX]:
                    await search.client.delete_by_query(index=index,query={'terms':{'tenant_id':tenants}},refresh=True)
            async with db.sessions() as session:
                for table in reversed(Base.metadata.sorted_tables):
                    if 'tenant_id' in table.c:
                        await session.execute(delete(table).where(table.c.tenant_id.in_(tenants)))
                await session.execute(delete(TenantRecord).where(TenantRecord.id.in_(tenants)))
                await session.execute(delete(RevokedTokenRecord).where(RevokedTokenRecord.digest.in_([hashlib.sha256(t.encode()).hexdigest() for t in tokens])))
                await session.commit()
            await search.close();await db.close()
            print('Temporary verification workspaces removed; public CISA records retained.',flush=True)


if __name__=='__main__':
    asyncio.run(main())
