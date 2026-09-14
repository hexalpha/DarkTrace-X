from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.domain.schemas import Alert, CVEIntel, DashboardOverview, IOC, IOCCreate, IndicatorType, Severity


NOW = datetime.now(UTC)


class IntelligenceService:
    """Repository seam. Replace the demo collection with tenant-scoped SQLAlchemy repositories."""

    def __init__(self) -> None:
        self._iocs: list[IOC] = [
            IOC(type=IndicatorType.DOMAIN, value="cdn-sync-check.example", confidence=92, risk_score=94, tags=["c2", "phishing"], source="approved-feed", first_seen=NOW - timedelta(days=2), last_seen=NOW - timedelta(minutes=4)),
            IOC(type=IndicatorType.IP, value="198.51.100.42", confidence=77, risk_score=81, tags=["scanner", "brute-force"], source="edr-correlation", first_seen=NOW - timedelta(days=1), last_seen=NOW - timedelta(minutes=11)),
            IOC(type=IndicatorType.HASH, value="7c4a8d09ca3762af61e59520943dc26494f8941b", confidence=68, risk_score=73, tags=["loader"], source="sandbox", first_seen=NOW - timedelta(days=4), last_seen=NOW - timedelta(hours=2)),
        ]
        self._alerts = [
            Alert(title="Potential credential exposure linked to approved breach feed", severity=Severity.CRITICAL, score=96, status="investigating", created_at=NOW - timedelta(minutes=9), mitre_techniques=["T1589", "T1078"], evidence_count=12),
            Alert(title="Suspicious outbound beacon pattern", severity=Severity.HIGH, score=84, status="open", created_at=NOW - timedelta(minutes=27), mitre_techniques=["T1071.001"], evidence_count=7),
            Alert(title="New exploit intelligence for internet-facing asset", severity=Severity.HIGH, score=78, status="triage", created_at=NOW - timedelta(hours=1), mitre_techniques=["T1190"], evidence_count=5),
            Alert(title="Phishing infrastructure overlap detected", severity=Severity.MEDIUM, score=64, status="open", created_at=NOW - timedelta(hours=2), mitre_techniques=["T1566"], evidence_count=3),
        ]

    def overview(self, tenant_id: str) -> DashboardOverview:
        return DashboardOverview(
            protected_assets=1284,
            active_alerts=len(self._alerts),
            critical_alerts=sum(alert.severity == Severity.CRITICAL for alert in self._alerts),
            iocs_tracked=24_891,
            risk_score=71,
            enrichment_coverage=94.8,
            event_rate=1824,
            attack_timeline=[
                {"hour": "00:00", "events": 480, "risk": 22}, {"hour": "04:00", "events": 612, "risk": 36},
                {"hour": "08:00", "events": 1048, "risk": 58}, {"hour": "12:00", "events": 1743, "risk": 71},
                {"hour": "16:00", "events": 1384, "risk": 63}, {"hour": "20:00", "events": 1824, "risk": 71},
            ],
            regions=[
                {"name": "North America", "events": 643, "risk": "high"},
                {"name": "Europe", "events": 498, "risk": "medium"},
                {"name": "Asia Pacific", "events": 511, "risk": "critical"},
                {"name": "Other", "events": 172, "risk": "low"},
            ],
        )

    def list_iocs(self, tenant_id: str, query: str | None = None) -> list[IOC]:
        if not query:
            return self._iocs
        needle = query.casefold()
        return [ioc for ioc in self._iocs if needle in ioc.value.casefold() or any(needle in tag.casefold() for tag in ioc.tags)]

    def create_ioc(self, tenant_id: str, payload: IOCCreate) -> IOC:
        now = datetime.now(UTC)
        ioc = IOC(
            type=payload.type,
            value=payload.value.strip(),
            confidence=payload.confidence,
            risk_score=min(100, round(payload.confidence * 0.86)),
            tags=sorted(set(tag.strip().lower() for tag in payload.tags if tag.strip())),
            source=payload.source,
            first_seen=now,
            last_seen=now,
        )
        self._iocs.insert(0, ioc)
        return ioc

    def list_alerts(self, tenant_id: str, severity: Severity | None = None) -> list[Alert]:
        return [alert for alert in self._alerts if severity is None or alert.severity == severity]

    def cves(self) -> list[CVEIntel]:
        return [
            CVEIntel(cve_id="CVE-2026-24817", title="Internet-facing component authentication bypass", cvss=9.1, epss=0.82, exploited=True, published_at=NOW - timedelta(days=1), affected_products=["Edge gateway", "Identity proxy"], mitigation="Apply the vendor fix, restrict management paths, and hunt for anomalous session creation."),
            CVEIntel(cve_id="CVE-2026-19204", title="Server-side request forgery in workflow integration", cvss=8.2, epss=0.41, exploited=False, published_at=NOW - timedelta(days=4), affected_products=["Automation server"], mitigation="Upgrade to the fixed release and restrict outbound network access from workers."),
            CVEIntel(cve_id="CVE-2026-11402", title="Privilege escalation via local service", cvss=7.8, epss=0.18, exploited=False, published_at=NOW - timedelta(days=8), affected_products=["Endpoint agent"], mitigation="Deploy the patch through the staged endpoint ring and validate service permissions."),
        ]


intelligence_service = IntelligenceService()

