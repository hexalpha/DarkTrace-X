"""Tenant-scoped, signed webhook delivery for real DarkTrace X events."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import socket
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from sqlalchemy import select, update

from app.core.security import Principal
from app.core.config import get_settings
from app.services.safe_http import public_request
from app.domain.schemas import Severity, WebhookSubscription
from app.services import copilot_store
from app.storage import database as database_module
from app.storage.models import WebhookSubscriptionRecord

_RANK = {Severity.INFO.value: 0, Severity.LOW.value: 1, Severity.MEDIUM.value: 2, Severity.HIGH.value: 3, Severity.CRITICAL.value: 4}


def validate_webhook_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Webhook URL must be HTTPS without credentials, query parameters or fragments")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "host.docker.internal", "metadata.google.internal"}:
        raise ValueError("Webhook URL cannot target local or metadata services")
    try:
        address = ipaddress.ip_address(host)
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast:
            raise ValueError("Webhook URL cannot target a private or local address")
    except ValueError as exc:
        if str(exc).startswith("Webhook URL"):
            raise
    return parsed.geturl()


def _public_addresses(host: str) -> bool:
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return False
    return bool(addresses) and all(not (ipaddress.ip_address(item[4][0]).is_private or ipaddress.ip_address(item[4][0]).is_loopback or ipaddress.ip_address(item[4][0]).is_link_local or ipaddress.ip_address(item[4][0]).is_reserved) for item in addresses)


class WebhookService:
    async def register(self, principal: Principal, payload: WebhookSubscription) -> dict:
        url = validate_webhook_url(str(payload.url))
        types = sorted({item.strip().lower() for item in payload.event_types if item.strip()})
        if not types or any(len(item) > 80 or not item.replace(".", "").replace("_", "").isalnum() for item in types):
            raise ValueError("Event types must be simple names such as alert.created")
        db = database_module.database
        async with db.sessions() as session:
            record = WebhookSubscriptionRecord(tenant_id=principal.tenant_id, name=payload.name.strip(), url=url, event_types=types, minimum_severity=payload.minimum_severity.value, encrypted_secret=copilot_store.cipher().encrypt(payload.secret.get_secret_value().encode()).decode())
            session.add(record)
            await session.flush()
            session.add(__import__("app.storage.models", fromlist=["AuditEventRecord"]).AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="webhook.created", resource_type="webhook", resource_id=record.id, outcome="success", metadata_json={"name": record.name, "event_types": types}))
            await session.commit()
            return {"id": record.id, "name": record.name, "url": record.url, "event_types": record.event_types, "minimum_severity": record.minimum_severity, "enabled": record.enabled, "created_at": record.created_at}

    async def list(self, principal: Principal) -> list[dict]:
        db = database_module.database
        async with db.sessions() as session:
            rows = (await session.scalars(select(WebhookSubscriptionRecord).where(WebhookSubscriptionRecord.tenant_id == principal.tenant_id).order_by(WebhookSubscriptionRecord.created_at.desc()))).all()
        return [{"id": row.id, "name": row.name, "url": row.url, "event_types": row.event_types, "minimum_severity": row.minimum_severity, "enabled": row.enabled, "failure_count": row.failure_count, "last_delivered_at": row.last_delivered_at, "created_at": row.created_at} for row in rows]

    async def remove(self, principal: Principal, ident: str) -> bool:
        db = database_module.database
        async with db.sessions() as session:
            row = await session.scalar(select(WebhookSubscriptionRecord).where(WebhookSubscriptionRecord.tenant_id == principal.tenant_id, WebhookSubscriptionRecord.id == ident).with_for_update())
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def dispatch(self, tenant_id: str, event_type: str, severity: str, payload: dict) -> int:
        db = database_module.database
        if not db or not db.ready:
            return 0
        async with db.sessions() as session:
            rows = (await session.scalars(select(WebhookSubscriptionRecord).where(WebhookSubscriptionRecord.tenant_id == tenant_id, WebhookSubscriptionRecord.enabled.is_(True)))).all()
        eligible = [row for row in rows if (event_type in row.event_types or "*" in row.event_types) and _RANK.get(severity.lower(), 0) >= _RANK.get(row.minimum_severity, 3)]
        from app.storage.models import DeliveryJobRecord
        event_id = str(uuid4())
        async with db.sessions() as session:
            for row in eligible:
                session.add(DeliveryJobRecord(tenant_id=tenant_id,kind='webhook',target_id=row.id,
                    dedupe_key=event_id+':'+row.id,payload=copilot_store.redact({'id':event_id,'event_type':event_type,
                    'severity':severity,'occurred_at':datetime.now(UTC).isoformat(),'payload':payload})))
            await session.commit()
        return len(eligible)

    async def deliver(self, row, event):
        # Resolve/pin on every attempt; redirects are never followed for signed POSTs.
        secret = copilot_store.cipher().decrypt(row.encrypted_secret.encode())
        body = json.dumps({**event,'tenant_id':row.tenant_id},separators=(',',':'),ensure_ascii=True).encode()
        signature = hmac.new(secret,body,hashlib.sha256).hexdigest()
        response = await public_request('POST',validate_webhook_url(row.url),content=body,
            max_bytes=get_settings().webhook_max_response_bytes,timeout=5,
            headers={'Content-Type':'application/json','X-DarkTrace-Event':event['event_type'],
                     'X-DarkTrace-Signature':'sha256='+signature,'X-DarkTrace-Delivery':event['id']})
        response.raise_for_status()



webhook_service = WebhookService()
