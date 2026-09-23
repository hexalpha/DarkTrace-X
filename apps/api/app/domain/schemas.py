from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, SecretStr


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IndicatorType(StrEnum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH = "hash"
    EMAIL = "email"
    FILE = "file"


class IOCCreate(BaseModel):
    type: IndicatorType
    value: str = Field(min_length=1, max_length=4096)
    confidence: int = Field(default=50, ge=0, le=100)
    risk_score: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list, max_length=20)
    source: str = Field(default="manual", max_length=120)


class IOC(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: IndicatorType
    value: str
    confidence: int
    risk_score: int
    tags: list[str]
    source: str
    first_seen: datetime
    last_seen: datetime


class Alert(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    severity: Severity
    score: int = Field(ge=0, le=100)
    status: str
    created_at: datetime
    mitre_techniques: list[str] = Field(default_factory=list)
    evidence_count: int = 0


class DashboardOverview(BaseModel):
    protected_assets: int
    active_alerts: int
    critical_alerts: int
    iocs_tracked: int
    risk_score: int
    enrichment_coverage: float
    event_rate: int
    attack_timeline: list[dict[str, Any]]
    regions: list[dict[str, Any]]


class CVEIntel(BaseModel):
    cve_id: str
    title: str
    cvss: float | None = Field(default=None, ge=0, le=10)
    epss: float | None = Field(default=None, ge=0, le=1)
    exploited: bool
    published_at: datetime
    affected_products: list[str]
    mitigation: str


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    conversation_id: UUID | None = None
    provider: str | None = Field(default=None, max_length=40)
    model: str | None = Field(default=None, max_length=120)
    source_refs: list[str] = Field(default_factory=list, max_length=50)
    language: str = Field(default="en", pattern="^(en|hi)$")


class AIChatResponse(BaseModel):
    conversation_id: UUID
    message: str
    provider: str
    model: str
    used_fallback: bool
    source_refs: list[str]
    generated_at: datetime


class WebhookSubscription(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    url: HttpUrl
    event_types: list[str] = Field(min_length=1, max_length=20)
    minimum_severity: Severity = Severity.HIGH
    secret: SecretStr = Field(min_length=32, description="Shared signing secret; stored encrypted and never returned")


class ReportRequest(BaseModel):
    title: str = Field(default="DarkTrace X Intelligence Brief", min_length=3, max_length=150)
    include_iocs: bool = True
    include_alerts: bool = True
    include_cves: bool = True


class ReportSchedule(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    cron: str = Field(min_length=9, max_length=100)
    format: str = Field(pattern="^(pdf|docx|xlsx)$")
    recipients: list[str] = Field(min_length=1, max_length=100)


class YaraRule(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=3, max_length=120)
    namespace: str = Field(default="tenant")
    rule: str = Field(min_length=20, max_length=100_000)
    enabled: bool = True
    updated_at: datetime


class ExposureMention(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    monitored_term: str
    source_type: str
    confidence: int = Field(ge=0, le=100)
    summary: str
    observed_at: datetime
    legal_basis: str


class ObservableLookup(BaseModel):
    value: str = Field(min_length=1, max_length=4096)
    context_tags: list[str] = Field(default_factory=list, max_length=20)


class ReputationResult(BaseModel):
    observable: str
    type: IndicatorType
    verdict: str
    risk_score: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    tags: list[str]
    sources: list[str]
    mitre_techniques: list[str]
    explanation: str
    analyzed_at: datetime


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    query: str = Field(min_length=3, max_length=2_000)
    minimum_severity: Severity = Severity.HIGH
    destinations: list[str] = Field(default_factory=list, max_length=10)


class AlertRule(AlertRuleCreate):
    id: UUID = Field(default_factory=uuid4)
    enabled: bool = True
    created_at: datetime


class HuntRequest(BaseModel):
    hypothesis: str = Field(min_length=8, max_length=1_000)
    query: str = Field(min_length=3, max_length=2_000)
    time_range_hours: int = Field(default=24, ge=1, le=720)


class HuntResult(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: str
    hypothesis: str
    findings: int
    matching_indicators: list[IOC]
    recommended_next_step: str
    created_at: datetime


class AssetRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    hostname: str
    owner: str
    exposure: str
    criticality: str
    risk_score: int = Field(ge=0, le=100)
    services: list[str]
    last_seen: datetime


class ThreatActorProfile(BaseModel):
    id: str
    name: str
    motivation: str
    confidence: int = Field(ge=0, le=100)
    aliases: list[str]
    techniques: list[str]
    targeting: list[str]
    summary: str
    updated_at: datetime


class AuditEventView(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    actor: str
    action: str
    resource_type: str
    outcome: str
    occurred_at: datetime


class LocalModelScan(BaseModel):
    provider: str
    endpoint: str
    reachable: bool
    models: list[str]
    detail: str


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=256)
    tenant_id: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=256)
    tenant_id: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class KeywordMonitorCreate(BaseModel):
    term: str = Field(min_length=2, max_length=256)
    categories: list[str] = Field(default_factory=list, max_length=12)


class KeywordMonitor(KeywordMonitorCreate):
    id: str
    enabled: bool
    created_at: datetime


class FeedIngestResult(BaseModel):
    source: str
    received: int
    inserted: int
    matched_monitors: int
    created_alerts: int
    completed_at: datetime


class FeedItem(BaseModel):
    id: str
    source: str
    external_id: str
    title: str
    summary: str
    severity: Severity
    published_at: datetime


class SourceType(StrEnum):
    PUBLIC_THREAT_INTEL = "public_threat_intel"
    SECURITY_BLOG = "security_blog"
    VENDOR_ADVISORY = "vendor_advisory"
    CERT_FEED = "cert_feed"
    OSINT_FEED = "osint_feed"
    RSS = "rss"
    LICENSED_MONITORING = "licensed_monitoring"
    CUSTOM = "custom"


class CrawlPolicy(StrEnum):
    MANUAL = "manual"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    url: HttpUrl
    source_type: SourceType
    category: str = Field(min_length=2, max_length=64)
    description: str = Field(default="", max_length=2_000)
    crawl_policy: CrawlPolicy = CrawlPolicy.MANUAL
    frequency_minutes: int = Field(default=0, ge=0, le=10080)
    priority: int = Field(default=50, ge=0, le=100)
    trust_level: str = Field(default="medium", pattern="^(low|medium|high)$")
    parser_type: str = Field(default="html", pattern="^(html|rss|atom|json|text)$")
    tags: list[str] = Field(default_factory=list, max_length=20)


class SourceUpdate(SourceCreate):
    pass


class SourceView(SourceCreate):
    id: str
    tenant_id: str
    canonical_url: str
    enabled: bool
    health: str
    robots_status: str
    last_checked_at: datetime | None = None
    last_crawled_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failed_at: datetime | None = None
    next_scheduled_at: datetime | None = None
    failure_count: int
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class SourceValidation(BaseModel):
    valid: bool
    canonical_url: str
    health: str
    response_status: int | None = None
    content_type: str | None = None
    latency_ms: int | None = None
    reason: str | None = None


class CrawlJobView(BaseModel):
    retry_count: int = 0
    duration_ms: int | None = None
    error_type: str | None = None
    id: str
    tenant_id: str
    source_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    pages_requested: int
    pages_successful: int
    pages_failed: int
    bytes_downloaded: int
    records_extracted: int
    duplicates_found: int
    error: str | None = None


class SourceDocumentView(BaseModel):
    id: str
    source_id: str
    crawl_id: str
    source_url: str
    canonical_url: str
    title: str
    content_hash: str
    collected_at: datetime
    status: str
    tags: list[str]
    normalized_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityView(BaseModel):
    id: str
    entity_type: str
    value: str
    confidence: int
    extraction_method: str
    first_seen: datetime
    last_seen: datetime
    status: str


class ThreatEventView(BaseModel):
    id: str
    event_type: str
    source_id: str
    document_id: str
    entity_id: str | None
    severity: Severity
    confidence: int
    reason: str
    evidence: dict[str, Any]
    status: str
    created_at: datetime


class OperationalAlert(BaseModel):
    id: str
    title: str
    severity: Severity
    score: int = Field(ge=0, le=100)
    status: str
    evidence: dict[str, Any]
    created_at: datetime


class IndexedIOCCreate(BaseModel):
    indicator_type: IndicatorType
    value: str = Field(min_length=1, max_length=4096)
    confidence: int = Field(default=50, ge=0, le=100)
    risk_score: int = Field(default=50, ge=0, le=100)
    tags: list[str] = Field(default_factory=list, max_length=20)
    source: str = Field(min_length=2, max_length=120)
    evidence: dict[str, str] = Field(default_factory=dict, max_length=20)


class IndexedIOC(BaseModel):
    id: str
    tenant_id: str
    indicator_type: IndicatorType
    value: str
    confidence: int
    risk_score: int
    tags: list[str]
    source: str
    evidence: dict[str, str]
    observed_at: datetime


class CorrelationResult(BaseModel):
    observable: str
    indicator_type: IndicatorType
    matches: list[IndexedIOC]
    correlation_count: int


class GraphResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    generated_at: datetime


class ActorProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    techniques: list[str] = Field(default_factory=list, max_length=100)
    targeting: list[str] = Field(default_factory=list, max_length=40)
    summary: str = Field(min_length=10, max_length=8_000)
    sources: list[str] = Field(min_length=1, max_length=20)


class ActorProfile(ActorProfileCreate):
    id: str
    tenant_id: str
    updated_at: datetime


class Tenant(BaseModel):
    id: str
    name: str
    active: bool
    created_at: datetime


class TenantSummary(Tenant):
    user_count: int


class UserView(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    active: bool
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: str = Field(pattern="^(viewer|analyst|lead|admin)$")


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=256)
    role: str = Field(default="viewer", pattern="^(viewer|analyst|lead|admin)$")


class AuditEvent(BaseModel):
    id: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    metadata: dict[str, Any]
    occurred_at: datetime


class ConversationMessage(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    provider: str | None = None
    model: str | None = None
    created_at: datetime


class AutomationCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    trigger: str = Field(default="manual", pattern=r"^(manual|alert\.created|ioc\.created|schedule)$")
    provider: str = Field(default="local", pattern=r"^(local|external)$")
    model: str | None = Field(default=None, max_length=120)
    instruction: str = Field(min_length=12, max_length=4_000)


class Automation(AutomationCreate):
    id: UUID = Field(default_factory=uuid4)
    enabled: bool = True
    created_at: datetime
    last_run_at: datetime | None = None


class AutomationRunRequest(BaseModel):
    context: dict[str, str] = Field(default_factory=dict)


class AutomationRunResponse(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    automation_id: UUID
    status: str
    output: str
    provider: str
    model: str
    used_fallback: bool
    generated_at: datetime
