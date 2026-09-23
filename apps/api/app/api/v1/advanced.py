import json
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.security import Principal, Role, current_principal, require_role
from app.services.detection import TelemetryBatch, analyze
from app.storage import database as database_module
from app.storage.models import AuditEventRecord, ExtensionRecord, TelemetryRecord, OperationalAlertRecord

router = APIRouter(tags=["Detection & Extensions"])
Reader = Annotated[Principal, Depends(current_principal)]
Writer = Annotated[Principal, Depends(require_role(Role.ANALYST, Role.LEAD, Role.ADMIN))]
Admin = Annotated[Principal, Depends(require_role(Role.ADMIN))]

CATALOG = [
    {"id": "behavior-analyzer", "name": "Behavior Analyzer", "category": "Detection", "description": "Analyze unusual activity using learned entity baselines.", "version": "1.0.0", "scopes": ["telemetry:read"], "network_egress": False},
    {"id": "threat-forecast", "name": "Threat Forecast", "category": "Intelligence", "description": "Rank emerging behavioral risk with traceable evidence.", "version": "1.0.0", "scopes": ["telemetry:read"], "network_egress": False},
    {"id": "telemetry-quality", "name": "Telemetry Quality", "category": "Operations", "description": "Check baseline coverage and collection freshness.", "version": "1.0.0", "scopes": ["telemetry:read"], "network_egress": False},
]


def sessions():
    db = database_module.database
    if db is None or not db.ready or db.sessions is None:
        raise HTTPException(503, "PostgreSQL is not ready. Start the database service and retry.")
    return db.sessions()


def audit(session, principal, action, resource):
    session.add(AuditEventRecord(tenant_id=principal.tenant_id, actor_id=principal.user_id,
        action=action, resource_type="advanced", resource_id=resource, outcome="success", metadata_json={}))


async def snapshot(principal):
    async with sessions() as session:
        rows = (await session.scalars(select(TelemetryRecord).where(
            TelemetryRecord.tenant_id == principal.tenant_id,
            TelemetryRecord.observed_at >= datetime.now(UTC) - timedelta(days=30)
        ).order_by(TelemetryRecord.observed_at.desc(), TelemetryRecord.id).limit(10000))).all()
    result = analyze([row.payload for row in rows])
    result["window"] = "Latest 10,000 events within 30 days"
    return result


@router.post("/telemetry", status_code=201)
async def ingest(payload: TelemetryBatch, principal: Writer):
    created_events = []
    async with sessions() as session:
        inserted = 0
        for event in payload.events:
            data = event.model_dump(mode="json")
            data["observed_at"] = event.observed_at.astimezone(UTC).isoformat()
            result = await session.execute(insert(TelemetryRecord).values(tenant_id=principal.tenant_id,
                id=event.id, entity=event.entity, metric=event.metric, observed_at=event.observed_at,
                payload=data).on_conflict_do_nothing().returning(TelemetryRecord.id))
            inserted += result.scalar_one_or_none() is not None
        audit(session, principal, "telemetry.ingest", str(inserted))
        await session.commit()
    # Replayed batches also repair any alert materialization interrupted after ingestion.
    analysis = await snapshot(principal)
    created = 0
    async with sessions() as session:
        for item in analysis["anomalies"]:
            result = await session.execute(insert(OperationalAlertRecord).values(
                tenant_id=principal.tenant_id, dedupe_key=f"anomaly:{item['id']}",
                title=f"Unusual {item['metric']} on {item['entity']}", severity=item["severity"],
                score=round(item["score"]), evidence={"source": "behavioral-telemetry", "model": analysis["model"], **item}
            ).on_conflict_do_nothing().returning(OperationalAlertRecord.id))
            if result.scalar_one_or_none() is not None:
                created += 1
                created_events.append({"title": f"Unusual {item['metric']} on {item['entity']}", "severity": item["severity"], "score": round(item["score"]), "evidence": item})
        await session.commit()
    from app.services.webhooks import webhook_service
    for event in created_events:
        await webhook_service.dispatch(principal.tenant_id, "alert.created", event["severity"], event)
    return {"inserted": inserted, "duplicates": len(payload.events) - inserted, "created_alerts": created}


@router.get("/detection/overview")
async def detection(principal: Reader):
    return await snapshot(principal)


@router.get("/marketplace")
async def marketplace(principal: Reader):
    async with sessions() as session:
        installed = {row.id: row for row in (await session.scalars(select(ExtensionRecord).where(ExtensionRecord.tenant_id == principal.tenant_id))).all()}
    return {"can_manage": principal.role == Role.ADMIN, "can_run": principal.role != Role.VIEWER,
        "plugins": [{**item, "publisher": "DarkTrace X", "installed": item["id"] in installed,
            "enabled": installed[item["id"]].enabled if item["id"] in installed else False} for item in CATALOG]}


class PluginState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


def manifest(plugin_id):
    item = next((item for item in CATALOG if item["id"] == plugin_id), None)
    if item is None:
        raise HTTPException(404, "Plugin not found")
    return item


@router.put("/marketplace/{plugin_id}")
async def install(plugin_id: str, payload: PluginState, principal: Admin):
    manifest(plugin_id)
    async with sessions() as session:
        await session.execute(insert(ExtensionRecord).values(tenant_id=principal.tenant_id, id=plugin_id,
            enabled=payload.enabled).on_conflict_do_update(index_elements=["tenant_id", "id"], set_={"enabled": payload.enabled}))
        audit(session, principal, "plugin.enable" if payload.enabled else "plugin.disable", plugin_id)
        await session.commit()
    return {"id": plugin_id, "enabled": payload.enabled}


@router.delete("/marketplace/{plugin_id}", status_code=204)
async def uninstall(plugin_id: str, principal: Admin):
    manifest(plugin_id)
    async with sessions() as session:
        row = await session.get(ExtensionRecord, (principal.tenant_id, plugin_id))
        if row:
            await session.delete(row)
            audit(session, principal, "plugin.uninstall", plugin_id)
            await session.commit()
    return Response(status_code=204)


@router.post("/marketplace/{plugin_id}/run")
async def run_plugin(plugin_id: str, principal: Writer):
    manifest(plugin_id)
    async with sessions() as session:
        row = await session.get(ExtensionRecord, (principal.tenant_id, plugin_id))
        if not row or not row.enabled:
            raise HTTPException(409, "Install and enable this plugin before running it")
        result = await snapshot(principal)
        audit(session, principal, "plugin.run", plugin_id)
        await session.commit()
    if plugin_id == "behavior-analyzer":
        return {"anomalies": result["anomalies"], "model": result["model"]}
    if plugin_id == "threat-forecast":
        return {"predictions": result["predictions"], "limitations": result["limitations"]}
    return {key: result[key] for key in ("event_count", "baseline_ready", "learning", "last_observed_at", "window", "limitations")}


TOOLS = [{"name": name, "description": description,
    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}}
    for name, description in [("anomaly_summary", "Read tenant behavioral anomalies."),
        ("threat_forecast", "Read tenant risk forecasts and their limitations."),
        ("telemetry_health", "Read tenant baseline readiness.")]]


@router.get("/mcp/servers")
async def mcp_servers(principal: Reader):
    return {"servers": [{"id": "darktracex", "name": "DarkTrace X Intelligence", "endpoint": "/api/v1/mcp",
        "transport": "Streamable HTTP", "protocol": "2025-11-25", "authentication": "Bearer token required",
        "tools": TOOLS, "status": "available"}]}


async def mcp_identity(request: Request, principal: Reader):
    if not request.headers.get("authorization", "").lower().startswith("bearer "):
        raise HTTPException(401, "MCP requires a bearer token, including in development")
    origin = request.headers.get("origin")
    if origin and origin not in get_settings().cors_origin_list:
        raise HTTPException(403, "Origin is not allowed")
    if request.headers.get("mcp-protocol-version", "2025-11-25") not in ("2025-03-26", "2025-06-18", "2025-11-25"):
        raise HTTPException(400, "Unsupported MCP protocol version")
    return principal


@router.get("/mcp")
async def mcp_stream(principal: Annotated[Principal, Depends(mcp_identity)]):
    return Response(status_code=405, headers={"Allow": "POST"})


@router.post("/mcp")
async def mcp_rpc(request: Request, principal: Annotated[Principal, Depends(mcp_identity)]):
    def error(code, message, ident=None):
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": message}}
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 65536:
            raise HTTPException(413, "MCP request exceeds 64 KiB")
    try:
        body = json.loads(raw)
    except ValueError:
        return error(-32700, "Parse error")
    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0" or not isinstance(body.get("method"), str):
        return error(-32600, "Invalid request")
    ident, method, params = body.get("id"), body["method"], body.get("params", {})
    if "id" not in body:
        return Response(status_code=202)
    if not isinstance(ident, (str, int)) or isinstance(ident, bool) or not isinstance(params, dict):
        return error(-32600, "Invalid request")
    if method == "initialize":
        result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "DarkTrace X Intelligence", "version": "1.0.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        name = params.get("name")
        if name not in {tool["name"] for tool in TOOLS} or params.get("arguments", {}) != {}:
            return error(-32602, "Unknown tool or invalid arguments", ident)
        try:
            data = await snapshot(principal)
        except HTTPException:
            result = {"content": [{"type": "text", "text": "Telemetry storage is unavailable."}], "isError": True}
        else:
            keys = {"anomaly_summary": ("anomalies", "model", "limitations"), "threat_forecast": ("predictions", "limitations"), "telemetry_health": ("event_count", "baseline_ready", "learning")}[name]
            result = {"content": [{"type": "text", "text": json.dumps({key: data[key] for key in keys})}], "isError": False}
    else:
        return error(-32601, "Method not found", ident)
    return {"jsonrpc": "2.0", "id": ident, "result": result}
