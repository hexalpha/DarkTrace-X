from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.config import Settings, get_settings
from app.core.security import Principal, Role, current_principal, require_role
from app.domain.schemas import AIChatRequest, AIChatResponse, Alert, CVEIntel, DashboardOverview, ExposureMention, IOC, IOCCreate, ReportRequest, ReportSchedule, Severity, WebhookSubscription, YaraRule
from app.observability import AI_REQUESTS
from app.services.ai import AIProviderUnavailable, AIRouter
from app.services.intelligence import intelligence_service
from app.services.reports import report_service
from app.plugins.registry import plugin_registry

router = APIRouter()


@lru_cache
def get_ai_router() -> AIRouter:
    """Process-local development memory; production swaps this seam for encrypted persistence."""
    return AIRouter(get_settings())


def ai_router() -> AIRouter:
    return get_ai_router()


@router.get("/health/live", tags=["Platform"])
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", tags=["Platform"])
async def readiness() -> dict[str, str]:
    # Replace with bounded DB, Redis, and search readiness probes in live deployments.
    return {"status": "ready"}


@router.get("/dashboard/overview", response_model=DashboardOverview, tags=["Dashboard"])
async def dashboard(principal: Annotated[Principal, Depends(current_principal)]) -> DashboardOverview:
    return intelligence_service.overview(principal.tenant_id)


@router.get("/iocs", response_model=list[IOC], tags=["Threat Intelligence"])
async def list_iocs(
    principal: Annotated[Principal, Depends(current_principal)],
    q: str | None = Query(default=None, max_length=256),
) -> list[IOC]:
    return intelligence_service.list_iocs(principal.tenant_id, q)


@router.post("/iocs", response_model=IOC, status_code=status.HTTP_201_CREATED, tags=["Threat Intelligence"])
async def create_ioc(
    payload: IOCCreate,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST, Role.LEAD, Role.ADMIN))],
) -> IOC:
    return intelligence_service.create_ioc(principal.tenant_id, payload)


@router.get("/alerts", response_model=list[Alert], tags=["Alerts"])
async def list_alerts(
    principal: Annotated[Principal, Depends(current_principal)],
    severity: Severity | None = None,
) -> list[Alert]:
    return intelligence_service.list_alerts(principal.tenant_id, severity)


@router.get("/cves", response_model=list[CVEIntel], tags=["Vulnerability Intelligence"])
async def list_cves(principal: Annotated[Principal, Depends(current_principal)]) -> list[CVEIntel]:
    return intelligence_service.cves()


@router.get("/ai/providers", tags=["AI SOC Assistant"])
async def list_ai_providers(
    principal: Annotated[Principal, Depends(current_principal)],
    assistant: Annotated[AIRouter, Depends(ai_router)],
) -> dict[str, object]:
    return {"default": assistant.settings.ai_default_provider, "providers": assistant.enabled_providers()}


@router.post("/ai/chat", response_model=AIChatResponse, tags=["AI SOC Assistant"])
async def chat_with_soc_assistant(
    payload: AIChatRequest,
    principal: Annotated[Principal, Depends(current_principal)],
    assistant: Annotated[AIRouter, Depends(ai_router)],
) -> AIChatResponse:
    try:
        result = await assistant.complete(payload)
        AI_REQUESTS.labels(result.provider, "success").inc()
        return result
    except AIProviderUnavailable as exc:
        for provider in exc.attempted:
            AI_REQUESTS.labels(provider, "failed").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "No configured AI provider is available. Check the model panel or retry later.", "attempted": exc.attempted},
        ) from exc


@router.post("/integrations/webhooks", status_code=status.HTTP_202_ACCEPTED, tags=["Integrations"])
async def register_webhook(
    payload: WebhookSubscription,
    principal: Annotated[Principal, Depends(require_role(Role.ADMIN))],
) -> dict[str, object]:
    # Persist an encrypted signing secret and enqueue a verification challenge in the worker service.
    return {"id": str(uuid4()), "name": payload.name, "status": "verification_pending", "created_at": datetime.now(UTC)}


@router.get("/exposure/mentions", response_model=list[ExposureMention], tags=["Exposure Intelligence"])
async def exposure_mentions(principal: Annotated[Principal, Depends(current_principal)]) -> list[ExposureMention]:
    return [
        ExposureMention(monitored_term="northstar.example", source_type="approved breach intelligence feed", confidence=91, summary="A newly observed reference matched the protected brand term; analyst review required.", observed_at=datetime.now(UTC), legal_basis="licensed intelligence subscription"),
        ExposureMention(monitored_term="Northstar Global", source_type="public forum monitoring", confidence=63, summary="Public discussion volume increased; no credential material collected or retained.", observed_at=datetime.now(UTC), legal_basis="publicly accessible source within terms"),
    ]


@router.get("/yara-rules", response_model=list[YaraRule], tags=["Threat Intelligence"])
async def list_yara_rules(principal: Annotated[Principal, Depends(current_principal)]) -> list[YaraRule]:
    return [YaraRule(name="DarkTraceX_Suspicious_Loader", namespace="global", rule="rule DarkTraceX_Suspicious_Loader { strings: $a = \"loader\" nocase condition: $a }", enabled=True, updated_at=datetime.now(UTC))]


@router.get("/plugins", tags=["Extensibility"])
async def list_plugins(principal: Annotated[Principal, Depends(current_principal)]) -> dict[str, object]:
    return {"plugins": [manifest.__dict__ for manifest in plugin_registry.manifests()]}


@router.post("/reports/{format_name}", tags=["Reporting"])
async def export_report(
    format_name: str,
    payload: ReportRequest,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST, Role.LEAD, Role.ADMIN))],
) -> Response:
    try:
        media_type, filename, body = report_service.render(principal.tenant_id, format_name, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(body, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/reports/schedules", status_code=status.HTTP_202_ACCEPTED, tags=["Reporting"])
async def schedule_report(
    payload: ReportSchedule,
    principal: Annotated[Principal, Depends(require_role(Role.LEAD, Role.ADMIN))],
) -> dict[str, object]:
    # Persist schedule after cron validation; the worker signs and sends reports using tenant policy.
    return {"id": str(uuid4()), "name": payload.name, "status": "scheduled", "created_at": datetime.now(UTC)}
