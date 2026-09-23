import hashlib
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
import jwt
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.api.v1.advanced import Admin, Reader, Writer, audit, sessions
from app.api.v1.routes import operations, search
from app.core.config import get_settings
from app.domain.schemas import AssetRecord
from app.services.intelligence import intelligence_service
from app.storage.models import IntelligenceRecord, KeywordMonitorRecord, OperationalAlertRecord, RevokedTokenRecord

router = APIRouter(tags=["Workspace Operations"])


@router.get('/documents/{ident}')
async def document_detail(ident: str, principal: Reader):
    from app.storage.models import SourceDocumentRecord, EntityObservationRecord, IntelligenceEntityRecord, ThreatEventRecord
    async with sessions() as db:
        row=await db.get(SourceDocumentRecord,(principal.tenant_id,ident))
        if not row:
            raise HTTPException(404,'Document not found')
        observations=(await db.scalars(select(EntityObservationRecord).where(EntityObservationRecord.tenant_id==principal.tenant_id,EntityObservationRecord.document_id==ident))).all()
        entity_ids=[o.entity_id for o in observations]
        entities=(await db.scalars(select(IntelligenceEntityRecord).where(IntelligenceEntityRecord.tenant_id==principal.tenant_id,IntelligenceEntityRecord.id.in_(entity_ids)))).all() if entity_ids else []
        events=(await db.scalars(select(ThreatEventRecord).where(ThreatEventRecord.tenant_id==principal.tenant_id,ThreatEventRecord.document_id==ident).limit(500))).all()
        alerts=(await db.scalars(select(OperationalAlertRecord).where(OperationalAlertRecord.tenant_id==principal.tenant_id,OperationalAlertRecord.evidence['document_id'].as_string()==ident).limit(100))).all()
        return {'id':row.id,'title':row.title,'source_id':row.source_id,'crawl_id':row.crawl_id,'canonical_url':row.canonical_url,
                'normalized_text':row.normalized_text,'published_at':row.published_at,'collected_at':row.collected_at,
                'content_hash':row.content_hash,'metadata':row.metadata_json,
                'entities':[{'id':e.id,'type':e.entity_type,'value':e.value,'confidence':e.confidence} for e in entities],
                'events':[{'id':e.id,'type':e.event_type,'severity':e.severity,'status':e.status} for e in events],
                'alerts':[{'id':a.id,'title':a.title,'status':a.status,'score':a.score} for a in alerts]}


@router.get('/documents/{ident}/raw')
async def document_raw(ident: str, principal: Reader):
    from app.storage.models import SourceDocumentRecord
    async with sessions() as db:
        row=await db.get(SourceDocumentRecord,(principal.tenant_id,ident))
        if not row:
            raise HTTPException(404,'Document not found')
        return Response(row.raw_content,media_type='text/plain',headers={'Content-Disposition':'attachment; filename="source-document.txt"'})


@router.get('/health/components')
async def component_health(request: Request, principal: Reader):
    from app.services.copilot_tools import health
    result=await health()
    scheduler=getattr(request.app.state,'source_scheduler',None)
    worker=getattr(request.app.state,'delivery_worker',None)
    result['scheduler']='ONLINE' if scheduler and scheduler._task and not scheduler._task.done() else 'OFFLINE'
    result['delivery_worker']={'state':'ONLINE' if worker and worker.task and not worker.task.done() else 'OFFLINE','last_success':worker.last_success if worker else None}
    return result


@router.get('/deliveries')
async def deliveries(principal: Admin):
    from app.storage.models import DeliveryJobRecord
    async with sessions() as db:
        rows=(await db.scalars(select(DeliveryJobRecord).where(DeliveryJobRecord.tenant_id==principal.tenant_id).order_by(DeliveryJobRecord.created_at.desc()).limit(100))).all()
        return [{'id':r.id,'kind':r.kind,'target_id':r.target_id,'status':r.status,'attempts':r.attempts,
                 'next_attempt_at':r.next_attempt_at,'last_error':r.last_error,'created_at':r.created_at,
                 'artifact_available':bool(r.kind=='report' and r.result.get('body'))} for r in rows]


@router.get('/deliveries/{ident}/artifact')
async def delivery_artifact(ident: str, principal: Admin):
    import base64
    from app.storage.models import DeliveryJobRecord
    async with sessions() as db:
        row=await db.scalar(select(DeliveryJobRecord).where(DeliveryJobRecord.tenant_id==principal.tenant_id,DeliveryJobRecord.id==ident,DeliveryJobRecord.kind=='report'))
        if not row or not row.result.get('body'):
            raise HTTPException(404,'Report artifact unavailable')
        return Response(base64.b64decode(row.result['body']),media_type=row.result['media_type'],headers={'Content-Disposition':'attachment; filename="'+row.result['filename']+'"'})


@router.get("/auth/me")
async def me(principal: Reader):
    return principal


@router.post("/auth/logout", status_code=204)
async def logout(request: Request, principal: Reader):
    token = request.headers["authorization"].split(" ", 1)[1] if request.headers.get("authorization") else request.cookies["dtx_access"]
    digest = hashlib.sha256(token.encode()).hexdigest()
    claims = jwt.decode(token, get_settings().jwt_secret.get_secret_value(), algorithms=['HS256'], audience='darktracex-api', issuer='darktracex')
    expires = datetime.fromtimestamp(claims["exp"], UTC)
    async with sessions() as db:
        await db.execute(insert(RevokedTokenRecord).values(digest=digest, expires_at=expires).on_conflict_do_nothing())
        audit(db, principal, "auth.logout", principal.user_id)
        await db.commit()
    response = Response(status_code=204)
    from app.services.browser_sessions import revoke
    await revoke(request, response)
    return response


@router.post('/auth/refresh', status_code=204)
async def refresh(request: Request):
    from app.services.browser_sessions import rotate
    response = Response(status_code=204)
    await rotate(request, response, get_settings())
    return response


class AssetCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=253)
    owner: str = Field(min_length=1, max_length=160)
    exposure: Literal["internal", "internet"] = "internal"
    criticality: Literal["low", "medium", "high", "critical"] = "medium"
    risk_score: int = Field(ge=0, le=100, default=0)
    services: list[str] = Field(default_factory=list, max_length=30)


@router.post("/assets", response_model=AssetRecord, status_code=201)
async def create_asset(payload: AssetCreate, principal: Writer):
    item = AssetRecord(**payload.model_dump(), last_seen=datetime.now(UTC))
    await intelligence_service.save(principal.tenant_id, "assets", item.model_dump(mode="json"))
    return item


class AlertUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["open", "triage", "investigating", "resolved", "false_positive"]


@router.patch("/operational-alerts/{alert_id}")
async def update_alert(alert_id: str, payload: AlertUpdate, principal: Writer):
    async with sessions() as db:
        item = await db.scalar(select(OperationalAlertRecord).where(OperationalAlertRecord.id == alert_id, OperationalAlertRecord.tenant_id == principal.tenant_id).with_for_update())
        if not item:
            raise HTTPException(404, "Alert not found")
        item.status = payload.status
        audit(db, principal, "alert.status_changed", alert_id)
        await db.commit()
    return {"id": alert_id, "status": payload.status}


@router.delete("/monitors/keywords/{monitor_id}", status_code=204)
async def delete_monitor(monitor_id: str, principal: Writer):
    async with sessions() as db:
        item = await db.scalar(select(KeywordMonitorRecord).where(KeywordMonitorRecord.id == monitor_id, KeywordMonitorRecord.tenant_id == principal.tenant_id))
        if not item:
            raise HTTPException(404, "Monitor not found")
        await db.delete(item)
        audit(db, principal, "monitor.deleted", monitor_id)
        await db.commit()
    return Response(status_code=204)


class SourceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=512)
    summary: str = Field(min_length=1, max_length=12000)
    source_url: HttpUrl
    observed_at: AwareDatetime


class SourceBatch(BaseModel):
    source: str = Field(min_length=2, max_length=100)
    source_type: Literal["licensed_dark_web", "public_web", "internal"]
    legal_basis: str = Field(min_length=5, max_length=500)
    items: list[SourceItem] = Field(min_length=1, max_length=200)


@router.post("/exposure/ingest", status_code=201)
async def ingest_exposure(payload: SourceBatch, principal: Writer):
    inserted, matches = 0, 0
    created_events = []
    async with sessions() as db:
        monitors = (await db.scalars(select(KeywordMonitorRecord).where(KeywordMonitorRecord.tenant_id == principal.tenant_id, KeywordMonitorRecord.enabled.is_(True)))).all()
        for item in payload.items:
            ident = hashlib.sha256(f"{payload.source}:{item.external_id}".encode()).hexdigest()
            result = await db.execute(insert(IntelligenceRecord).values(tenant_id=principal.tenant_id, collection="source_items", id=ident, payload={**item.model_dump(mode="json"), "source": payload.source, "source_type": payload.source_type}).on_conflict_do_nothing().returning(IntelligenceRecord.id))
            inserted += result.scalar_one_or_none() is not None
            for monitor in monitors:
                if monitor.term.casefold() not in f"{item.title} {item.summary}".casefold():
                    continue
                key = f"mention:{ident}:{monitor.id}"
                evidence = {"source": payload.source, "source_type": payload.source_type, "source_url": str(item.source_url), "external_id": item.external_id, "monitored_term": monitor.term, "legal_basis": payload.legal_basis, "summary": item.summary[:3000], "observed_at": item.observed_at.isoformat()}
                result = await db.execute(insert(OperationalAlertRecord).values(tenant_id=principal.tenant_id, dedupe_key=key, title=f"Keyword '{monitor.term}' matched: {item.title}"[:512], severity="medium", score=50, evidence=evidence).on_conflict_do_nothing().returning(OperationalAlertRecord.id))
                if result.scalar_one_or_none():
                    matches += 1
                    created_events.append({"title": f"Keyword '{monitor.term}' matched: {item.title}"[:512], "severity": "medium", "score": 50, "evidence": evidence})
                await db.execute(insert(IntelligenceRecord).values(tenant_id=principal.tenant_id, collection="mentions", id=hashlib.sha256(key.encode()).hexdigest(), payload={"id": ident, **evidence}).on_conflict_do_nothing())
        audit(db, principal, "exposure.ingested", payload.source)
        await db.commit()
    from app.services.webhooks import webhook_service
    for event in created_events:
        await webhook_service.dispatch(principal.tenant_id, "alert.created", event["severity"], event)
    return {"inserted": inserted, "created_alerts": matches, "received": len(payload.items)}


@router.get("/platform/status")
async def platform_status(principal: Reader):
    from app.storage.database import database
    from app.search.service import search_service
    settings = get_settings()
    return {"database": "ready" if database and database.ready else "unavailable", "search": "ready" if search_service and search_service.ready else "unavailable", "licensed_feed": "configured" if settings.approved_feed_url else "not_configured", "authentication": "required", "tenant": principal.tenant_id}


@router.post("/intelligence/reindex")
async def reindex(principal: Admin):
    items = await intelligence_service.list_iocs(principal.tenant_id)
    for item in items:
        await search().index_ioc(principal.tenant_id, item.type.value, item.value, item.confidence, item.risk_score, item.tags, item.source, {})
    return {"indexed": len(items)}
