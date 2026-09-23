import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, Role
from app.domain.schemas import AuditEvent, ConversationMessage, DashboardOverview, FeedIngestResult, FeedItem, KeywordMonitor, KeywordMonitorCreate, LoginRequest, OperationalAlert, RegisterRequest, Tenant, TenantSummary, UserCreate, UserRoleUpdate, UserView
from app.storage.database import Database
from app.services.geography import reported_regions
from app.storage.models import AuditEventRecord, ConversationMessageRecord, KeywordMonitorRecord, OperationalAlertRecord, TenantRecord, ThreatFeedItemRecord, UserRecord, TelemetryRecord, IntelligenceRecord

CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, cost, salt_text, digest_text = stored.split("$", 3)
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt_text), n=int(cost), r=8, p=1, dklen=32)
        return hmac.compare_digest(digest, base64.b64decode(digest_text))
    except (ValueError, TypeError):
        return False


class OperationalService:
    """Persistent, tenant-scoped monitoring and feed correlation service."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def _session(self) -> AsyncSession:
        if not self.database.ready or self.database.sessions is None:
            raise RuntimeError("PostgreSQL is not ready")
        return self.database.sessions()

    async def register(self, payload: RegisterRequest) -> Principal:
        email = payload.email.strip().casefold()
        async with self._session() as session:
            tenant = await session.get(TenantRecord, payload.tenant_id)
            if tenant is not None:
                raise ValueError("Tenant already exists. Ask a tenant administrator to create your account.")
            session.add(TenantRecord(id=payload.tenant_id, name=payload.tenant_id))
            existing = await session.scalar(select(UserRecord).where(UserRecord.tenant_id == payload.tenant_id, UserRecord.email == email))
            if existing:
                raise ValueError("An account already exists for this tenant and email")
            user = UserRecord(tenant_id=payload.tenant_id, email=email, display_name=payload.display_name.strip(), password_hash=_password_hash(payload.password), role=Role.ADMIN.value)
            session.add(user)
            await session.commit()
            return Principal(user_id=user.id, tenant_id=user.tenant_id, role=Role(user.role), email=user.email)

    async def create_user(self, principal: Principal, payload: UserCreate) -> UserView:
        email = payload.email.strip().casefold()
        async with self._session() as session:
            existing = await session.scalar(select(UserRecord).where(UserRecord.tenant_id == principal.tenant_id, UserRecord.email == email))
            if existing:
                raise ValueError("An account already exists for this tenant and email")
            user = UserRecord(tenant_id=principal.tenant_id, email=email, display_name=payload.display_name.strip(), password_hash=_password_hash(payload.password), role=payload.role)
            session.add(user)
            await session.flush()
            session.add(AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="user.created", resource_type="user", resource_id=user.id, outcome="success", metadata_json={"role": payload.role}))
            await session.commit()
            return UserView(id=user.id, email=user.email, display_name=user.display_name, role=user.role, active=user.active, created_at=user.created_at)

    async def tenant_summary(self, principal: Principal) -> TenantSummary:
        async with self._session() as session:
            tenant = await session.get(TenantRecord, principal.tenant_id)
            if tenant is None:
                raise ValueError("Tenant not found")
            count = int((await session.scalar(select(func.count()).select_from(UserRecord).where(UserRecord.tenant_id == principal.tenant_id))) or 0)
            return TenantSummary(id=tenant.id, name=tenant.name, active=tenant.active, created_at=tenant.created_at, user_count=count)

    async def users(self, principal: Principal) -> list[UserView]:
        async with self._session() as session:
            records = (await session.scalars(select(UserRecord).where(UserRecord.tenant_id == principal.tenant_id).order_by(UserRecord.created_at))).all()
            return [UserView(id=item.id, email=item.email, display_name=item.display_name, role=item.role, active=item.active, created_at=item.created_at) for item in records]

    async def update_user_role(self, principal: Principal, user_id: str, payload: UserRoleUpdate) -> UserView:
        async with self._session() as session:
            await session.scalar(select(TenantRecord).where(TenantRecord.id == principal.tenant_id).with_for_update())
            user = await session.scalar(select(UserRecord).where(UserRecord.id == user_id, UserRecord.tenant_id == principal.tenant_id))
            if user is None:
                raise ValueError("User not found")
            if user.role == Role.ADMIN.value and payload.role != Role.ADMIN.value:
                admin_count = int((await session.scalar(select(func.count()).select_from(UserRecord).where(UserRecord.tenant_id == principal.tenant_id, UserRecord.role == Role.ADMIN.value, UserRecord.active.is_(True)))) or 0)
                if admin_count <= 1:
                    raise ValueError("The final active tenant administrator cannot be demoted")
            user.role = payload.role
            session.add(AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="user.role_updated", resource_type="user", resource_id=user.id, outcome="success", metadata_json={"role": payload.role}))
            await session.commit()
            return UserView(id=user.id, email=user.email, display_name=user.display_name, role=user.role, active=user.active, created_at=user.created_at)

    async def audit_events(self, principal: Principal, limit: int = 100) -> list[AuditEvent]:
        async with self._session() as session:
            records = (await session.scalars(select(AuditEventRecord).where(AuditEventRecord.tenant_id == principal.tenant_id).order_by(desc(AuditEventRecord.occurred_at)).limit(limit))).all()
            return [AuditEvent(id=item.id, actor_id=item.actor_id, action=item.action, resource_type=item.resource_type, resource_id=item.resource_id, outcome=item.outcome, metadata=item.metadata_json, occurred_at=item.occurred_at) for item in records]

    async def conversation_history(self, principal: Principal, conversation_id: str) -> list[ConversationMessage]:
        async with self._session() as session:
            records = (await session.scalars(select(ConversationMessageRecord).where(ConversationMessageRecord.tenant_id == principal.tenant_id, ConversationMessageRecord.user_id == principal.user_id, ConversationMessageRecord.conversation_id == conversation_id).order_by(ConversationMessageRecord.created_at.desc()).limit(40))).all()
            return [ConversationMessage(id=item.id, conversation_id=item.conversation_id, role=item.role, content=item.content, provider=item.provider, model=item.model, created_at=item.created_at) for item in reversed(records)]

    async def append_conversation(self, principal: Principal, conversation_id: str, role: str, content: str, provider: str | None = None, model: str | None = None) -> ConversationMessage:
        async with self._session() as session:
            record = ConversationMessageRecord(tenant_id=principal.tenant_id, user_id=principal.user_id, conversation_id=conversation_id, role=role, content=content, provider=provider, model=model)
            session.add(record)
            await session.commit()
            return ConversationMessage(id=record.id, conversation_id=record.conversation_id, role=record.role, content=record.content, provider=record.provider, model=record.model, created_at=record.created_at)

    async def authenticate(self, payload: LoginRequest) -> Principal | None:
        async with self._session() as session:
            user = await session.scalar(select(UserRecord).where(UserRecord.tenant_id == payload.tenant_id, UserRecord.email == payload.email.strip().casefold()))
            if not user or not user.active or not _verify_password(payload.password, user.password_hash):
                return None
            return Principal(user_id=user.id, tenant_id=user.tenant_id, role=Role(user.role), email=user.email)

    async def create_monitor(self, principal: Principal, payload: KeywordMonitorCreate) -> KeywordMonitor:
        term = payload.term.strip()
        async with self._session() as session:
            exists = await session.scalar(select(KeywordMonitorRecord).where(KeywordMonitorRecord.tenant_id == principal.tenant_id, KeywordMonitorRecord.term == term))
            if exists:
                raise ValueError("This keyword is already being monitored")
            record = KeywordMonitorRecord(tenant_id=principal.tenant_id, term=term, categories=sorted({item.strip().casefold() for item in payload.categories if item.strip()}), created_by=principal.user_id)
            session.add(record)
            await session.commit()
            return KeywordMonitor(id=record.id, term=record.term, categories=record.categories, enabled=record.enabled, created_at=record.created_at)

    async def list_monitors(self, principal: Principal) -> list[KeywordMonitor]:
        async with self._session() as session:
            records = (await session.scalars(select(KeywordMonitorRecord).where(KeywordMonitorRecord.tenant_id == principal.tenant_id).order_by(desc(KeywordMonitorRecord.created_at)))).all()
            return [KeywordMonitor(id=item.id, term=item.term, categories=item.categories, enabled=item.enabled, created_at=item.created_at) for item in records]

    async def list_alerts(self, principal: Principal) -> list[OperationalAlert]:
        async with self._session() as session:
            records = (await session.scalars(select(OperationalAlertRecord).where(OperationalAlertRecord.tenant_id == principal.tenant_id).order_by(desc(OperationalAlertRecord.created_at)).limit(500))).all()
            return [OperationalAlert(id=item.id, title=item.title, severity=item.severity, score=item.score, status=item.status, evidence=item.evidence, created_at=item.created_at) for item in records]

    async def overview(self, principal: Principal) -> DashboardOverview:
        now = datetime.now(UTC)
        async with self._session() as session:
            scope = [OperationalAlertRecord.tenant_id == principal.tenant_id, OperationalAlertRecord.status.not_in(["resolved", "false_positive"])]
            count = int(await session.scalar(select(func.count()).select_from(OperationalAlertRecord).where(*scope)) or 0)
            critical = int(await session.scalar(select(func.count()).select_from(OperationalAlertRecord).where(*scope, OperationalAlertRecord.severity == "critical")) or 0)
            risk = int(await session.scalar(select(func.max(OperationalAlertRecord.score)).where(*scope)) or 0)
            assets = int(await session.scalar(select(func.count()).select_from(IntelligenceRecord).where(IntelligenceRecord.tenant_id == principal.tenant_id, IntelligenceRecord.collection == "assets")) or 0)
            iocs = int(await session.scalar(select(func.count()).select_from(IntelligenceRecord).where(IntelligenceRecord.tenant_id == principal.tenant_id, IntelligenceRecord.collection == "iocs")) or 0)
            times = (await session.scalars(select(TelemetryRecord.observed_at).where(TelemetryRecord.tenant_id == principal.tenant_id, TelemetryRecord.observed_at >= now - timedelta(hours=24), TelemetryRecord.observed_at <= now))).all()
            located = (await session.scalars(select(TelemetryRecord.payload).where(
                TelemetryRecord.tenant_id == principal.tenant_id,
                TelemetryRecord.observed_at >= now - timedelta(hours=24),
                TelemetryRecord.observed_at <= now,
                TelemetryRecord.payload["location"]["latitude"].as_float().is_not(None),
            ).order_by(TelemetryRecord.observed_at.desc(), TelemetryRecord.id).limit(10000))).all()
        buckets = { (now - timedelta(hours=i)).strftime("%Y-%m-%d %H:00"): 0 for i in reversed(range(24)) }
        for timestamp in times:
            key = timestamp.strftime("%Y-%m-%d %H:00")
            if key in buckets:
                buckets[key] += 1
        rate = sum(t.replace(tzinfo=UTC) >= now - timedelta(minutes=1) for t in times)
        return DashboardOverview(protected_assets=assets, active_alerts=count, critical_alerts=critical, iocs_tracked=iocs, risk_score=risk, enrichment_coverage=0, event_rate=rate, attack_timeline=[{"hour": key[-5:], "events": value} for key, value in buckets.items()], regions=reported_regions(located))

    async def list_feed_items(self, principal: Principal, limit: int = 50) -> list[FeedItem]:
        async with self._session() as session:
            records = (await session.scalars(select(ThreatFeedItemRecord).order_by(desc(ThreatFeedItemRecord.published_at)).limit(limit))).all()
            return [FeedItem(id=item.id, source=item.source, external_id=item.external_id, title=item.title, summary=item.summary, severity=item.severity, published_at=item.published_at) for item in records]

    async def ingest_cisa_kev(self, principal: Principal) -> FeedIngestResult:
        """Ingest the CISA KEV catalog only; no arbitrary URLs and no illicit-source collection."""
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.get(CISA_KEV_URL, headers={"Accept": "application/json", "User-Agent": "DarkTraceX/1.0 defensive-feed-client"})
            response.raise_for_status()
            payload = response.json()
        vulnerabilities = payload.get("vulnerabilities", [])
        if not isinstance(vulnerabilities, list):
            raise ValueError("CISA KEV response did not contain a vulnerability list")
        now = datetime.now(UTC)
        inserted = 0
        matched = 0
        alerts_created = 0
        created_events = []
        async with self._session() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT pg_advisory_xact_lock(73421901)"))
            monitors = (await session.scalars(select(KeywordMonitorRecord).where(KeywordMonitorRecord.tenant_id == principal.tenant_id, KeywordMonitorRecord.enabled.is_(True)))).all()
            for entry in vulnerabilities:
                if not isinstance(entry, dict) or not entry.get("cveID"):
                    continue
                external_id = str(entry["cveID"])
                title = " ".join(str(entry.get(key, "")).strip() for key in ("vendorProject", "product", "vulnerabilityName") if entry.get(key))[:512]
                summary = str(entry.get("shortDescription") or entry.get("requiredAction") or "CISA KEV catalog entry")[:5000]
                date_text = str(entry.get("dateAdded", ""))
                try:
                    published = datetime.fromisoformat(date_text).replace(tzinfo=UTC)
                except ValueError:
                    published = now
                record = await session.scalar(select(ThreatFeedItemRecord).where(ThreatFeedItemRecord.source == "cisa-kev", ThreatFeedItemRecord.external_id == external_id))
                if not record:
                    record = ThreatFeedItemRecord(source="cisa-kev", external_id=external_id, title=title or external_id, summary=summary, severity="high", published_at=published, raw=entry)
                    session.add(record)
                    inserted += 1
                haystack = f"{title}\n{summary}".casefold()
                for monitor in monitors:
                    if monitor.term.casefold() not in haystack:
                        continue
                    matched += 1
                    dedupe_key = f"cisa-kev:{external_id}:monitor:{monitor.id}"
                    existing_alert = await session.scalar(select(OperationalAlertRecord).where(OperationalAlertRecord.tenant_id == principal.tenant_id, OperationalAlertRecord.dedupe_key == dedupe_key))
                    if not existing_alert:
                        evidence = {"source": "cisa-kev", "cve": external_id, "monitor": monitor.term, "title": title}
                        session.add(OperationalAlertRecord(tenant_id=principal.tenant_id, dedupe_key=dedupe_key, title=f"Monitored keyword '{monitor.term}' matched {external_id}", severity="high", score=82, evidence=evidence))
                        created_events.append({"title": f"Monitored keyword '{monitor.term}' matched {external_id}", "severity": "high", "score": 82, "evidence": evidence})
                        alerts_created += 1
            await session.commit()
        from app.services.webhooks import webhook_service
        for event in created_events:
            await webhook_service.dispatch(principal.tenant_id, "alert.created", event["severity"], event)
        return FeedIngestResult(source="cisa-kev", received=len(vulnerabilities), inserted=inserted, matched_monitors=matched, created_alerts=alerts_created, completed_at=now)
