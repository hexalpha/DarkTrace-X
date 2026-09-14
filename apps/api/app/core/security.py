from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import Settings, get_settings


class Role(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    LEAD = "lead"
    ADMIN = "admin"


class Principal(BaseModel):
    user_id: str
    tenant_id: str
    role: Role
    email: str


bearer = HTTPBearer(auto_error=False)


def create_access_token(principal: Principal, settings: Settings) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = principal.model_dump() | {"exp": expires_at, "sub": principal.user_id}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")


def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    """Development has a visible demo principal; production is bearer-token only."""
    if credentials is None:
        if settings.app_env != "production":
            return Principal(
                user_id="demo-analyst",
                tenant_id="demo-tenant",
                role=Role.ANALYST,
                email="analyst@darktracex.local",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    try:
        claims = jwt.decode(credentials.credentials, settings.jwt_secret.get_secret_value(), algorithms=["HS256"])
        return Principal(
            user_id=claims["sub"],
            tenant_id=claims["tenant_id"],
            role=Role(claims["role"]),
            email=claims["email"],
        )
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc


def require_role(*roles: Role):
    def dependency(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    return dependency

