from prometheus_client import Counter, Histogram

REQUESTS = Counter("darktracex_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("darktracex_http_request_duration_seconds", "HTTP request latency", ["method", "path"])
AI_REQUESTS = Counter("darktracex_ai_requests_total", "AI completion attempts", ["provider", "outcome"])
COPILOT_EVENTS = Counter("darktracex_copilot_events_total", "Copilot audited events", ["action"])
COPILOT_LATENCY = Histogram("darktracex_copilot_inference_seconds", "Completed copilot request latency", ["provider"])
COPILOT_TOKENS = Counter("darktracex_copilot_reported_tokens_total", "Provider-reported tokens; unavailable usage is not estimated", ["provider"])
