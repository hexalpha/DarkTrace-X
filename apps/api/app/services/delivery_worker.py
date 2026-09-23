"""Durable, at-least-once delivery. Receiver deduplicates stable delivery IDs."""
import asyncio
import base64
import logging
import smtplib
import ssl
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.storage.models import DeliveryJobRecord, ReportScheduleRecord, WebhookSubscriptionRecord, TenantRecord, AuditEventRecord
from app.services.cron import due

logger=logging.getLogger(__name__)


class DeliveryWorker:
    def __init__(self,database,settings):
        self.database,self.settings=database,settings
        self.stop_event=asyncio.Event()
        self.task=None
        self.last_success=None

    async def enqueue_reports(self):
        now=datetime.now(UTC).replace(second=0,microsecond=0)
        async with self.database.sessions() as db:
            schedules=(await db.scalars(select(ReportScheduleRecord).join(TenantRecord,TenantRecord.id==ReportScheduleRecord.tenant_id).where(TenantRecord.active.is_(True),ReportScheduleRecord.enabled.is_(True)))).all()
            for row in schedules:
                if not self.settings.smtp_host or not self.settings.smtp_sender:
                    row.delivery_status='smtp_unavailable'
                    continue
                if due(row.cron,now):
                    await db.execute(insert(DeliveryJobRecord).values(id=str(uuid4()),tenant_id=row.tenant_id,kind='report',target_id=row.id,
                        dedupe_key='report:'+row.id+':'+now.isoformat(),payload={},status='pending',attempts=0,
                        next_attempt_at=now,result={},created_at=now).on_conflict_do_nothing())
                    row.delivery_status='queued'
            await db.commit()

    async def generate_report(self,job,schedule):
        from app.services.operations import OperationalService
        from app.services.intelligence import intelligence_service
        from app.services.reports import report_service
        from app.core.security import Principal,Role
        from app.domain.schemas import ReportRequest
        principal=Principal(tenant_id=job.tenant_id,user_id='report-worker',email='worker@darktracex.internal',role=Role.ADMIN)
        media,filename,body=report_service.render(job.tenant_id,schedule.format,ReportRequest(title=schedule.name),
            await OperationalService(self.database).list_alerts(principal),await intelligence_service.list_iocs(job.tenant_id),await intelligence_service.cves())
        return {'media_type':media,'filename':filename,'body':base64.b64encode(body).decode()}

    def send_report(self,job,schedule):
        message=EmailMessage()
        message['From']=self.settings.smtp_sender
        message['To']=', '.join(schedule.recipients)
        message['Subject']=schedule.name
        message['Message-ID']=f'<{job.id}@darktracex.local>'
        message.set_content('Scheduled DarkTrace X intelligence report. Review source evidence before acting.')
        major,minor=job.result['media_type'].split('/',1)
        message.add_attachment(base64.b64decode(job.result['body']),maintype=major,subtype=minor,filename=job.result['filename'])
        with smtplib.SMTP_SSL(self.settings.smtp_host,self.settings.smtp_port,timeout=15,context=ssl.create_default_context()) as smtp:
            if self.settings.smtp_username:
                smtp.login(self.settings.smtp_username,self.settings.smtp_password.get_secret_value() if self.settings.smtp_password else '')
            smtp.send_message(message)

    async def process_one(self):
        now=datetime.now(UTC)
        async with self.database.sessions() as db:
            job=await db.scalar(select(DeliveryJobRecord).where(DeliveryJobRecord.status.in_(['pending','retry']),DeliveryJobRecord.next_attempt_at<=now).order_by(DeliveryJobRecord.next_attempt_at).with_for_update(skip_locked=True).limit(1))
            if not job:
                return False
            job.attempts+=1
            try:
                tenant=await db.get(TenantRecord,job.tenant_id)
                if not tenant or not tenant.active:
                    job.status='cancelled'
                elif job.kind=='webhook':
                    row=await db.get(WebhookSubscriptionRecord,(job.tenant_id,job.target_id))
                    if not row or not row.enabled:
                        job.status='cancelled'
                    else:
                        from app.services.webhooks import webhook_service
                        await webhook_service.deliver(row,job.payload)
                        row.last_delivered_at=now;row.failure_count=0
                        job.status='delivered';job.result={'delivered_at':now.isoformat()}
                elif job.kind=='report':
                    row=await db.get(ReportScheduleRecord,(job.tenant_id,job.target_id))
                    if not row or not row.enabled:
                        job.status='cancelled'
                    elif not job.result.get('body'):
                        # Persist the artifact in a separate queue step before network delivery.
                        job.result=await self.generate_report(job,row)
                        job.status='pending'
                        job.attempts-=1
                    else:
                        await asyncio.to_thread(self.send_report,job,row)
                        job.status='delivered';row.delivery_status='delivered';row.last_run_at=now
                else:
                    job.status='cancelled'
                job.last_error=None
            except Exception as exc:
                job.last_error=type(exc).__name__
                job.status='failed' if job.attempts>=5 else 'retry'
                job.next_attempt_at=now+timedelta(seconds=min(900,5*2**job.attempts))
                logger.warning('delivery.failed job_id=%s tenant_id=%s error_type=%s',job.id,job.tenant_id,type(exc).__name__)
            db.add(AuditEventRecord(tenant_id=job.tenant_id,actor_id='delivery-worker',action='delivery.'+job.status,
                resource_type=job.kind,resource_id=job.id,outcome='failure' if job.last_error else 'success',metadata_json={'attempts':job.attempts,'error_type':job.last_error}))
            await db.commit()
            return True

    async def loop(self):
        while not self.stop_event.is_set():
            try:
                await self.enqueue_reports()
                for _ in range(10):
                    if not await self.process_one():
                        break
                self.last_success=datetime.now(UTC).isoformat()
            except Exception as exc:
                logger.warning('delivery.cycle.failed error_type=%s',type(exc).__name__)
            try:
                await asyncio.wait_for(self.stop_event.wait(),timeout=5)
            except TimeoutError:
                pass

    async def start(self):
        if self.settings.delivery_worker_enabled:
            self.task=asyncio.create_task(self.loop(),name='delivery-worker')

    async def stop(self):
        self.stop_event.set()
        if self.task:
            await self.task
