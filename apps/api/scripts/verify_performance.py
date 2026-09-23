"""Small local baseline; not a capacity or enterprise scalability claim."""
import asyncio
import json
import secrets
import time
from uuid import uuid4
import httpx
from sqlalchemy import delete
from app.core.config import get_settings
from app.storage.database import Database
from app.storage.models import Base,TenantRecord


async def main():
    db=Database(get_settings());await db.connect()
    tenant='performance-check-'+uuid4().hex[:10]
    results={}
    async with httpx.AsyncClient(base_url='http://nginx:8080/api/v1',timeout=30) as client:
        try:
            r=await client.post('/auth/register',json={'tenant_id':tenant,'email':'qa@example.com','display_name':'Disposable benchmark','password':secrets.token_urlsafe(24)})
            r.raise_for_status();client.headers['Authorization']='Bearer '+r.json()['access_token']
            for name,path in [('api','/dashboard/overview'),('documents','/documents'),('ioc_search','/iocs?q=example'),('alerts','/operational-alerts')]:
                timings=[];errors=0
                for _ in range(30):
                    start=time.perf_counter();response=await client.get(path);timings.append((time.perf_counter()-start)*1000)
                    errors+=response.status_code!=200
                    await asyncio.sleep(.05)
                timings.sort()
                results[name]={'samples':len(timings),'p50_ms':round(timings[14],2),'p95_ms':round(timings[28],2),'p99_ms':round(timings[29],2),'error_rate':errors/30,'dataset':'empty isolated tenant; concurrency 1'}
            print(json.dumps(results,indent=2),flush=True)
        finally:
            async with db.sessions() as session:
                for table in reversed(Base.metadata.sorted_tables):
                    if 'tenant_id' in table.c:
                        await session.execute(delete(table).where(table.c.tenant_id==tenant))
                await session.execute(delete(TenantRecord).where(TenantRecord.id==tenant));await session.commit()
    await db.close()
asyncio.run(main())
