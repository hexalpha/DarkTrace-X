from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


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
    cvss: float = Field(ge=0, le=10)
    epss: float = Field(ge=0, le=1)
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
