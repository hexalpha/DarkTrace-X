# Detection and extensions

The sidebar includes AI Anomalies, Threat Forecast, MCP Servers, and Marketplace. Restart the API after updating: its existing startup schema bootstrap creates `behavior_telemetry` and `tenant_extensions` in PostgreSQL. Existing records are preserved. No additional dependencies or AI provider keys are needed for these features.

## Telemetry and anomaly detection

POST `/api/v1/telemetry` with a bearer token for an analyst, lead, or administrator:

```json
{"events":[{"id":"sensor-a-001","entity":"server-01","metric":"failed_logins","value":2,"observed_at":"2026-09-14T08:00:00Z"}]}
```

Supported metrics: `failed_logins`, `outbound_bytes`, `dns_requests`, `process_count`. Send equal-duration buckets per entity/metric. A batch accepts up to 500 unique event IDs. Replays are ignored within the tenant; corrections require a new ID. Values must be finite and nonnegative; timestamps require a timezone and cannot exceed five minutes into the future.

GET `/api/v1/detection/overview` analyzes the latest 10,000 tenant events within 30 days. The first 20 earlier observations train a baseline. Each observation is compared with the median and median absolute deviation of up to 200 preceding observations, with a noise floor for constant baselines. Equal-time observations do not train each other. Upward deviations of at least 3.5 are findings; score = min(100, 10 × deviation). Responses include evidence IDs, baseline, sample count, severity, and review advice. No sample telemetry is inserted automatically.

This is an unsupervised statistical detector. It does not use an LLM or a pretrained attack classifier. It does not yet model seasonality, validate bucket duration or automatically ingest SIEM streams. Ingestion writes deduplicated findings into the persistent alert queue, where analysts can triage them. Scoring runs on refresh/import, not in a background worker. Review findings before taking action.

## Predictive threat engine

Forecasts require five scored observations during the last 24 hours. A smoothing factor of 0.3 tracks anomaly scores; the change between the two halves of the recent sequence increases priority when risk is rising. The 24-hour outlook is an extrapolated monitoring priority, not a calibrated attack probability. Evidence and limited/moderate confidence labels describe data coverage, not measured predictive accuracy. Validate against labeled production telemetry before relying on it for operational thresholds.

## Marketplace

GET `/api/v1/marketplace` lists three runnable, built-in extensions: Behavior Analyzer, Threat Forecast, and Telemetry Quality. They use tenant telemetry with no network egress or downloaded code.

Administrators install or enable using PUT `/api/v1/marketplace/{id}` with `{"enabled":true}`; disable with false; DELETE uninstalls. Analysts, leads and administrators can POST `/api/v1/marketplace/{id}/run` after installation. Disabled/uninstalled extensions return 409. Changes, runs and ingestion create persistent audit events. `/plugins` also returns the same actual marketplace inventory.

This is a curated local marketplace, not a third-party package installation service. Publisher text identifies bundled source; it does not claim cryptographic verification. Future third-party extensions require separate signing, sandboxing and review work.

## MCP

The API serves one built-in server at `/api/v1/mcp`, using stateless JSON responses over Streamable HTTP. Supported methods: initialize, ping, tools/list, tools/call; notifications return 202 and standalone GET streams return 405. Advertised protocol version is 2025-11-25. Every request, including local development, requires a valid bearer token; Origin is checked when supplied. Tools are `anomaly_summary`, `threat_forecast`, and `telemetry_health`, with no arguments and read-only tenant access. Use the MCP page to inspect and test tools after signing in.

Transport reference: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

The former demo-only stdio module is retired. This release does not connect to arbitrary remote MCP servers, launch processes, implement OAuth discovery, stream notifications, or store client secrets. Clients need support for supplying an existing bearer token. Expose it through the same controlled ingress as the REST API, with request-size/rate limits appropriate to the deployment.

## Verification

From `apps/api`, run `python -m unittest discover -s tests -v` for detection and protocol tests. Run `python -m unittest tests.integration_advanced -v` explicitly for PostgreSQL persistence, replay handling, tenant isolation and the plugin lifecycle. The integration test uses isolated temporary tenant IDs and deletes only its records afterward; it skips if PostgreSQL is unavailable.

From `apps/web`, run the existing typecheck and build scripts.

Verification on 2026-09-14: 11 automated tests passed, TypeScript and optimized Next.js build passed. `scripts.smoke_workspace` passed against real PostgreSQL 16, Elasticsearch 8 and local LM Studio: authentication, immediate role changes, tenant isolation, IOC correlation, actor profiles, detection, forecast, replay protection, alert triage, source matching, plugin lifecycle, MCP, 1,709 live CISA records, all three report formats, AI conversation isolation and logout revocation. Temporary integration tenants are removed afterward. Browser registration and IOC creation were also exercised. On 2026-09-15, both Docker images built and the full container integration workflow passed, including local AI, 1,710 CISA records and logout; two additional AI regression tests passed. Kubernetes deployment remains unverified.

## Reported telemetry geography

An authorized telemetry event may include an optional `location` object: `{"latitude":28.6,"longitude":77.2,"name":"Reported site","source":"Approved sensor inventory"}`. Coordinates must be finite and within geographic bounds; name and source are required. Existing events without locations remain valid. Locations are stored with the original event and preserved through anomaly evidence.

The dashboard plots a latitude/longitude grid using only source-provided locations from the authenticated tenant. It shows at most 200 groups from the latest 10,000 geocoded observations in the last 24 hours, excluding future observations. The location selector exposes provenance, count and last observation. These are reported locations, not independently verified attacker origin; event volume is not severity. Empty coverage is UNAVAILABLE and failed refreshes are STALE. There are no random coordinates, IP lookups, external map requests or model-generated geographic evidence.
