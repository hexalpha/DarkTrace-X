"""Live approved-source workflow in a disposable tenant."""
import asyncio
import secrets
import time
from uuid import uuid4
import httpx
from sqlalchemy import delete, select
from app.core.config import get_settings
from app.storage.database import Database
from app.storage.models import Base, TenantRecord, SourceDocumentRecord, SourceRecord
from datetime import UTC,datetime,timedelta


async def main():
    tenant='source-check-'+uuid4().hex[:12]
    db=Database(get_settings()); await db.connect()
    async with httpx.AsyncClient(base_url='http://nginx:8080/api/v1',timeout=240) as client:
        async def call(method,path,body=None,code=200):
            response=await client.request(method,path,json=body)
            assert response.status_code==code, (path,response.status_code,response.text[:180])
            return response.json() if response.content else None
        try:
            password=secrets.token_urlsafe(24)
            identity={'tenant_id':tenant,'email':'source@example.com','password':password}
            token=await call('POST','/auth/register',{**identity,'display_name':'Disposable source verification'},201)
            client.headers['Authorization']='Bearer '+token['access_token']
            await call('POST','/tenants/users',{'email':'analyst@example.com','password':password,'display_name':'QA Analyst','role':'analyst'},201)
            await call('POST','/auth/login',identity)
            await call('POST','/monitors/keywords',{'term':'CVE','categories':['verification']},201)
            payload={'name':'Official CISA KEV verification','url':'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json','source_type':'public_threat_intel','category':'official advisories','parser_type':'json','trust_level':'high','crawl_policy':'hourly'}
            source=await call('POST','/sources',payload,201)
            validation=await call('POST',f"/sources/{source['id']}/validate")
            assert validation['valid'],validation
            async with db.sessions() as session:
                saved=await session.get(SourceRecord,(tenant,source['id']))
                saved.next_scheduled_at=datetime.now(UTC)+timedelta(hours=1)
                await session.commit()
            await call('POST',f"/sources/{source['id']}/enable")
            print('PASS tenant, user, login, source registration/validation, enabled hourly schedule',flush=True)
            started=time.perf_counter()
            result=await call('POST',f"/sources/{source['id']}/crawl",code=202)
            assert result['job']['status']=='completed',result['job']
            documents=await call('GET','/documents');entities=await call('GET','/entities');events=await call('GET','/events');alerts=await call('GET','/operational-alerts')
            assert documents and entities and events and alerts
            detail=await call('GET','/documents/'+documents[0]['id'])
            assert detail['normalized_text'] and detail['metadata']['entries']
            async with db.sessions() as session:
                raw=await session.scalar(select(SourceDocumentRecord.raw_content).where(SourceDocumentRecord.tenant_id==tenant))
                assert raw and 'vulnerabilities' in raw
            print('PASS raw document, JSON normalization, entities, observations/events, keyword alert; crawl seconds=',round(time.perf_counter()-started,2),flush=True)
            again=await call('POST',f"/sources/{source['id']}/crawl",code=202)
            assert again['job']['duplicates_found']==1
            assert len(await call('GET','/operational-alerts'))==len(alerts)
            audit=await call('GET','/audit/events/operational')
            assert any(row['action']=='source.crawl.completed' for row in audit)
            await call('POST',f"/sources/{source['id']}/disable")
            for page in ('documents','entities','events','crawls'):
                assert (await client.get('http://nginx:8080/'+page)).status_code==200
            print('PASS deduplication, alert deduplication, crawl audit trail, disabled source and frontend route HTTP responses',flush=True)
            print('NOTE authenticated visual UI verification is separate',flush=True)
        finally:
            async with db.sessions() as session:
                for table in reversed(Base.metadata.sorted_tables):
                    if 'tenant_id' in table.c:
                        await session.execute(delete(table).where(table.c.tenant_id==tenant))
                await session.execute(delete(TenantRecord).where(TenantRecord.id==tenant)); await session.commit()
    await db.close()
asyncio.run(main())
