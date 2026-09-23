import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.api.v1.advanced import router
from app.core.config import Settings, get_settings
from app.core.security import Principal, Role, create_access_token
from app.services.detection import TelemetryBatch, analyze


def events(values, entity="host-a", start=None):
    start = start or datetime.now(UTC) - timedelta(hours=2)
    return [{"id": f"{entity}-{i}", "entity": entity, "metric": "failed_logins", "value": value,
        "observed_at": (start + timedelta(minutes=i)).isoformat()} for i, value in enumerate(values)]


class DetectionTests(unittest.TestCase):
    def test_cold_start_and_constant_baseline(self):
        self.assertEqual(analyze(events([3] * 19))["learning"], 1)
        result = analyze(events([3] * 30))
        self.assertEqual(result["anomalies"], [])
        self.assertEqual(result["predictions"][0]["risk_score"], 0)

    def test_spike_and_forecast(self):
        result = analyze(events([2] * 25 + [20] * 5))
        self.assertEqual(len(result["anomalies"]), 5)
        self.assertEqual(result["anomalies"][0]["baseline"], 2)
        self.assertGreater(result["predictions"][0]["risk_score"], 35)

    def test_order_and_entity_isolation(self):
        data = events([2] * 25 + [20]) + events([500] * 26, "host-b")
        self.assertEqual(analyze(data)["anomalies"], analyze(list(reversed(data)))["anomalies"])
        self.assertEqual({e["entity"] for e in analyze(data)["anomalies"]}, {"host-a"})

    def test_simultaneous_events(self):
        data = events([2] * 30)
        for event in data:
            event["observed_at"] = data[0]["observed_at"]
        self.assertEqual(analyze(data)["predictions"], [])

    def test_stale_evidence(self):
        self.assertEqual(analyze(events([2] * 25 + [20] * 5, start=datetime.now(UTC) - timedelta(days=3)))["predictions"], [])

    def test_input_validation(self):
        for value in [-1, float("nan"), float("inf")]:
            with self.assertRaises(ValidationError):
                TelemetryBatch(events=events([value]))
        event = events([1])[0]
        with self.assertRaises(ValidationError):
            TelemetryBatch(events=[event, event])
        event["observed_at"] = "2020-01-01T00:00:00"
        with self.assertRaises(ValidationError):
            TelemetryBatch(events=[event])


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        from app.core.security import decode_access_token
        async def active(token, settings):
            return decode_access_token(token, settings)
        auth = patch("app.core.security.validate_active_token", side_effect=active)
        auth.start()
        self.addCleanup(auth.stop)
        from tests.test_production_config import ProductionConfigurationTests
        with patch('pathlib.Path.is_file', return_value=True):
            self.settings = Settings(**ProductionConfigurationTests().config())
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_settings] = lambda: self.settings
        self.client = TestClient(app)

    def headers(self, role=Role.ANALYST, tenant="tenant-a"):
        token = create_access_token(Principal(user_id="test-user", tenant_id=tenant, role=role, email="test@example.com"), self.settings)
        return {"Authorization": f"Bearer {token}"}

    def rpc(self, method, params=None, headers=None):
        return self.client.post("/api/v1/mcp", headers=headers or self.headers(), json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})

    def test_auth_roles(self):
        self.assertEqual(self.client.get("/api/v1/detection/overview").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/mcp", json={}).status_code, 401)
        self.assertEqual(self.client.put("/api/v1/marketplace/behavior-analyzer", headers=self.headers(), json={"enabled": True}).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/telemetry", headers=self.headers(Role.VIEWER), json={"events": events([1])}).status_code, 403)

    def test_mcp_lifecycle_errors(self):
        self.assertEqual(self.rpc("initialize").json()["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(len(self.rpc("tools/list").json()["result"]["tools"]), 3)
        self.assertEqual(self.rpc("unknown").json()["error"]["code"], -32601)
        self.assertEqual(self.rpc("tools/call", {"name": "unknown"}).json()["error"]["code"], -32602)
        self.assertEqual(self.rpc("ping", headers={**self.headers(), "Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/mcp", headers=self.headers(), content="{").json()["error"]["code"], -32700)
        self.assertEqual(self.client.post("/api/v1/mcp", headers=self.headers(), json={"jsonrpc": "2.0", "method": "notifications/initialized"}).status_code, 202)

    def test_mcp_tenant(self):
        with patch("app.api.v1.advanced.snapshot", new_callable=AsyncMock) as read:
            read.return_value = {"event_count": 0, "baseline_ready": 0, "learning": 0}
            self.rpc("tools/call", {"name": "telemetry_health"}, self.headers(tenant="tenant-b"))
            self.assertEqual(read.call_args.args[0].tenant_id, "tenant-b")

    def test_storage_unavailable(self):
        with patch("app.api.v1.advanced.database_module.database", None):
            self.assertEqual(self.client.get("/api/v1/detection/overview", headers=self.headers()).status_code, 503)
            self.assertTrue(self.rpc("tools/call", {"name": "telemetry_health"}).json()["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
