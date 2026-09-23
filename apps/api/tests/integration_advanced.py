"""Run explicitly against the configured PostgreSQL; uses isolated temporary tenant IDs."""
import unittest
from uuid import uuid4
import httpx
from fastapi import FastAPI
from sqlalchemy import delete
from app.api.v1.advanced import router
from app.core.config import get_settings
from app.core.security import Principal, Role, create_access_token
from app.storage import database as db_module
from app.storage.models import AuditEventRecord, ExtensionRecord, TelemetryRecord, TenantRecord, UserRecord
from tests.test_advanced import events


class PersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_lifecycle_and_tenant_isolation(self):
        settings = get_settings()
        db = db_module.configure_database(settings)
        await db.connect()
        if not db.ready:
            await db.close()
            self.skipTest("Configured PostgreSQL is unavailable")
        tenants = [f"advanced-test-{uuid4().hex}" for _ in range(2)]
        async with db.sessions() as session:
            for tenant in tenants:
                session.add(TenantRecord(id=tenant, name=tenant))
                session.add(UserRecord(id=tenant, tenant_id=tenant, email="test@example.com", display_name="Test", password_hash="unused", role="admin"))
            await session.commit()
        def headers(tenant):
            p = Principal(user_id=tenant, tenant_id=tenant, role=Role.ADMIN, email="test@example.com")
            return {"Authorization": f"Bearer {create_access_token(p, settings)}"}
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                a, b = headers(tenants[0]), headers(tenants[1])
                payload = {"events": events([2] * 25 + [20] * 5)}
                first = await client.post("/api/v1/telemetry", headers=a, json=payload)
                self.assertEqual(first.status_code, 201, first.text)
                self.assertEqual(first.json()["inserted"], 30)
                second = await client.post("/api/v1/telemetry", headers=a, json=payload)
                self.assertEqual(second.json()["duplicates"], 30)
                result = await client.get("/api/v1/detection/overview", headers=a)
                self.assertEqual(len(result.json()["anomalies"]), 5)
                other = await client.get("/api/v1/detection/overview", headers=b)
                self.assertEqual(other.json()["event_count"], 0)
                path = "/api/v1/marketplace/behavior-analyzer"
                self.assertEqual((await client.post(path + "/run", headers=a)).status_code, 409)
                self.assertEqual((await client.put(path, headers=a, json={"enabled": True})).status_code, 200)
                self.assertEqual((await client.post(path + "/run", headers=a)).status_code, 200)
                self.assertEqual((await client.post(path + "/run", headers=b)).status_code, 409)
                await client.put(path, headers=a, json={"enabled": False})
                self.assertEqual((await client.post(path + "/run", headers=a)).status_code, 409)
                self.assertEqual((await client.delete(path, headers=a)).status_code, 204)
                catalog = (await client.get("/api/v1/marketplace", headers=a)).json()
                self.assertFalse(catalog["plugins"][0]["installed"])
        finally:
            async with db.sessions() as session:
                for model in (AuditEventRecord, ExtensionRecord, TelemetryRecord, UserRecord):
                    await session.execute(delete(model).where(model.tenant_id.in_(tenants)))
                await session.execute(delete(TenantRecord).where(TenantRecord.id.in_(tenants)))
                await session.commit()
            await db.close()


if __name__ == "__main__":
    unittest.main()
