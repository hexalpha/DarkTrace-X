import logging
import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from elasticsearch import AsyncElasticsearch

from app.core.config import Settings

logger = logging.getLogger(__name__)


class SearchService:
    IOC_INDEX = "darktracex-iocs"
    ACTOR_INDEX = "darktracex-actors"

    def __init__(self, settings: Settings) -> None:
        self.client: AsyncElasticsearch | None = None
        self.ready = False
        try:
            auth = None
            if settings.elasticsearch_username and settings.elasticsearch_password:
                auth = (settings.elasticsearch_username, settings.elasticsearch_password.get_secret_value())
            self.client = AsyncElasticsearch(settings.elasticsearch_url, basic_auth=auth, verify_certs=True,
                ca_certs=settings.elasticsearch_ca_certs, request_timeout=5, retry_on_timeout=True, max_retries=2)
        except Exception as exc:
            logger.warning("Elasticsearch client unavailable: %s", exc.__class__.__name__)

    async def connect(self) -> None:
        if self.client is None:
            return
        try:
            if not await self.client.ping():
                return
            await self._ensure_indexes()
            self.ready = True
        except Exception as exc:
            logger.warning("Elasticsearch unavailable: %s", exc.__class__.__name__)
            self.ready = False

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()

    async def _ensure_indexes(self) -> None:
        assert self.client is not None
        mappings = {
            "properties": {
                "tenant_id": {"type": "keyword"}, "indicator_type": {"type": "keyword"}, "value": {"type": "keyword"},
                "tags": {"type": "keyword"}, "source": {"type": "keyword"}, "confidence": {"type": "integer"},
                "risk_score": {"type": "integer"}, "observed_at": {"type": "date"}, "evidence": {"type": "flattened"},
            }
        }
        if not await self.client.indices.exists(index=self.IOC_INDEX):
            await self.client.indices.create(index=self.IOC_INDEX, mappings=mappings)
        actor_mappings = {"properties": {"tenant_id": {"type": "keyword"}, "name": {"type": "keyword"}, "aliases": {"type": "keyword"}, "techniques": {"type": "keyword"}, "targeting": {"type": "keyword"}, "sources": {"type": "keyword"}, "summary": {"type": "text"}, "updated_at": {"type": "date"}}}
        if not await self.client.indices.exists(index=self.ACTOR_INDEX):
            await self.client.indices.create(index=self.ACTOR_INDEX, mappings=actor_mappings)

    async def _require(self) -> AsyncElasticsearch:
        if not self.ready:
            await self.connect()
        if not self.ready or self.client is None:
            raise RuntimeError("Elasticsearch is not ready")
        return self.client

    async def index_ioc(self, tenant_id: str, indicator_type: str, value: str, confidence: int, risk_score: int, tags: list[str], source: str, evidence: dict[str, str]) -> dict:
        client = await self._require()
        from app.services.intelligence import intelligence_service
        from app.domain.schemas import IndicatorType
        value = intelligence_service._validate_observable(IndicatorType(indicator_type), value)
        document = {"tenant_id": tenant_id, "indicator_type": indicator_type, "value": value, "confidence": confidence, "risk_score": risk_score, "tags": sorted(set(tags)), "source": source, "evidence": evidence, "observed_at": datetime.now(UTC).isoformat()}
        document_id = hashlib.sha256(f"{tenant_id}:{indicator_type}:{value}".encode()).hexdigest()
        await client.index(index=self.IOC_INDEX, id=document_id, document=document, refresh="wait_for")
        return {"id": document_id, **document}

    async def correlate_ioc(self, tenant_id: str, indicator_type: str, value: str) -> list[dict]:
        client = await self._require()
        from app.services.intelligence import intelligence_service
        from app.domain.schemas import IndicatorType
        value = intelligence_service._validate_observable(IndicatorType(indicator_type), value)
        response = await client.search(index=self.IOC_INDEX, size=100, query={"bool": {"filter": [{"term": {"tenant_id": tenant_id}}, {"term": {"indicator_type": indicator_type}}, {"term": {"value": value}}]}})
        return [{"id": item["_id"], **item["_source"]} for item in response["hits"]["hits"]]

    async def graph(self, tenant_id: str) -> dict:
        client = await self._require()
        response = await client.search(index=self.IOC_INDEX, size=500, query={"bool": {"filter": [{"term": {"tenant_id": tenant_id}}]}})
        nodes: list[dict] = []
        edges: list[dict] = []
        for hit in response["hits"]["hits"]:
            doc = hit["_source"]
            ioc_id = f"ioc:{hit['_id']}"
            nodes.append({"id": ioc_id, "type": "ioc", "label": doc["value"], "risk": doc["risk_score"]})
            for tag in doc.get("tags", []):
                tag_id = f"tag:{tag}"
                if not any(node["id"] == tag_id for node in nodes):
                    nodes.append({"id": tag_id, "type": "tag", "label": tag, "risk": 0})
                edges.append({"source": ioc_id, "target": tag_id, "relation": "tagged"})
        node_ids = {node["id"] for node in nodes}
        for actor in await self.list_actors(tenant_id):
            actor_id = f"actor:{actor['id']}"
            nodes.append({"id": actor_id, "type": "actor", "label": actor["name"], "risk": 0})
            for technique in actor.get("techniques", []):
                technique_id = f"technique:{technique}"
                if technique_id not in node_ids:
                    nodes.append({"id": technique_id, "type": "technique", "label": technique, "risk": 0})
                    node_ids.add(technique_id)
                edges.append({"source": actor_id, "target": technique_id, "relation": "reported_technique"})
        # Only persisted observations create source-entity relationships.
        from sqlalchemy import select
        from app.services.intelligence import session
        from app.storage.models import EntityObservationRecord, IntelligenceEntityRecord, SourceDocumentRecord, ThreatEventRecord, OperationalAlertRecord
        async with session() as db:
            observations=(await db.scalars(select(EntityObservationRecord).where(EntityObservationRecord.tenant_id==tenant_id).order_by(EntityObservationRecord.observed_at.desc()).limit(300))).all()
            entities={e.id:e for e in (await db.scalars(select(IntelligenceEntityRecord).where(IntelligenceEntityRecord.tenant_id==tenant_id,IntelligenceEntityRecord.id.in_([o.entity_id for o in observations])))).all()}
            documents={d.id:d for d in (await db.scalars(select(SourceDocumentRecord).where(SourceDocumentRecord.tenant_id==tenant_id,SourceDocumentRecord.id.in_([o.document_id for o in observations])))).all()}
            known={n['id'] for n in nodes}
            for observation in observations:
                entity=entities.get(observation.entity_id)
                document=documents.get(observation.document_id)
                if not entity or not document:
                    continue
                doc_id='document:'+document.id; entity_id='entity:'+entity.id
                for ident,kind,label in ((doc_id,'document',document.title),(entity_id,entity.entity_type,entity.value)):
                    if ident not in known:
                        nodes.append({'id':ident,'type':kind,'label':label,'risk':0});known.add(ident)
                edges.append({'source':doc_id,'target':entity_id,'relation':'document.contains_entity','confidence':observation.confidence,
                    'source_id':observation.source_id,'document_id':document.id,'first_seen':entity.first_seen.isoformat(),'last_seen':entity.last_seen.isoformat()})
            events=(await db.scalars(select(ThreatEventRecord).where(ThreatEventRecord.tenant_id==tenant_id).order_by(ThreatEventRecord.created_at.desc()).limit(100))).all()
            for event in events:
                entity_id='entity:'+str(event.entity_id)
                if entity_id in known:
                    event_id='event:'+event.id
                    nodes.append({'id':event_id,'type':'event','label':event.event_type,'risk':0});known.add(event_id)
                    edges.append({'source':event_id,'target':entity_id,'relation':'event.observes_entity','confidence':event.confidence,
                        'source_id':event.source_id,'document_id':event.document_id,'first_seen':event.created_at.isoformat(),'last_seen':event.created_at.isoformat()})
            alerts=(await db.scalars(select(OperationalAlertRecord).where(OperationalAlertRecord.tenant_id==tenant_id).order_by(OperationalAlertRecord.created_at.desc()).limit(100))).all()
            for alert in alerts:
                event_id='event:'+str(alert.evidence.get('event_id',''))
                if event_id in known:
                    ident='alert:'+alert.id;nodes.append({'id':ident,'type':'alert','label':alert.title,'risk':alert.score})
                    edges.append({'source':ident,'target':event_id,'relation':'alert.derived_from_event','confidence':100,
                        'source_id':alert.evidence.get('source_id'),'document_id':alert.evidence.get('document_id'),
                        'first_seen':alert.created_at.isoformat(),'last_seen':alert.created_at.isoformat()})
        return {"nodes": nodes, "edges": edges, "generated_at": datetime.now(UTC).isoformat()}

    async def upsert_actor(self, tenant_id: str, payload: dict) -> dict:
        client = await self._require()
        document = {**payload, "tenant_id": tenant_id, "updated_at": datetime.now(UTC).isoformat()}
        actor_id = hashlib.sha256(f"{tenant_id}:{payload['name'].casefold()}".encode()).hexdigest()
        await client.index(index=self.ACTOR_INDEX, id=actor_id, document=document, refresh="wait_for")
        return {"id": actor_id, **document}

    async def list_actors(self, tenant_id: str) -> list[dict]:
        client = await self._require()
        response = await client.search(index=self.ACTOR_INDEX, size=200, query={"bool": {"filter": [{"term": {"tenant_id": tenant_id}}]}}, sort=[{"updated_at": "desc"}])
        return [{"id": item["_id"], **item["_source"]} for item in response["hits"]["hits"]]


search_service: SearchService | None = None


def configure_search(settings: Settings) -> SearchService:
    global search_service
    search_service = SearchService(settings)
    return search_service
