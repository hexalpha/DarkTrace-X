import hashlib
import ipaddress
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, or_, func, cast, String
from sqlalchemy.dialects.postgresql import insert
from app.domain.schemas import Alert, AlertRule, AssetRecord, AuditEventView, CVEIntel, HuntResult, IOC, IndicatorType, ReputationResult
from app.storage import database as database_module
from app.storage.models import IntelligenceRecord, OperationalAlertRecord, ThreatFeedItemRecord, AuditEventRecord


def session():
    db = database_module.database
    if not db or not db.ready or not db.sessions:
        raise HTTPException(503, 'PostgreSQL is unavailable')
    return db.sessions()


class IntelligenceService:
    """Persistent tenant repositories. No generated reputation or sample records."""
    async def documents(self, tenant_id, collection, limit=500):
        async with session() as db:
            rows = (await db.scalars(select(IntelligenceRecord).where(IntelligenceRecord.tenant_id == tenant_id, IntelligenceRecord.collection == collection).order_by(IntelligenceRecord.updated_at.desc()).limit(limit))).all()
            return [row.payload for row in rows]

    async def save(self, tenant_id, collection, payload, ident=None):
        data = dict(payload)
        data['id'] = ident or data.get('id') or str(uuid4())
        async with session() as db:
            await db.execute(insert(IntelligenceRecord).values(tenant_id=tenant_id, collection=collection, id=str(data['id']), payload=data).on_conflict_do_update(index_elements=['tenant_id', 'collection', 'id'], set_={'payload': data, 'updated_at': datetime.now(UTC)}))
            await db.commit()
        return data

    async def list_iocs(self, tenant_id, query=None):
        async with session() as db:
            statement = select(IntelligenceRecord).where(IntelligenceRecord.tenant_id == tenant_id, IntelligenceRecord.collection == 'iocs')
            if query:
                needle = query.casefold()
                statement = statement.where(or_(func.lower(IntelligenceRecord.payload['value'].as_string()).contains(needle, autoescape=True), func.lower(cast(IntelligenceRecord.payload['tags'], String)).contains(needle, autoescape=True)))
            rows = (await db.scalars(statement.order_by(IntelligenceRecord.updated_at.desc()).limit(500))).all()
        return [IOC(**row.payload) for row in rows]

    async def create_ioc(self, tenant_id, payload):
        now = datetime.now(UTC)
        value = self._validate_observable(payload.type, payload.value)
        ioc = IOC(type=payload.type, value=value, confidence=payload.confidence, risk_score=payload.risk_score, tags=sorted(set(payload.tags)), source=payload.source, first_seen=now, last_seen=now)
        # Stable UUID preserves compatibility with the public IOC contract.
        from uuid import UUID
        ioc.id = UUID(hashlib.sha256(f'{tenant_id}:{payload.type}:{value}'.encode()).hexdigest()[:32])
        async with session() as db:
            old = await db.get(IntelligenceRecord, (tenant_id, 'iocs', str(ioc.id)))
            if old:
                ioc.first_seen = datetime.fromisoformat(old.payload['first_seen'])
        await self.save(tenant_id, 'iocs', ioc.model_dump(mode='json'))
        return ioc

    async def list_alerts(self, tenant_id, severity=None):
        async with session() as db:
            query = select(OperationalAlertRecord).where(OperationalAlertRecord.tenant_id == tenant_id)
            if severity:
                query = query.where(OperationalAlertRecord.severity == severity)
            rows = (await db.scalars(query.order_by(OperationalAlertRecord.created_at.desc()).limit(500))).all()
        return [Alert(id=r.id, title=r.title, severity=r.severity, score=r.score, status=r.status, created_at=r.created_at, evidence_count=len(r.evidence), mitre_techniques=r.evidence.get('mitre_techniques', [])) for r in rows]

    async def cves(self):
        async with session() as db:
            rows = (await db.scalars(select(ThreatFeedItemRecord).where(ThreatFeedItemRecord.source == 'cisa-kev').order_by(ThreatFeedItemRecord.published_at.desc()).limit(200))).all()
        return [CVEIntel(cve_id=r.external_id, title=r.title, cvss=None, epss=None, exploited=True, published_at=r.published_at, affected_products=[str(r.raw.get('product', ''))], mitigation=str(r.raw.get('requiredAction', 'Consult the vendor advisory.'))) for r in rows]

    async def reputation(self, tenant_id, indicator_type, payload):
        value = self._validate_observable(indicator_type, payload.value)
        existing = next((i for i in await self.list_iocs(tenant_id, value) if i.type == indicator_type and i.value == value), None)
        return ReputationResult(observable=value, type=indicator_type, verdict=('malicious' if existing.risk_score >= 75 else 'suspicious') if existing else 'unknown', risk_score=existing.risk_score if existing else 0, confidence=existing.confidence if existing else 0, tags=existing.tags if existing else [], sources=[existing.source] if existing else [], mitre_techniques=[], explanation='Matched recorded tenant intelligence; score supplied by its source.' if existing else 'No recorded evidence. Unknown does not mean safe; no risk score was inferred.', analyzed_at=datetime.now(UTC))

    @staticmethod
    def _validate_observable(indicator_type, raw_value):
        value = raw_value.strip()
        if indicator_type == IndicatorType.IP:
            return str(ipaddress.ip_address(value))
        if indicator_type == IndicatorType.DOMAIN:
            value = value.rstrip('.').encode('idna').decode().lower()
            if not re.fullmatch(r'(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', value):
                raise ValueError('Invalid domain indicator')
            return value
        if indicator_type == IndicatorType.HASH:
            if len(value) not in (32, 40, 64) or not re.fullmatch('[a-fA-F0-9]+', value):
                raise ValueError('Hash must be MD5, SHA-1, or SHA-256 hexadecimal')
            return value.lower()
        if indicator_type == IndicatorType.URL:
            parsed = urlsplit(value)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('A valid HTTP(S) URL without credentials is required')
            return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, ''))
        if indicator_type == IndicatorType.EMAIL:
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
                raise ValueError('Invalid email indicator')
            return value.casefold()
        if not value:
            raise ValueError('Indicator cannot be blank')
        return value

    async def alert_rules(self, tenant_id):
        return [AlertRule(**p) for p in await self.documents(tenant_id, 'alert_rules')]

    async def create_alert_rule(self, tenant_id, payload):
        rule = AlertRule(**payload.model_dump(), created_at=datetime.now(UTC))
        await self.save(tenant_id, 'alert_rules', rule.model_dump(mode='json'))
        return rule

    async def hunt(self, tenant_id, payload):
        cutoff = datetime.now(UTC) - timedelta(hours=payload.time_range_hours)
        matches = [i for i in await self.list_iocs(tenant_id, payload.query) if i.last_seen >= cutoff]
        result = HuntResult(status='completed', hypothesis=payload.hypothesis, findings=len(matches), matching_indicators=matches, recommended_next_step='Validate matches against endpoint/network evidence.' if matches else 'No matching recorded indicators in this time range.', created_at=datetime.now(UTC))
        await self.save(tenant_id, 'hunts', result.model_dump(mode='json'))
        return result

    async def assets(self, tenant_id):
        return [AssetRecord(**p) for p in await self.documents(tenant_id, 'assets')]

    async def audit_events(self, tenant_id):
        async with session() as db:
            rows = (await db.scalars(select(AuditEventRecord).where(AuditEventRecord.tenant_id == tenant_id).order_by(AuditEventRecord.occurred_at.desc()).limit(100))).all()
        return [AuditEventView(id=r.id, actor=r.actor_id, action=r.action, resource_type=r.resource_type, outcome=r.outcome, occurred_at=r.occurred_at) for r in rows]


intelligence_service = IntelligenceService()
