import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from app.services import copilot_store as store
from app.services.copilot_tools import health
from app.services.intelligence import session
from app.storage.models import CopilotRecord, OperationalAlertRecord


async def notifications(p):
    # Transaction-scoped lock serializes the whole per-user cooldown decision.
    lock_id = int.from_bytes(hashlib.sha256(f'{p.tenant_id}:{p.user_id}:notifications'.encode()).digest()[:8], 'big', signed=True)
    async with session() as db:
        await db.execute(text("SET LOCAL lock_timeout = '3s'"))
        await db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key':lock_id})
        return await generate_notifications(p)


async def generate_notifications(p):
    now = datetime.now(UTC)
    async with session() as db:
        alerts = (await db.scalars(select(OperationalAlertRecord).where(OperationalAlertRecord.tenant_id==p.tenant_id,
            OperationalAlertRecord.status.not_in(['resolved','false_positive']), OperationalAlertRecord.severity.in_(['high','critical'])
        ).order_by(OperationalAlertRecord.created_at.desc()).limit(20))).all()
    candidates = [{'id':a.id,'alert_id':a.id,'group':str(a.evidence.get('source','operational-alert')),'title':a.title,'severity':a.severity.upper(),'observed_at':a.created_at.isoformat()} for a in alerts]
    status = await health()
    for name, value in status['services'].items():
        previous_state = await store.get(p,'service_state',name)
        if not previous_state or previous_state.get('state') != value:
            previous_state = {'state':value,'since':now.isoformat()}
            await store.put(p,'service_state',name,previous_state)
        if value == 'OFFLINE':
            candidates.append({'id':'health-'+name+previous_state['since'], 'group':'health-'+name,'title':name+' connection failed','severity':'HIGH','observed_at':now.isoformat()})
    prefs = await store.get(p,'preferences','default') or {}
    muted = prefs.get('muted_groups', [])
    previous = await store.listing(p,'notification',100)
    recent = [n for n in previous if n.get('created_at','') > (now-timedelta(hours=1)).isoformat()]
    created = 0
    for event in candidates:
        ident = hashlib.sha256(event['id'].encode()).hexdigest()
        if event['group'] in muted or any(n['id']==ident for n in previous):
            continue
        if len(recent)+created >= 3 or any(n.get('group')==event['group'] and n.get('created_at','')>(now-timedelta(minutes=10)).isoformat() for n in previous):
            continue
        data = {**event,'id':ident,'state':'new','created_at':now.isoformat(),'mode':'LIVE'}
        async with session() as db:
            await db.execute(insert(CopilotRecord).values(tenant_id=p.tenant_id,user_id=p.user_id,kind='notification',id=ident,payload=store.redact(data)).on_conflict_do_nothing())
            await db.commit()
        created += 1
    if created:
        await store.audit(p,'alerts.generated',{'count':created})
    return await store.listing(p,'notification',100)
