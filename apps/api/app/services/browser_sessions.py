import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, update

from app.core.security import Principal, Role, create_access_token
from app.services.intelligence import session
from app.storage.models import BrowserSessionRecord, TenantRecord, UserRecord

ACCESS = 'dtx_access'
REFRESH = 'dtx_refresh'
CSRF = 'dtx_csrf'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def check_csrf(request):
    cookie = request.cookies.get(CSRF, '')
    supplied = request.headers.get('x-csrf-token', '')
    if not cookie or not secrets.compare_digest(cookie, supplied):
        raise HTTPException(403, 'Request verification failed')


def cookies(response, settings, access, refresh, csrf):
    common = dict(secure=settings.app_env == 'production', samesite='strict', path='/')
    response.set_cookie(ACCESS, access, httponly=True, max_age=settings.access_token_expire_minutes*60, **common)
    response.set_cookie(REFRESH, refresh, httponly=True, max_age=7*86400, **common)
    response.set_cookie(CSRF, csrf, httponly=False, max_age=7*86400, **common)


async def issue(principal, response, settings):
    refresh, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    family = str(uuid4())
    async with session() as db:
        db.add(BrowserSessionRecord(digest=digest(refresh), family=family, tenant_id=principal.tenant_id,
            user_id=principal.user_id, csrf=digest(csrf), revoked=False, expires_at=datetime.now(UTC)+timedelta(days=7)))
        await db.commit()
    access = create_access_token(principal, settings, family)
    cookies(response, settings, access, refresh, csrf)
    return access


async def rotate(request, response, settings):
    check_csrf(request)
    value = request.cookies.get(REFRESH, '')
    async with session() as db:
        record = await db.scalar(select(BrowserSessionRecord).where(BrowserSessionRecord.digest == digest(value)).with_for_update())
        if not record or record.expires_at <= datetime.now(UTC):
            raise HTTPException(401, 'Session expired')
        if record.revoked:
            await db.execute(update(BrowserSessionRecord).where(BrowserSessionRecord.family==record.family).values(revoked=True))
            await db.commit()
            raise HTTPException(401, 'Session expired')
        if not secrets.compare_digest(record.csrf, digest(request.cookies.get(CSRF, ''))):
            raise HTTPException(403, 'Request verification failed')
        user = await db.get(UserRecord, record.user_id)
        tenant = await db.get(TenantRecord, record.tenant_id)
        if not user or not user.active or user.tenant_id != record.tenant_id or not tenant or not tenant.active:
            raise HTTPException(401, 'Session expired')
        principal = Principal(user_id=user.id, tenant_id=user.tenant_id, email=user.email, role=Role(user.role))
        refresh, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        record.revoked = True
        db.add(BrowserSessionRecord(digest=digest(refresh), family=record.family, tenant_id=record.tenant_id,
            user_id=record.user_id, csrf=digest(csrf), revoked=False, expires_at=record.expires_at))
        await db.commit()
    cookies(response, settings, create_access_token(principal, settings, record.family), refresh, csrf)


async def revoke(request, response):
    value = request.cookies.get(REFRESH)
    if value:
        async with session() as db:
            record = await db.get(BrowserSessionRecord, digest(value))
            if record:
                await db.execute(update(BrowserSessionRecord).where(BrowserSessionRecord.family==record.family).values(revoked=True))
                await db.commit()
    for name in (ACCESS, REFRESH, CSRF):
        response.delete_cookie(name, path='/')
