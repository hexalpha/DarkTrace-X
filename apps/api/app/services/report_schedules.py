"""Durable, validated report schedules; delivery stays disabled until SMTP is configured."""
from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.security import Principal
from app.domain.schemas import ReportSchedule
from app.services.intelligence import session
from app.storage.models import AuditEventRecord, ReportScheduleRecord

_CRON_FIELD = re.compile(r"^[0-9*/?,\-]+$")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_schedule(payload: ReportSchedule) -> list[str]:
    from app.services.cron import parse
    parse(payload.cron)
    fields = payload.cron.strip().split()
    if len(fields) != 5 or any(not _CRON_FIELD.fullmatch(field) or len(field) > 20 for field in fields):
        raise ValueError("Cron must contain five bounded fields using digits, *, /, ?, or -")
    recipients = sorted({item.strip().casefold() for item in payload.recipients if item.strip()})
    if not recipients or len(recipients) > 100 or any(len(item) > 320 or not _EMAIL.fullmatch(item) for item in recipients):
        raise ValueError("Recipients must be valid email addresses")
    return recipients


class ReportScheduleService:
    async def create(self, principal: Principal, payload: ReportSchedule) -> dict:
        recipients = validate_schedule(payload)
        async with session() as db:
            record = ReportScheduleRecord(tenant_id=principal.tenant_id, name=payload.name.strip(), cron=payload.cron.strip(), format=payload.format, recipients=recipients)
            db.add(record)
            await db.flush()
            db.add(AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id, action="report_schedule.created", resource_type="report_schedule", resource_id=record.id, outcome="success", metadata_json={"format": record.format, "recipients": len(recipients)}))
            await db.commit()
        return self.view(record)

    async def list(self, principal: Principal) -> list[dict]:
        async with session() as db:
            rows = (await db.scalars(select(ReportScheduleRecord).where(ReportScheduleRecord.tenant_id == principal.tenant_id).order_by(ReportScheduleRecord.created_at.desc()))).all()
        return [self.view(row) for row in rows]

    async def remove(self, principal: Principal, ident: str) -> bool:
        async with session() as db:
            row = await db.scalar(select(ReportScheduleRecord).where(ReportScheduleRecord.tenant_id == principal.tenant_id, ReportScheduleRecord.id == ident).with_for_update())
            if row is None:
                return False
            await db.delete(row)
            await db.commit()
            return True

    @staticmethod
    def view(record: ReportScheduleRecord) -> dict:
        return {"id": record.id, "name": record.name, "cron": record.cron, "format": record.format, "recipients": record.recipients, "enabled": record.enabled, "delivery_status": record.delivery_status, "last_run_at": record.last_run_at, "created_at": record.created_at}


report_schedule_service = ReportScheduleService()
