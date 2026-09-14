from prometheus_client import Counter, Histogram

REQUESTS = Counter("darktracex_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("darktracex_http_request_duration_seconds", "HTTP request latency", ["method", "path"])
AI_REQUESTS = Counter("darktracex_ai_requests_total", "AI completion attempts", ["provider", "outcome"])

