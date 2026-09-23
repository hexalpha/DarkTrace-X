"""Explicit read-only tools. No dynamic imports, SQL, URLs or paths from model arguments."""
import asyncio
import hashlib
import json
import math
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from redis.asyncio import Redis

from app.core.config import get_settings
from app.services import copilot_store as store
from app.services.copilot_gateway import local_health
from app.services.intelligence import intelligence_service, session
from app.storage.models import OperationalAlertRecord, TelemetryRecord, ThreatFeedItemRecord

ALLOWLIST = ('README.md', 'docs/ARCHITECTURE.md', 'docs/API.md', 'docs/DATABASE.md', 'docs/DEPLOYMENT.md', 'docs/SECURITY.md', 'docs/DETECTION_EXTENSIONS.md', 'docs/COPILOT.md')


class Knowledge:
    def __init__(self):
        self.chunks = []
        self.loaded_at = None

    def refresh(self):
        root = Path(get_settings().project_knowledge_root).resolve()
        chunks = []
        for relative in ALLOWLIST:
            path = root / relative
            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root) or path.stat().st_size > 150000:
                continue
            content = store.redact(path.read_text(encoding='utf-8'))
            for offset in range(0, len(content), 1400):
                body = content[offset:offset+1600]
                chunks.append({'source':relative, 'reference':f'{relative}#chunk-{offset//1400}', 'text':body, 'terms':Counter(re.findall(r'\w+', body.lower())), 'sha256':hashlib.sha256(body.encode()).hexdigest()})
        self.chunks = chunks
        self.loaded_at = datetime.now(UTC).isoformat()

    def search(self, query, limit=3):
        if self.loaded_at is None:
            self.refresh()
        terms = set(re.findall(r'\w+', query.lower()))
        ranked = []
        for chunk in self.chunks:
            score = sum((1+math.log(chunk['terms'][t])) * math.log(1+len(self.chunks)/(1+sum(t in c['terms'] for c in self.chunks))) for t in terms if chunk['terms'][t])
            if score:
                ranked.append((score, chunk))
        return [{k:v for k,v in c.items() if k!='terms'} | {'retrieved_at':self.loaded_at,'mode':'LIVE'} for _,c in sorted(ranked,key=lambda r:r[0],reverse=True)[:limit]]

    def status(self):
        if self.loaded_at is None:
            self.refresh()
        return {'mode':'LIVE' if self.chunks else 'UNAVAILABLE','method':'lexical TF-IDF retrieval', 'chunks':len(self.chunks),'sources':sorted({c['source'] for c in self.chunks}),'indexed_at':self.loaded_at}


knowledge = Knowledge()


async def health():
    async def check(name):
        try:
            if name == 'postgresql':
                async with session() as db:
                    await db.execute(text('SELECT 1'))
            elif name == 'redis':
                async with Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2) as r:
                    await r.ping()
            else:
                from app.search.service import search_service
                if not search_service or not search_service.client or not await search_service.client.ping():
                    raise RuntimeError()
            return name, 'ONLINE'
        except Exception:
            return name, 'OFFLINE'
    results = await asyncio.gather(*(check(n) for n in ('postgresql','redis','elasticsearch')))
    return {'services':dict(results), 'local_model':await local_health(), 'observed_at':datetime.now(UTC).isoformat(), 'mode':'LIVE'}


class ToolCall(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tool: Literal['alerts','ioc','cves','feeds','actors','health','mentions','events','assets','project_knowledge','live_intelligence']
    query: str = Field('', max_length=240)
    id: str | None = Field(None, max_length=80)
    limit: int = Field(3, ge=1, le=10)


async def invoke(p, call: ToolCall):
    stamp = datetime.now(UTC).isoformat()
    tool = call.tool
    source = 'DarkTrace X / '+tool
    reference = '/api/v1/' + tool
    mode = 'LIVE'
    if tool == 'health':
        data = await health()
        from app.services.copilot_gateway import configurations
        data['configured_models'] = await configurations(p)
    elif tool == 'project_knowledge':
        data = knowledge.search(call.query, call.limit)
    elif tool == 'live_intelligence':
        await store.limit(p, 'live_intelligence', 4, 300)
        from app.services.operations import CISA_KEV_URL
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            async with client.stream('GET', CISA_KEV_URL) as r:
                r.raise_for_status()
                body = b''
                async for chunk in r.aiter_bytes():
                    body += chunk
                    if len(body) > 8_000_000:
                        raise ValueError('Feed exceeds size limit')
        items = json.loads(body).get('vulnerabilities', [])
        data = [{k:item.get(k) for k in ('cveID','vendorProject','product','vulnerabilityName','dateAdded','requiredAction','knownRansomwareCampaignUse')} for item in sorted(items,key=lambda i:i.get('dateAdded',''),reverse=True) if not call.query or call.query.casefold() in json.dumps(item).casefold()][:call.limit]
        source, reference = 'CISA KEV (live retrieval)', CISA_KEV_URL
    elif tool == 'alerts':
        async with session() as db:
            q = select(OperationalAlertRecord).where(OperationalAlertRecord.tenant_id==p.tenant_id)
            if call.id:
                q = q.where(OperationalAlertRecord.id==call.id)
            elif call.query.lower() == 'today':
                q = q.where(OperationalAlertRecord.created_at >= datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0))
            elif call.query.lower() in ('critical','high','medium','low','info'):
                q = q.where(OperationalAlertRecord.severity==call.query.lower())
            elif call.query:
                q = q.where(OperationalAlertRecord.title.ilike('%'+call.query.replace('%','').replace('_','')+'%'))
            rows = (await db.scalars(q.order_by(OperationalAlertRecord.score.desc()).limit(call.limit))).all()
            data = [{'id':r.id,'title':r.title,'severity':r.severity,'score':r.score,'status':r.status,'evidence':r.evidence,'observed_at':r.created_at.isoformat()} for r in rows]
    elif tool == 'events':
        async with session() as db:
            rows = (await db.scalars(select(TelemetryRecord).where(TelemetryRecord.tenant_id==p.tenant_id).order_by(TelemetryRecord.observed_at.desc()).limit(call.limit))).all()
            data = [r.payload for r in rows]
    elif tool in {'feeds','cves'}:
        async with session() as db:
            q = select(ThreatFeedItemRecord)
            if call.query:
                q = q.where(ThreatFeedItemRecord.external_id.ilike('%'+call.query.replace('%','').replace('_','')+'%'))
            rows = (await db.scalars(q.order_by(ThreatFeedItemRecord.published_at.desc()).limit(call.limit))).all()
            data = [{'id':r.external_id,'title':r.title,'summary':r.summary[:700],'source':r.source,'retrieved_at':r.ingested_at.isoformat(),'reference':'https://www.cisa.gov/known-exploited-vulnerabilities-catalog'} for r in rows]
        mode = 'LIVE' if data else 'UNAVAILABLE'
    elif tool == 'ioc':
        data = [i.model_dump(mode='json') for i in (await intelligence_service.list_iocs(p.tenant_id, call.query or None))[:call.limit]]
    elif tool == 'actors':
        from app.api.v1.routes import search
        data = (await search().list_actors(p.tenant_id))[:call.limit]
    else:
        data = await intelligence_service.documents(p.tenant_id, tool, call.limit)
    result = store.redact({'tool':tool,'source':source,'reference':reference,'retrieved_at':stamp,'mode':mode,'data':data})
    await store.put(p, 'tool_call', str(uuid4()), {'tool':tool,'at':stamp,'source':source,'mode':mode})
    await store.audit(p, 'tool.called', {'tool':tool})
    return result


def initial_tools(question, alert_id=None):
    lower = question.lower()
    if alert_id:
        return [ToolCall(tool='alerts', id=alert_id)]
    if any(t in lower for t in ('dark web','dark-web','monitoring results','mention','exposure','leak')):
        return [ToolCall(tool='mentions',limit=5)]
    if any(t in lower for t in ('latest', 'current news', 'new vulnerabilities')):
        return [ToolCall(tool='live_intelligence')]
    if any(t in lower for t in ('health','running','connected','unhealthy','provider','services')):
        return [ToolCall(tool='health')]
    if any(t in lower for t in ('dark web','dark-web','mention','exposure','leak')):
        return [ToolCall(tool='mentions',limit=5)]
    cve = re.search(r'CVE-\d{4}-\d+',question,re.I)
    if cve:
        return [ToolCall(tool='cves',query=cve.group().upper())]
    if any(t in lower for t in ('alert','threat','incident')):
        return [ToolCall(tool='alerts',query='critical' if 'critical' in lower else 'today' if 'today' in lower else '')]
    if 'ioc' in lower or 'indicator' in lower:
        return [ToolCall(tool='ioc')]
    return [ToolCall(tool='project_knowledge',query=question)]
