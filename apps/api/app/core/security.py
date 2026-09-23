import hashlib
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated
from uuid import uuid4
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWTError as JWTError
from pydantic import BaseModel
from app.core.config import Settings, get_settings


class Role(StrEnum):
    VIEWER = 'viewer'
    ANALYST = 'analyst'
    LEAD = 'lead'
    ADMIN = 'admin'


class Principal(BaseModel):
    user_id: str
    tenant_id: str
    role: Role
    email: str


bearer = HTTPBearer(auto_error=False)


def create_access_token(principal: Principal, settings: Settings, browser_family=None) -> str:
    now = datetime.now(UTC)
    payload = principal.model_dump() | {'exp': now + timedelta(minutes=settings.access_token_expire_minutes), 'iat': now, 'sub': principal.user_id, 'jti': str(uuid4()), 'iss': 'darktracex', 'aud': 'darktracex-api'}
    if browser_family:
        payload['sid'] = browser_family
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm='HS256')


def decode_access_token(token, settings):
    try:
        claims = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=['HS256'], audience='darktracex-api', issuer='darktracex', options={'require': ['exp', 'sub']})
        return Principal(user_id=claims['sub'], tenant_id=claims['tenant_id'], role=Role(claims['role']), email=claims['email'])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(401, 'Invalid or expired access token') from exc


async def validate_active_token(token, settings):
    from app.storage.models import UserRecord, TenantRecord, RevokedTokenRecord
    from app.services.intelligence import session
    principal = decode_access_token(token, settings)
    async with session() as db:
        claims = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=['HS256'], audience='darktracex-api', issuer='darktracex')
        if claims.get('sid'):
            from sqlalchemy import select
            from app.storage.models import BrowserSessionRecord
            active = await db.scalar(select(BrowserSessionRecord.digest).where(
                BrowserSessionRecord.family == claims['sid'], BrowserSessionRecord.user_id == principal.user_id,
                BrowserSessionRecord.tenant_id == principal.tenant_id, BrowserSessionRecord.revoked.is_(False),
                BrowserSessionRecord.expires_at > datetime.now(UTC)).limit(1))
            if not active:
                raise HTTPException(401, 'Session is no longer active')
        revoked = await db.get(RevokedTokenRecord, hashlib.sha256(token.encode()).hexdigest())
        user = await db.get(UserRecord, principal.user_id)
        tenant = await db.get(TenantRecord, principal.tenant_id)
        if revoked or not user or not user.active or user.tenant_id != principal.tenant_id or not tenant or not tenant.active:
            raise HTTPException(401, 'Session is no longer active')
        return Principal(user_id=user.id, tenant_id=user.tenant_id, role=Role(user.role), email=user.email)


async def current_principal(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], settings: Annotated[Settings, Depends(get_settings)]) -> Principal:
    from app.services.browser_sessions import ACCESS, check_csrf
    token = credentials.credentials if credentials else request.cookies.get(ACCESS)
    if not token:
        raise HTTPException(401, 'Sign in to access your workspace', headers={'WWW-Authenticate': 'Bearer'})
    if not credentials and request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        check_csrf(request)
    principal = await validate_active_token(token, settings)
    request.state.tenant_id = principal.tenant_id
    return principal


def require_role(*roles: Role):
    def dependency(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if principal.role not in roles:
            raise HTTPException(403, 'Insufficient role')
        return principal
    return dependency
