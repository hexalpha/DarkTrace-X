"""Restart-safe source scheduler for configured recurring crawl policies."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import Settings
from app.core.security import Principal, Role
from app.services.source_management import SourceManagementService
from app.storage.models import SourceRecord, TenantRecord

logger = logging.getLogger(__name__)


POLICY_MINUTES = {"hourly": 60, "daily": 1440, "weekly": 10080}


class SourceScheduler:
    def __init__(self, database, settings: Settings) -> None:
        self.database = database
        self.settings = settings
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def run_once(self) -> int:
        now = datetime.now(UTC)
        due: list[tuple[str, str]] = []
        async with self.database.sessions() as db:
            rows = (await db.scalars(select(SourceRecord).join(TenantRecord, TenantRecord.id == SourceRecord.tenant_id).where(TenantRecord.active.is_(True), SourceRecord.enabled.is_(True), SourceRecord.crawl_policy != "manual").with_for_update(of=SourceRecord, skip_locked=True))).all()
            for row in rows:
                if row.next_scheduled_at and row.next_scheduled_at > now:
                    continue
                minutes = row.frequency_minutes if row.crawl_policy == "custom" else POLICY_MINUTES.get(row.crawl_policy, 0)
                if minutes <= 0:
                    continue
                row.next_scheduled_at = now + timedelta(minutes=minutes)
                due.append((row.tenant_id, row.id))
            await db.commit()
        completed = 0
        service = SourceManagementService(self.database)
        for tenant_id, source_id in due:
            principal = Principal(user_id="scheduler", tenant_id=tenant_id, role=Role.ADMIN, email="scheduler@darktracex.internal")
            try:
                await service.crawl(principal, source_id)
                completed += 1
            except Exception as exc:  # One source must not stop the scheduler.
                logger.warning("scheduled source crawl failed source_id=%s error=%s", source_id, exc.__class__.__name__)
        return completed

    async def start(self) -> None:
        if not self.settings.crawler_scheduler_enabled or self._task:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="darktracex-source-scheduler")

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                if not self.database.ready:
                    await self.database.connect()
                await self.run_once()
            except Exception as exc:
                logger.warning("source scheduler cycle failed error=%s", exc.__class__.__name__)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.settings.crawler_scheduler_interval_seconds)
            except TimeoutError:
                continue

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task
            self._task = None
