import asyncio
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.v1.routes import router as v1_router
from app.core.config import get_settings
from app.graphql import graphql_router
from app.observability import LATENCY, REQUESTS

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB pools, Redis clients, search clients, and worker consumers here.
    yield
    # Close clients with bounded timeouts here.


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
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def secure_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - started
    route = request.scope.get("route")
    route_path = getattr(route, "path", request.url.path)
    REQUESTS.labels(request.method, route_path, response.status_code).inc()
    LATENCY.labels(request.method, route_path).observe(duration)
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
    """Replace the sample pulse with Redis Streams consumer groups and tenant topic checks."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"type": "telemetry.pulse", "events_per_minute": 1824, "at": int(time.time())})
            await asyncio.sleep(12)
    except WebSocketDisconnect:
        return


app.include_router(v1_router, prefix=settings.api_v1_prefix)
app.include_router(graphql_router, prefix="/graphql")

