import unittest
from datetime import UTC,datetime,timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from sqlalchemy import create_engine,select
from app.storage.models import Base,DeliveryJobRecord,TenantRecord,WebhookSubscriptionRecord
from app.services.delivery_worker import DeliveryWorker
from app.services.cron import due,parse
from tests.test_persistence import AsyncSessionAdapter


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_webhook_retry_then_delivery_and_history(self):
        engine=create_engine('sqlite://');Base.metadata.create_all(engine)
        db=SimpleNamespace(sessions=lambda:AsyncSessionAdapter(engine))
        worker=DeliveryWorker(db,SimpleNamespace())
        async with db.sessions() as session:
            session.add(TenantRecord(id='delivery-test',name='test'))
            session.add(WebhookSubscriptionRecord(tenant_id='delivery-test',id='hook',name='test',url='https://example.com',event_types=['alert.created'],encrypted_secret='not-used'))
            session.add(DeliveryJobRecord(id='job',tenant_id='delivery-test',kind='webhook',target_id='hook',dedupe_key='one',payload={'event_type':'alert.created'}))
            await session.commit()
        with patch('app.services.webhooks.webhook_service.deliver',AsyncMock(side_effect=TimeoutError())):
            self.assertTrue(await worker.process_one())
        async with db.sessions() as session:
            job=await session.get(DeliveryJobRecord,'job')
            self.assertEqual(job.status,'retry');self.assertEqual(job.attempts,1)
            self.assertEqual(job.last_error,'TimeoutError')
            job.next_attempt_at=datetime.now(UTC)-timedelta(seconds=1);await session.commit()
        with patch('app.services.webhooks.webhook_service.deliver',AsyncMock()):
            self.assertTrue(await worker.process_one())
        async with db.sessions() as session:
            job=await session.get(DeliveryJobRecord,'job')
            self.assertEqual(job.status,'delivered');self.assertEqual(job.attempts,2)
        engine.dispose()

    def test_cron_bounds_and_calendar(self):
        self.assertTrue(due('*/5 8 * * 1-5',datetime(2026,9,21,8,10,tzinfo=UTC)))
        self.assertFalse(due('*/5 8 * * 1-5',datetime(2026,9,21,8,11,tzinfo=UTC)))
        for cron in ('61 * * * *','* 25 * * *','*/0 * * * *','* * 0 * *'):
            with self.assertRaises(ValueError):
                parse(cron)
