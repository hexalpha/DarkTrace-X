import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.security import Principal, Role
from app.domain.schemas import SourceCreate, SourceType
from app.services.source_management import SourceManagementService, canonicalize, extract_entities, normalize_html, public_host_check
from app.storage.models import Base, CrawlJobRecord, SourceDocumentRecord
from tests.test_persistence import AsyncSessionAdapter


class FakeResponse:
    status_code = 200
    headers = {"content-type": "text/html; charset=utf-8"}

    async def aiter_bytes(self):
        yield b"<html><head><title>Critical CVE bulletin</title></head><body>Critical CVE-2026-1234 affects 203.0.113.7. Contact soc@example.com.</body></html>"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


class FakeClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, *args, **kwargs):
        return FakeResponse()

    def stream(self, *args, **kwargs):
        return FakeResponse()


@asynccontextmanager
async def unlocked(*args):
    yield


class SourceManagementTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.lock_patch = patch('app.services.source_management.source_lock', unlocked)
        self.lock_patch.start()
        self.addCleanup(self.lock_patch.stop)
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = SimpleNamespace(ready=True, sessions=lambda: AsyncSessionAdapter(self.engine))
        self.service = SourceManagementService(self.db)
        self.principal = Principal(user_id="operator", tenant_id="tenant-a", role=Role.ADMIN, email="operator@example.com")

    async def asyncTearDown(self):
        self.engine.dispose()

    async def test_public_url_guard_rejects_private_targets(self):
        with self.assertRaises(ValueError):
            await public_host_check("http://127.0.0.1:8080/internal")
        with self.assertRaises(ValueError):
            canonicalize("https://user:password@example.com/feed")

    async def test_normalization_extracts_entities_without_mutating_source_text(self):
        title, text, links = normalize_html("<html><title>Bulletin</title><script>ignore()</script><p>CVE-2026-1234 203.0.113.7</p></html>", "text/html")
        self.assertEqual(title, "Bulletin")
        self.assertNotIn("ignore", text)
        self.assertIn("CVE-2026-1234", extract_entities(text)["cve"])
        self.assertEqual(links, [])

    async def test_lifecycle_crawl_dedup_history_and_provenance(self):
        payload = SourceCreate(name="Approved bulletin", url="https://example.com/feed", source_type=SourceType.SECURITY_BLOG, category="security", parser_type="html")
        with patch("app.services.source_management.public_host_check", new=AsyncMock()), patch("app.services.source_management.public_request", new=AsyncMock(return_value=__import__("httpx").Response(200, headers={"content-type":"text/html"}, content=b"<title>Critical CVE bulletin</title>Critical CVE-2026-1234 affects 203.0.113.7. Contact soc@example.com.", request=__import__("httpx").Request("GET", "https://example.com/feed")))):
            source = await self.service.create(self.principal, payload)
            self.assertFalse(source.enabled)
            source = await self.service.set_enabled(self.principal, source.id, True)
            self.assertTrue(source.enabled)
            validation = await self.service.validate(self.principal, source.id)
            self.assertTrue(validation.valid)
            job, documents = await self.service.crawl(self.principal, source.id)
            self.assertEqual(job.status, "completed")
            self.assertEqual(len(documents), 1)
            duplicate_job, duplicate_documents = await self.service.crawl(self.principal, source.id)
            self.assertEqual(duplicate_job.duplicates_found, 1)
            self.assertEqual(duplicate_documents[0].content_hash, documents[0].content_hash)
            history = await self.service.history(self.principal, source.id)
            self.assertEqual(len(history), 2)
            async with self.db.sessions() as db:
                document = await db.scalar(select(SourceDocumentRecord).where(SourceDocumentRecord.tenant_id == "tenant-a"))
                jobs = (await db.scalars(select(CrawlJobRecord).where(CrawlJobRecord.tenant_id == "tenant-a"))).all()
            self.assertIn(document.crawl_id, {row.id for row in history})
            self.assertEqual(len(jobs), 2)


if __name__ == "__main__":
    unittest.main()
