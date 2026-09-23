"""Atomic account-wide login budget shared across API replicas."""
import asyncio
import hashlib
import logging

from fastapi import HTTPException
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)
WINDOW = 900
THRESHOLD = 8
RESERVE = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return n"


def account_key(payload):
    return 'auth:attempts:' + hashlib.sha256((payload.tenant_id + ':' + payload.email.strip().casefold()).encode()).hexdigest()


async def reserve(payload):
    key = account_key(payload)
    try:
        async with Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2) as cache:
            count = await cache.eval(RESERVE, 1, key, WINDOW)
    except RedisError:
        raise HTTPException(503, 'Sign-in temporarily unavailable') from None
    if count > THRESHOLD:
        logger.warning('auth.locked account_hash=%s', key.split(':')[-1])
        raise HTTPException(429, 'Sign-in temporarily unavailable; retry later', headers={'Retry-After': str(WINDOW)})
    if count > 1:
        await asyncio.sleep(min(2, 0.125 * 2 ** (count - 2)))


async def finish(payload, success):
    key = account_key(payload)
    logger.info('auth.%s account_hash=%s', 'success' if success else 'failure', key.split(':')[-1])
    if success:
        try:
            async with Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2) as cache:
                await cache.delete(key)
        except RedisError:
            raise HTTPException(503, 'Sign-in temporarily unavailable') from None
