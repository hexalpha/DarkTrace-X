from contextlib import asynccontextmanager
import hashlib
from uuid import uuid4
from redis.asyncio import Redis
from redis.exceptions import RedisError
from fastapi import HTTPException
from app.core.config import get_settings


@asynccontextmanager
async def source_lock(tenant_id, source_id):
    key = 'crawler:lease:' + hashlib.sha256(f'{tenant_id}:{source_id}'.encode()).hexdigest()
    lease = str(uuid4())
    acquired = False
    async with Redis.from_url(get_settings().redis_url, socket_timeout=2, socket_connect_timeout=2) as cache:
        try:
            acquired = await cache.set(key, lease, nx=True, ex=300)
            if not acquired:
                raise HTTPException(409, 'This source already has an active crawl')
            yield
        except RedisError:
            raise HTTPException(503, 'Crawler coordination is unavailable') from None
        finally:
            if acquired:
                await cache.eval("if redis.call('GET',KEYS[1])==ARGV[1] then return redis.call('DEL',KEYS[1]) end return 0",1,key,lease)
