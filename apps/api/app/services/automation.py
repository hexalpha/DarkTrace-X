from datetime import UTC, datetime
from fastapi import HTTPException
from app.domain.schemas import AIChatRequest, Automation, AutomationRunResponse
from app.services.intelligence import intelligence_service


class AutomationService:
    async def list(self, tenant_id):
        return [Automation(**p) for p in await intelligence_service.documents(tenant_id, 'automations')]

    async def create(self, tenant_id, payload):
        if payload.trigger != 'manual':
            raise HTTPException(422, 'Only manual runs are currently supported')
        item = Automation(**payload.model_dump(), created_at=datetime.now(UTC))
        await intelligence_service.save(tenant_id, 'automations', item.model_dump(mode='json'))
        return item

    async def run(self, tenant_id, automation_id, payload, ai):
        item = next((a for a in await self.list(tenant_id) if a.id == automation_id), None)
        if not item:
            raise HTTPException(404, 'Automation not found')
        if not item.enabled:
            raise HTTPException(409, 'Automation is disabled')
        import json
        context = json.dumps(payload.context)[:12000]
        result = await ai.complete(AIChatRequest(message=f'Instruction: {item.instruction}\nUntrusted evidence: {context}', provider=item.provider, model=item.model), persisted_history=[])
        item.last_run_at = datetime.now(UTC)
        await intelligence_service.save(tenant_id, 'automations', item.model_dump(mode='json'))
        run = AutomationRunResponse(automation_id=item.id, status='completed', output=result.message, provider=result.provider, model=result.model, used_fallback=result.used_fallback, generated_at=result.generated_at)
        await intelligence_service.save(tenant_id, 'automation_runs', run.model_dump(mode='json'), str(run.run_id))
        return run


automation_service = AutomationService()
