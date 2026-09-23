"""Tenant-scoped, SSRF-safe source registry and single-page crawl pipeline."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import re
import socket
import time
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import httpx
from sqlalchemy import desc, select

from app.core.security import Principal, Role
from app.domain.schemas import CrawlJobView, EntityView, SourceCreate, SourceDocumentView, SourceUpdate, SourceValidation, SourceView, ThreatEventView
from app.storage.models import AuditEventRecord, CrawlJobRecord, EntityObservationRecord, IntelligenceEntityRecord, KeywordMonitorRecord, OperationalAlertRecord, SourceDocumentRecord, SourceRecord, ThreatEventRecord

from app.services.safe_http import public_request
from app.services.crawl_lock import source_lock
from app.core.config import get_settings

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "metadata.google.internal"}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: list[str] = []
        self.text: list[str] = []
        self.links: list[str] = []
        self._in_title = False
        self._ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript", "template"}:
            self._ignored += 1
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href[:2048])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "template"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value or self._ignored:
            return
        if self._in_title:
            self.title.append(value)
        self.text.append(value)


def canonicalize(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Only absolute HTTP(S) source URLs are allowed")
    if parts.username or parts.password:
        raise ValueError("Source URLs cannot contain credentials")
    host = parts.hostname.casefold()
    port = parts.port
    netloc = host if port in {None, 80 if parts.scheme == "http" else 443} else f"{host}:{port}"
    path = parts.path or "/"
    return urlunsplit((parts.scheme.casefold(), netloc, path, parts.query, ""))


async def public_host_check(url: str) -> None:
    parts = urlsplit(url)
    host = (parts.hostname or "").casefold()
    if host in BLOCKED_HOSTS:
        raise ValueError("Source host is not allowed")
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Source DNS resolution failed") from exc
    for address in {item[4][0] for item in addresses}:
        parsed = ipaddress.ip_address(address)
        if parsed.is_private or parsed.is_loopback or parsed.is_link_local or parsed.is_reserved or parsed.is_multicast or parsed.is_unspecified:
            raise ValueError("Source resolves to a private or reserved network")


def normalize_html(body: str, content_type: str) -> tuple[str, str, list[str]]:
    parser = TextExtractor()
    if "html" in content_type.casefold():
        parser.feed(body)
        title = " ".join(parser.title).strip()[:512] or "Untitled source document"
        text = " ".join(parser.text).strip()
        links = parser.links
    else:
        title = "Source document"
        text = " ".join(body.split())
        links = []
    return title, text[:MAX_RESPONSE_BYTES], links[:200]


def extract_entities(text: str) -> dict[str, list[str]]:
    patterns = {
        "ipv4": r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b",
        "domain": r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\b",
        "url": r"https?://[^\s<>\"']+",
        "email": r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b",
        "md5": r"\b[a-fA-F0-9]{32}\b",
        "sha1": r"\b[a-fA-F0-9]{40}\b",
        "sha256": r"\b[a-fA-F0-9]{64}\b",
        "cve": r"\bCVE-\d{4}-\d{4,7}\b",
    }
    return {kind: sorted(set(re.findall(pattern, text, re.IGNORECASE)))[:200] for kind, pattern in patterns.items()}


class SourceManagementService:
    def __init__(self, database) -> None:
        self.database = database

    def _session(self):
        if not self.database.ready or self.database.sessions is None:
            raise RuntimeError("PostgreSQL is not ready")
        return self.database.sessions()

    @staticmethod
    def _view(row: SourceRecord) -> SourceView:
        return SourceView.model_validate(row, from_attributes=True)

    @staticmethod
    def _job_view(row: CrawlJobRecord) -> CrawlJobView:
        return CrawlJobView.model_validate(row, from_attributes=True)

    async def list(self, principal: Principal, query: str | None = None, limit: int = 100, offset: int = 0) -> list[SourceView]:
        async with self._session() as db:
            statement = select(SourceRecord).where(SourceRecord.tenant_id == principal.tenant_id).order_by(desc(SourceRecord.updated_at)).offset(offset).limit(limit)
            if query:
                statement = statement.where(SourceRecord.name.ilike(f"%{query}%"))
            return [self._view(row) for row in (await db.scalars(statement)).all()]

    async def get(self, principal: Principal, source_id: str) -> SourceRecord:
        async with self._session() as db:
            row = await db.scalar(select(SourceRecord).where(SourceRecord.tenant_id == principal.tenant_id, SourceRecord.id == source_id))
            if not row:
                raise ValueError("Source not found")
            return row

    async def create(self, principal: Principal, payload: SourceCreate) -> SourceView:
        canonical = canonicalize(str(payload.url))
        await public_host_check(canonical)
        async with self._session() as db:
            existing = await db.scalar(select(SourceRecord).where(SourceRecord.tenant_id == principal.tenant_id, SourceRecord.canonical_url == canonical))
            if existing:
                raise ValueError("A source with this canonical URL already exists")
            row = SourceRecord(tenant_id=principal.tenant_id, id=str(uuid4()), canonical_url=canonical, url=str(payload.url), **payload.model_dump(exclude={"url"}))
            db.add(row)
            await db.flush()
            db.add(AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="source.created", resource_type="source", resource_id=row.id, outcome="success", metadata_json={"url": canonical}))
            await db.commit()
            return self._view(row)

    async def update(self, principal: Principal, source_id: str, payload: SourceUpdate) -> SourceView:
        canonical = canonicalize(str(payload.url))
        await public_host_check(canonical)
        async with self._session() as db:
            row = await db.scalar(select(SourceRecord).where(SourceRecord.tenant_id == principal.tenant_id, SourceRecord.id == source_id).with_for_update())
            if not row:
                raise ValueError("Source not found")
            conflict = await db.scalar(select(SourceRecord).where(SourceRecord.tenant_id == principal.tenant_id, SourceRecord.canonical_url == canonical, SourceRecord.id != source_id))
            if conflict:
                raise ValueError("A source with this canonical URL already exists")
            for key, value in payload.model_dump().items():
                setattr(row, "url" if key == "url" else key, str(value) if key == "url" else value)
            row.canonical_url = canonical
            db.add(AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="source.updated", resource_type="source", resource_id=row.id, outcome="success", metadata_json={"url": canonical}))
            await db.commit()
            return self._view(row)

    async def set_enabled(self, principal: Principal, source_id: str, enabled: bool) -> SourceView:
        async with self._session() as db:
            row = await db.scalar(select(SourceRecord).where(SourceRecord.tenant_id == principal.tenant_id, SourceRecord.id == source_id).with_for_update())
            if not row:
                raise ValueError("Source not found")
            row.enabled = enabled
            row.health = "UNTESTED" if enabled else "DISABLED"
            db.add(AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id, action=f"source.{('enabled' if enabled else 'disabled')}", resource_type="source", resource_id=row.id, outcome="success", metadata_json={}))
            await db.commit()
            return self._view(row)

    async def remove(self, principal: Principal, source_id: str) -> bool:
        async with self._session() as db:
            row = await db.scalar(select(SourceRecord).where(SourceRecord.tenant_id == principal.tenant_id, SourceRecord.id == source_id).with_for_update())
            if not row:
                return False
            row.enabled = False
            row.health = "DISABLED"
            db.add(AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="source.archived", resource_type="source", resource_id=row.id, outcome="success", metadata_json={}))
            await db.commit()
            return True

    async def validate(self, principal: Principal, source_id: str) -> SourceValidation:
        row = await self.get(principal, source_id)
        started = time.perf_counter()
        try:
            await public_host_check(row.canonical_url)
            response = await public_request('GET', row.canonical_url,
                max_bytes=get_settings().source_max_response_bytes,
                timeout=get_settings().outbound_timeout_seconds, redirects=3,
                headers={'User-Agent': 'DarkTraceX/1.0 defensive-source-validator'})
            if response.status_code >= 400:
                raise ValueError(f"Source returned HTTP {response.status_code}")
            content_type = response.headers.get("content-type", "")
            if row.parser_type in {"html", "rss", "atom"} and not any(value in content_type.casefold() for value in ("html", "xml", "rss", "text")):
                raise ValueError("Source content type is incompatible with the configured parser")
            health = "HEALTHY"
            reason = None
            status_code = response.status_code
        except (httpx.HTTPError, ValueError, TimeoutError) as exc:
            health = "DEGRADED"
            reason = str(exc)
            content_type = None
            status_code = None
        latency = int((time.perf_counter() - started) * 1000)
        async with self._session() as db:
            current = await db.scalar(select(SourceRecord).where(SourceRecord.tenant_id == principal.tenant_id, SourceRecord.id == source_id).with_for_update())
            if current:
                current.last_checked_at = datetime.now(UTC)
                current.health = health
                current.last_error = reason
                if health == "HEALTHY":
                    current.failure_count = 0
                await db.commit()
        return SourceValidation(valid=health == "HEALTHY", canonical_url=row.canonical_url, health=health, response_status=status_code, content_type=content_type, latency_ms=latency, reason=reason)

    async def crawl(self, principal: Principal, source_id: str) -> tuple[CrawlJobView, list[SourceDocumentView]]:
        async with source_lock(principal.tenant_id, source_id):
            async with asyncio.timeout(240):
                return await self._crawl(principal, source_id)

    async def _crawl(self, principal: Principal, source_id: str) -> tuple[CrawlJobView, list[SourceDocumentView]]:
        row = await self.get(principal, source_id)
        if not row.enabled:
            raise ValueError("Enable the source before crawling")
        await public_host_check(row.canonical_url)
        async with self._session() as db:
            active = await db.scalar(select(CrawlJobRecord).where(CrawlJobRecord.tenant_id == principal.tenant_id, CrawlJobRecord.source_id == source_id, CrawlJobRecord.status == "running"))
            if active:
                if active.started_at.replace(tzinfo=UTC) > datetime.now(UTC) - timedelta(seconds=300):
                    raise ValueError("A crawl for this source is already running")
                active.status = 'failed'
                active.error = 'Worker lease expired before completion'
                active.finished_at = datetime.now(UTC)
            job = CrawlJobRecord(tenant_id=principal.tenant_id, id=str(uuid4()), source_id=source_id, status="running")
            db.add(job)
            await db.commit()
        documents: list[SourceDocumentView] = []
        now = datetime.now(UTC)
        try:
            if row.parser_type == 'html':
                from urllib.robotparser import RobotFileParser
                parts = urlsplit(row.canonical_url)
                robots_url = urlunsplit((parts.scheme, parts.netloc, '/robots.txt', '', ''))
                robots = await public_request('GET', robots_url, max_bytes=65536, timeout=10, redirects=3)
                permitted = robots.status_code == 404
                if robots.status_code == 200:
                    rules = RobotFileParser()
                    rules.parse(robots.text.splitlines())
                    permitted = rules.can_fetch('DarkTraceX', row.canonical_url)
                async with self._session() as robots_db:
                    current = await robots_db.get(SourceRecord, (principal.tenant_id, source_id))
                    current.robots_status = 'allowed' if permitted else 'blocked'
                    await robots_db.commit()
                if not permitted:
                    raise ValueError('Source crawling is not permitted by robots policy')
            for attempt in range(3):
                try:
                    response = await public_request('GET', row.canonical_url,
                        max_bytes=get_settings().source_max_response_bytes,
                        timeout=get_settings().outbound_timeout_seconds, redirects=3,
                        headers={'User-Agent': 'DarkTraceX/1.0 defensive-source-crawler'})
                    response.raise_for_status()
                    break
                except (httpx.HTTPError, TimeoutError) as exc:
                    if attempt == 2 or isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500 and exc.response.status_code != 429:
                        raise
                    async with self._session() as retry_db:
                        retry_job = await retry_db.get(CrawlJobRecord, (principal.tenant_id, job.id))
                        retry_job.retry_count = attempt + 1
                        await retry_db.commit()
                    await asyncio.sleep(2 ** attempt)
            content_type = response.headers.get('content-type', 'text/plain')
            if not any(kind in content_type.lower() for kind in ('text/', 'html', 'xml', 'json')):
                raise ValueError('Unsupported source content type')
            raw = response.content.decode('utf-8', errors='replace')
            entries = []
            if row.parser_type in {'rss', 'atom', 'json'}:
                from app.services.source_parsers import parse_structured
                title, normalized, links, entries = parse_structured(raw, row.parser_type, row.canonical_url, normalize_html)
            else:
                title, normalized, links = normalize_html(raw, content_type)
            if len(normalized) < 20:
                raise ValueError("Source returned empty or unusable content")
            content_hash = hashlib.sha256(normalized.encode()).hexdigest()
            entities = extract_entities(normalized)
            async with self._session() as db:
                job = await db.scalar(select(CrawlJobRecord).where(CrawlJobRecord.tenant_id == principal.tenant_id, CrawlJobRecord.id == job.id).with_for_update())
                source = await db.scalar(select(SourceRecord).where(SourceRecord.tenant_id == principal.tenant_id, SourceRecord.id == source_id).with_for_update())
                existing = await db.scalar(select(SourceDocumentRecord).where(SourceDocumentRecord.tenant_id == principal.tenant_id, SourceDocumentRecord.content_hash == content_hash))
                if existing:
                    existing.last_seen = now
                    job.duplicates_found = 1
                    job.records_extracted = 1
                    job.pages_successful = 1
                    job.bytes_downloaded = len(raw.encode())
                    document = existing
                else:
                    document = SourceDocumentRecord(tenant_id=principal.tenant_id, source_id=source_id, crawl_id=job.id, source_url=row.url, canonical_url=row.canonical_url, title=title, raw_content=raw, normalized_text=normalized, content_hash=content_hash, collected_at=now, first_seen=now, last_seen=now, source_category=row.category, metadata_json={"content_type": content_type, "links": links, "entities": entities, "entries":entries})
                    db.add(document)
                    job.records_extracted = 1
                    job.pages_successful = 1
                    job.bytes_downloaded = len(raw.encode())
                await db.flush()
                extracted_entities: dict[tuple[str, str], str] = {}
                for entity_type, values in entities.items():
                    for value in values:
                        entity_id = hashlib.sha256(f"{principal.tenant_id}:{entity_type}:{value.casefold()}".encode()).hexdigest()
                        existing_entity = await db.scalar(select(IntelligenceEntityRecord).where(IntelligenceEntityRecord.tenant_id == principal.tenant_id, IntelligenceEntityRecord.id == entity_id).with_for_update())
                        if existing_entity:
                            existing_entity.last_seen = now
                            existing_entity.confidence = max(existing_entity.confidence, 95)
                        else:
                            db.add(IntelligenceEntityRecord(tenant_id=principal.tenant_id, id=entity_id, entity_type=entity_type, value=value, confidence=95, extraction_method="deterministic", first_seen=now, last_seen=now, metadata_json={"source_id": source_id, "document_id": document.id}))
                        observation = await db.scalar(select(EntityObservationRecord).where(EntityObservationRecord.tenant_id == principal.tenant_id, EntityObservationRecord.entity_id == entity_id, EntityObservationRecord.document_id == document.id))
                        if not observation:
                            db.add(EntityObservationRecord(tenant_id=principal.tenant_id, entity_id=entity_id, document_id=document.id, source_id=source_id, confidence=95, observed_at=now))
                        extracted_entities[(entity_type, value)] = entity_id
                        if entity_type in {"ipv4", "ipv6", "domain", "url", "email", "md5", "sha1", "sha256", "cve"}:
                            event_key = f"entity:{source_id}:{document.id}:{entity_id}"
                            if not await db.scalar(select(ThreatEventRecord).where(ThreatEventRecord.tenant_id == principal.tenant_id, ThreatEventRecord.dedupe_key == event_key)):
                                db.add(ThreatEventRecord(tenant_id=principal.tenant_id, event_type="entity.detected", source_id=source_id, document_id=document.id, entity_id=entity_id, severity="info", confidence=95, reason=f"Deterministic {entity_type} extraction from normalized source content", evidence={"source_id": source_id, "crawl_id": job.id, "document_id": document.id, "entity_type": entity_type, "entity_value": value, "extraction_method": "deterministic"}, status="new", dedupe_key=event_key))
                job.status = "completed"
                job.finished_at = datetime.now(UTC)
                job.duration_ms = max(0, int((job.finished_at-job.started_at.replace(tzinfo=UTC)).total_seconds()*1000))
                source.health = "HEALTHY"
                source.last_success_at = now
                source.last_crawled_at = now
                source.last_checked_at = now
                source.failure_count = 0
                source.last_error = None
                monitors = (await db.scalars(select(KeywordMonitorRecord).where(KeywordMonitorRecord.tenant_id == principal.tenant_id, KeywordMonitorRecord.enabled.is_(True)))).all()
                for monitor in monitors:
                    if monitor.term.casefold() in normalized.casefold():
                        from app.services.risk import keyword_risk
                        risk = keyword_risk(row.trust_level)
                        evidence = {"risk": risk, "source_id": source_id, "crawl_id": job.id, "document_id": document.id, "source_url": row.canonical_url, "term": monitor.term, "content_hash": content_hash}
                        dedupe = f"source:{source_id}:{content_hash}:{monitor.id}"
                        alert = await db.scalar(select(OperationalAlertRecord).where(OperationalAlertRecord.tenant_id == principal.tenant_id, OperationalAlertRecord.dedupe_key == dedupe))
                        if not alert:
                            event_key = f"keyword:{source_id}:{content_hash}:{monitor.id}"
                            event = await db.scalar(select(ThreatEventRecord).where(ThreatEventRecord.tenant_id == principal.tenant_id, ThreatEventRecord.dedupe_key == event_key))
                            if not event:
                                event = ThreatEventRecord(tenant_id=principal.tenant_id, event_type="keyword.match", source_id=source_id, document_id=document.id, entity_id=next(iter(extracted_entities.values()), None), severity="medium", confidence=85, reason=f"Configured keyword monitor matched '{monitor.term}'", evidence={**evidence, "monitor_id": monitor.id}, status="new", dedupe_key=event_key)
                                db.add(event)
                                await db.flush()
                            evidence["event_id"] = event.id
                            db.add(OperationalAlertRecord(tenant_id=principal.tenant_id, dedupe_key=dedupe, title=f"Source keyword '{monitor.term}' matched: {title}"[:512], severity=risk["severity"], score=risk["score"], evidence=evidence))
                db.add(AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="source.crawl.completed", resource_type="crawl", resource_id=job.id, outcome="success", metadata_json={"source_id": source_id, "documents": job.records_extracted, "duplicates": job.duplicates_found}))
                await db.commit()
                documents = [SourceDocumentView(id=document.id, source_id=document.source_id, crawl_id=document.crawl_id, source_url=document.source_url, canonical_url=document.canonical_url, title=document.title, content_hash=document.content_hash, collected_at=document.collected_at, status=document.status, tags=document.tags)]
                return self._job_view(job), documents
        except (httpx.HTTPError, ValueError, TimeoutError) as exc:
            async with self._session() as db:
                job = await db.scalar(select(CrawlJobRecord).where(CrawlJobRecord.tenant_id == principal.tenant_id, CrawlJobRecord.id == job.id).with_for_update())
                source = await db.scalar(select(SourceRecord).where(SourceRecord.tenant_id == principal.tenant_id, SourceRecord.id == source_id).with_for_update())
                job.status = "failed"
                job.finished_at = datetime.now(UTC)
                job.duration_ms = max(0, int((job.finished_at-job.started_at.replace(tzinfo=UTC)).total_seconds()*1000))
                job.pages_failed = 1
                job.error_type = type(exc).__name__
                job.error = 'Source crawl failed: ' + type(exc).__name__
                source.failure_count += 1
                source.last_failed_at = now
                source.last_checked_at = now
                source.last_error = job.error
                source.health = "OFFLINE" if source.failure_count >= 3 else "DEGRADED"
                db.add(AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="source.crawl.failed", resource_type="crawl", resource_id=job.id, outcome="failure", metadata_json={"source_id": source_id, "error_type": type(exc).__name__}))
                await db.commit()
            raise

    async def history(self, principal: Principal, source_id: str, limit: int = 50) -> list[CrawlJobView]:
        async with self._session() as db:
            rows = (await db.scalars(select(CrawlJobRecord).where(CrawlJobRecord.tenant_id == principal.tenant_id, CrawlJobRecord.source_id == source_id).order_by(desc(CrawlJobRecord.started_at)).limit(limit))).all()
            return [self._job_view(row) for row in rows]

    async def crawl_jobs(self, principal: Principal, limit: int = 100, offset: int = 0) -> list[CrawlJobView]:
        async with self._session() as db:
            rows = (await db.scalars(select(CrawlJobRecord).where(CrawlJobRecord.tenant_id == principal.tenant_id).order_by(desc(CrawlJobRecord.started_at)).offset(offset).limit(limit))).all()
            return [self._job_view(row) for row in rows]

    async def documents(self, principal: Principal, source_id: str | None = None, limit: int = 100, offset: int = 0) -> list[SourceDocumentView]:
        async with self._session() as db:
            statement = select(SourceDocumentRecord).where(SourceDocumentRecord.tenant_id == principal.tenant_id).order_by(desc(SourceDocumentRecord.collected_at)).offset(offset).limit(limit)
            if source_id:
                statement = statement.where(SourceDocumentRecord.source_id == source_id)
            rows = (await db.scalars(statement)).all()
            return [SourceDocumentView(id=row.id, source_id=row.source_id, crawl_id=row.crawl_id, source_url=row.source_url, canonical_url=row.canonical_url, title=row.title, content_hash=row.content_hash, collected_at=row.collected_at, status=row.status, tags=row.tags, normalized_text=row.normalized_text[:1000], metadata={"entity_count":sum(len(v) for v in row.metadata_json.get("entities",{}).values()),"entry_count":len(row.metadata_json.get("entries",[]))}) for row in rows]

    async def entities(self, principal: Principal, query: str | None = None, limit: int = 100, offset: int = 0) -> list[EntityView]:
        async with self._session() as db:
            statement = select(IntelligenceEntityRecord).where(IntelligenceEntityRecord.tenant_id == principal.tenant_id).order_by(desc(IntelligenceEntityRecord.last_seen)).offset(offset).limit(limit)
            if query:
                statement = statement.where(IntelligenceEntityRecord.value.ilike(f"%{query}%"))
            rows = (await db.scalars(statement)).all()
            return [EntityView.model_validate(row, from_attributes=True) for row in rows]

    async def events(self, principal: Principal, limit: int = 100, offset: int = 0) -> list[ThreatEventView]:
        async with self._session() as db:
            rows = (await db.scalars(select(ThreatEventRecord).where(ThreatEventRecord.tenant_id == principal.tenant_id).order_by(desc(ThreatEventRecord.created_at)).offset(offset).limit(limit))).all()
            return [ThreatEventView.model_validate(row, from_attributes=True) for row in rows]


source_management = SourceManagementService
