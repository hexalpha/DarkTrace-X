import asyncio
import time
import logging
import re
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.v1.routes import router as v1_router
from app.api.v1.advanced import router as advanced_router
from app.api.v1.platform import router as platform_router
from app.api.v1.copilot import router as copilot_router
from app.core.config import get_settings
from app.graphql import graphql_router
from app.observability import LATENCY, REQUESTS
from app.storage.database import configure_database
from app.search.service import configure_search
from app.services.scheduler import SourceScheduler
from app.services.delivery_worker import DeliveryWorker

settings = get_settings()
from app.core.logging import configure_logging
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database = configure_database(settings)
    await database.connect()
    app.state.database_ready = database.ready
    search = configure_search(settings)
    await search.connect()
    app.state.search = search
    app.state.search_ready = search.ready
    scheduler = SourceScheduler(database, settings)
    app.state.source_scheduler = scheduler
    await scheduler.start()
    delivery = DeliveryWorker(database, settings)
    app.state.delivery_worker = delivery
    await delivery.start()
    yield
    await delivery.stop()
    await scheduler.stop()
    await search.close()
    await database.close()


app = FastAPI(
    title="DarkTrace X API",
    summary="Tenant-scoped defensive threat intelligence and AI SOC operations API",
    version="0.1.0",
    license_info={"name": "Proprietary / internal deployment"},
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "MCP-Protocol-Version", "X-CSRF-Token", "X-Browser-Session"],
)


@app.exception_handler(RequestValidationError)
async def safe_validation(request: Request, exc: RequestValidationError):
    if request.url.path.startswith(settings.api_v1_prefix + '/copilot'):
        return JSONResponse(status_code=422, content={'detail':[{'loc':e['loc'],'msg':e['msg'],'type':e['type']} for e in exc.errors()]})
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(IntegrityError)
async def duplicate_record(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "A conflicting record already exists. Refresh and retry."})


@app.exception_handler(SQLAlchemyError)
async def database_failure(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=503, content={"detail": "Database operation failed. Retry when storage is available."})


@app.middleware("http")
async def secure_request_context(request: Request, call_next):
    if request.url.path.startswith(settings.api_v1_prefix + '/copilot') and request.method in {'POST','PUT','PATCH'}:
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 32768:
                return JSONResponse(status_code=413, content={'detail':'Copilot request exceeds 32 KiB'})
        request._body = bytes(data)
    supplied_id = request.headers.get('X-Request-ID','')
    request_id = supplied_id if re.fullmatch(r'[A-Za-z0-9-]{1,64}',supplied_id) else str(uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - started
    route = request.scope.get("route")
    route_path = getattr(route, "path", "UNMATCHED")
    REQUESTS.labels(request.method, route_path, response.status_code).inc()
    LATENCY.labels(request.method, route_path).observe(duration)
    logger.info('http.request %s %s status=%s',request.method,route_path,response.status_code,
                extra={'request_id':request_id,'tenant_id':getattr(request.state,'tenant_id',None),'duration_ms':round(duration*1000)})
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.websocket("/ws/events")
async def event_stream(websocket: WebSocket) -> None:
    from app.core.security import validate_active_token
    from app.services.operations import OperationalService
    from app.storage import database as database_module
    from fastapi import HTTPException
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.cors_origin_list:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        # Token travels in an initial message, never in a logged URL.
        hello = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        token = hello.get("token", "") if isinstance(hello, dict) else ""
        if not token and websocket.cookies.get('dtx_access'):
            if not origin or origin not in settings.cors_origin_list:
                await websocket.close(code=1008)
                return
            token = websocket.cookies['dtx_access']
        while True:
            principal = await validate_active_token(token, settings)
            overview = await OperationalService(database_module.database).overview(principal)
            await websocket.send_json({"type": "telemetry.pulse", "events_per_minute": overview.event_rate, "at": int(time.time())})
            await asyncio.sleep(12)
    except (WebSocketDisconnect, RuntimeError):
        return
    except (HTTPException, ValueError, TimeoutError, TypeError):
        await websocket.close(code=1008)


app.include_router(v1_router, prefix=settings.api_v1_prefix)
app.include_router(advanced_router, prefix=settings.api_v1_prefix)
app.include_router(platform_router, prefix=settings.api_v1_prefix)
app.include_router(copilot_router, prefix=settings.api_v1_prefix)
app.include_router(graphql_router, prefix="/graphql")
