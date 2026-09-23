import hashlib
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.services.intelligence import session
from app.storage.models import CopilotRecord, AuditEventRecord


@asynccontextmanager
async def memory_mutation(p):
    """Share the chat lease so deletion cannot race with an in-flight save."""
    from redis.asyncio import Redis
    from redis.exceptions import RedisError
    key = 'copilot:active:' + hashlib.sha256(f'{p.tenant_id}:{p.user_id}'.encode()).hexdigest()
    lease = str(uuid4())
    acquired = False
    async with Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2) as cache:
        try:
            acquired = await cache.set(key, lease, nx=True, ex=330)
            if not acquired:
                raise HTTPException(409, 'Stop active generation before changing or deleting memory')
            yield
        except RedisError:
            raise HTTPException(503, 'Memory coordination unavailable; retry when Redis is ready') from None
        finally:
            if acquired:
                await cache.eval("if redis.call('GET',KEYS[1])==ARGV[1] then return redis.call('DEL',KEYS[1]) end return 0", 1, key, lease)


def redact(value):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if re.search(r'password|secret|token|api.?key|authorization|private.?key', k, re.I) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if not isinstance(value, str):
        return value
    value = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----', '[REDACTED PRIVATE KEY]', value, flags=re.S)
    value = re.sub(r'(?i)\b(?:sk-[\w-]{12,}|AIza[\w-]{20,}|Bearer\s+[\w.\-]+|eyJ[\w-]+\.[\w-]+\.[\w-]+)', '[REDACTED]', value)
    value = re.sub(r'(?i)(password|api[_ -]?key|secret|access[_ -]?token)\s*[:=]\s*["\']?[^\s,"\'}]+', r'\1=[REDACTED]', value)
    settings = get_settings()
    for field in ("external_ai_api_key", "jwt_secret", "ai_secret_key", "copilot_worker_key", "elasticsearch_password", "smtp_password", "approved_feed_api_key"):
        secret = getattr(settings, field, None)
        if secret and len(secret.get_secret_value()) >= 8:
              value = value.replace(secret.get_secret_value(), '[REDACTED]')
    value = re.sub(r'(://[^\s:/]+:)[^\s@]+@', r'\1[REDACTED]@', value)
    return value


def cipher():
    key = get_settings().ai_secret_key
    if not key:
        raise HTTPException(503, "AI secret encryption key is not configured")
    try:
        return Fernet(key.get_secret_value().encode())
    except ValueError:
        raise HTTPException(503, "AI secret encryption key is invalid")


def scope(p, kind, owner=None):
    return (CopilotRecord.tenant_id == p.tenant_id, CopilotRecord.user_id == (owner or p.user_id), CopilotRecord.kind == kind)


async def get(p, kind, ident, owner=None):
    async with session() as db:
        row = await db.scalar(select(CopilotRecord).where(*scope(p, kind, owner), CopilotRecord.id == ident))
        return row.payload if row else None


async def listing(p, kind, limit=100, owner=None):
    async with session() as db:
        rows = (await db.scalars(select(CopilotRecord).where(*scope(p, kind, owner)).order_by(CopilotRecord.updated_at.desc()).limit(limit))).all()
        return [dict(r.payload, id=r.id) for r in rows]


async def put(p, kind, ident, data, owner=None):
    async with session() as db:
        await db.execute(insert(CopilotRecord).values(tenant_id=p.tenant_id, user_id=owner or p.user_id, kind=kind, id=ident, payload=data).on_conflict_do_update(
            index_elements=['tenant_id', 'user_id', 'kind', 'id'], set_={'payload': data, 'updated_at': datetime.now(UTC)}))
        await db.commit()


async def remove(p, kind, ident=None):
    async with session() as db:
        query = delete(CopilotRecord).where(*scope(p, kind))
        if ident:
            query = query.where(CopilotRecord.id == ident)
        await db.execute(query)
        await db.commit()


async def audit(p, action, metadata=None):
    from app.observability import COPILOT_EVENTS, COPILOT_LATENCY, COPILOT_TOKENS
    COPILOT_EVENTS.labels(action=action).inc()
    if action == 'completion' and metadata:
        COPILOT_LATENCY.labels(provider=metadata['provider']).observe(metadata['latency_ms']/1000)
        if isinstance(metadata.get('tokens'), (int, float)):
            COPILOT_TOKENS.labels(provider=metadata['provider']).inc(max(0, metadata['tokens']))
    async with session() as db:
        db.add(AuditEventRecord(tenant_id=p.tenant_id, actor_id=p.user_id, action='copilot.'+action,
            resource_type='copilot', resource_id=p.user_id, outcome='failure' if action.endswith('.failed') else 'success', metadata_json=redact(metadata or {})))
        await db.commit()


async def limit(p, purpose='chat', maximum=12, seconds=60):
    from redis.asyncio import Redis
    from redis.exceptions import RedisError
    key = hashlib.sha256(f'{p.tenant_id}:{p.user_id}:{purpose}'.encode()).hexdigest()
    try:
        async with Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2) as cache:
            count = await cache.eval("local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return n", 1, 'copilot:rate:'+key, seconds)
            if count > maximum:
                raise HTTPException(429, 'Request limit reached; retry shortly', headers={'Retry-After': str(seconds)})
            if purpose == 'chat':
                tenant_key = hashlib.sha256(p.tenant_id.encode()).hexdigest()
                tenant_count = await cache.eval("local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return n", 1, 'copilot:tenant-rate:'+tenant_key, seconds)
                if tenant_count > 60:
                    raise HTTPException(429, 'Workspace AI request limit reached', headers={'Retry-After': str(seconds)})
    except RedisError:
        raise HTTPException(503, 'Copilot rate-limit storage unavailable; retry when Redis is ready')
