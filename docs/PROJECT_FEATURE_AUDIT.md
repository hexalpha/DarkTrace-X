# DarkTrace-X Project Feature Audit

Audit date: 2026-09-20
Scope: current repository and local Docker deployment. No product-code changes were made during this audit. Only this audit report and the pending-work report were created.

## Executive result

**Overall local readiness: 82%**

This is a verified local Docker profile, not a production certification. The core API, frontend, PostgreSQL, Redis, Elasticsearch, Nginx, local GGUF worker, source registry, crawling pipeline, entity/event persistence, and core integration workflows are operational. Production TLS, backups, load qualification, cloud-provider coverage, licensed collection, migration baseline coverage, and several UI surfaces remain incomplete or unverified.

## Architecture

| Layer | Current implementation |
| --- | --- |
| Frontend | Next.js 15/React dashboard in `apps/web`, feature workspaces, Source Management, AI Copilot and AI Command Center. |
| API | FastAPI in `apps/api/app/main.py`, versioned REST routes, GraphQL router, WebSocket event stream, MCP endpoints. |
| Persistence | PostgreSQL/SQLAlchemy models; named Compose volume. Current development bootstrap still calls `Base.metadata.create_all`. Alembic source-pipeline migration `0001_source_pipeline` exists. |
| Search | Elasticsearch service with tenant-scoped IOC correlation and graph indexing. |
| Cache/control | Redis for copilot leases, rate limiting and coordination. |
| AI | Local Qwen GGUF worker, provider gateway adapters, RAG/project knowledge, copilot streaming and fallback policy. |
| Crawling | Tenant source registry, SSRF-safe validation, single-page HTTP crawl, normalization, SHA-256 deduplication, deterministic entity extraction, threat events and alerts. Persistent scheduler runs configured recurring policies. |
| Edge | Nginx routes frontend, REST, GraphQL, SSE and WebSocket traffic. |
| Deployment | Docker Compose works locally. Kubernetes manifests render with `kubectl kustomize`; no cluster rollout was performed. |
| CI/CD | GitHub Actions workflow includes backend tests, frontend lint/typecheck/build/audit, pip audit, secret scan and image builds. GitHub-hosted execution was not run locally. |

## Runtime evidence

| Check | Result |
| --- | --- |
| Compose config | PASS: `docker compose config --quiet` |
| API | Running, healthy |
| Web | Running |
| Nginx | Running on `127.0.0.1:8080` |
| PostgreSQL | Running, healthy |
| Redis | Running, healthy |
| Elasticsearch | Running, healthy |
| Local LLM | Running; real GGUF inference verified by container copilot test |
| Dashboard | HTTP 200 |
| API liveness | HTTP 200 |
| API readiness | HTTP 200, `{"status":"ready"}` |
| Nginx syntax | PASS: `nginx -t` |
| Kubernetes render | PASS: `kubectl kustomize infra/k8s` |
| API/web restart | PASS: both recovered, dashboard/readiness returned 200 |

## Test evidence

- Backend unit/security suite: **35 passed**.
- Host PostgreSQL integration test: **1 skipped**, because the host-side configuration targeted an unavailable host PostgreSQL; this is not a pass. The correct containerized workflow was then run.
- Containerized `scripts.smoke_workspace`: **PASS**, including registration/login, RBAC, tenant isolation, IOC/search/graph, actors, detection/forecast, source ingestion, marketplace/MCP, CISA feed, reports, AI and logout.
- Containerized `scripts.verify_copilot`: **PASS**, including WebSocket, GraphQL, PostgreSQL/Redis/Elasticsearch/GGUF health, RAG, RBAC, redaction, request limits, provider-secret handling, notifications, real GGUF streaming/persistence and logout.
- Frontend Docker production build: **PASS**.
- Fresh source pipeline: **PASS**. Source registration, enablement, CISA validation HTTP 200, crawl completion, one document, 100 CVE entities, 100 events, crawl history, and SSRF rejection HTTP 422.
- Scheduler cycle: **PASS**. A custom-interval source was claimed and crawled with `scheduled_crawls=1`.
- Migration discovery: **PASS**. Alembic head `0001_source_pipeline` discovered and migration/app compilation passed.

## Feature matrix

Status meanings: `PASS` tested and working; `PARTIAL` real behavior exists but important capability is incomplete; `FAIL` implemented but currently broken; `NOT IMPLEMENTED` absent; `NOT TESTED` not verified in this environment.

| Module | Feature | Frontend | Backend | Database | Tested | Status | Evidence | Pending work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Frontend | Dashboard | Connected | Connected | Connected | Yes | PASS | Dashboard HTTP 200; overview API is used. | Full browser/accessibility regression suite. |
| Frontend | Source Management | Connected | Connected | Connected | Yes | PASS | UI actions call `/sources`; live add/validate/enable/crawl/history flow passed. | Dedicated UI for documents/entities/events. |
| Frontend | Crawl Jobs | Partial | Connected | Connected | Partial | PARTIAL | Crawl history is embedded in Source Management; no standalone crawl-jobs page. | Dedicated job list/filter/retry UI. |
| Frontend | Documents | Not connected | Connected | Connected | API tested | PARTIAL | `/documents` returns persisted crawled documents; no frontend page uses it. | Documents page and detail/evidence view. |
| Frontend | IOC Intelligence | Connected | Connected | Connected | Yes | PASS | IOC CRUD/correlation and tenant isolation passed in container smoke. | More pagination/detail/observation UI. |
| Frontend | Events | Not connected | Connected | Connected | API tested | PARTIAL | `/events` returns persisted entity/keyword events; no dedicated UI page. | Events queue and event-detail UI. |
| Frontend | Alerts | Connected | Connected | Connected | Yes | PASS | Alert list/triage/Ask AI exercised in smoke and UI code calls APIs. | Unified event-to-alert detail and richer scoring factors. |
| Frontend | Threat Map | Connected | Connected | Connected | Yes | PASS | Source-reported geography validation and dashboard rendering verified. | Automatic geolocation intentionally absent. |
| Frontend | Threat Graph | Connected | Connected | Connected | Yes | PASS | Elasticsearch graph path and UI graph component exist; smoke passed graph isolation. | Broader entity relationship graph. |
| Frontend | Reports | Connected | Connected | Connected | Yes | PASS | PDF/DOCX/XLSX live exports passed. | Scheduled delivery worker. |
| Frontend | AI Command Center | Connected | Connected | Connected | Yes | PASS | Production build and copilot verification passed. | Broader UI diagnostics and provider live coverage. |
| Frontend | AI Copilot/chatbot | Connected | Connected | Connected | Yes | PASS | Real GGUF streaming, persistence, redaction and logout verification passed. | Cloud provider live coverage, adversarial/load evaluation. |
| Frontend | Exposure | Connected | Connected | Connected | Yes | PASS | Keyword monitors, CISA import and approved evidence import are wired. | Licensed live collection is absent. |
| Frontend | CVE Intelligence | Connected | Connected | Connected | Yes | PASS | CISA KEV data retrieved and displayed; no fabricated CVSS/EPSS. | Full NVD/asset matching. |
| Frontend | YARA | Not connected | Backend endpoint | Persistent documents | Not tested | NOT TESTED | `/yara-rules` backend route exists; no visible current navigation/page found. | UI and runtime validation. |
| Frontend | Plugins/Marketplace | Connected | Connected | Connected | Yes | PASS | Marketplace lifecycle and MCP execution passed in smoke. | Arbitrary third-party sandboxed plugins absent. |
| Frontend | Integrations/Webhooks | Not connected | Connected | Connected | Unit validation | PARTIAL | Admin webhook API and security validation exist; no dedicated UI and external delivery not live-tested. | UI and delivery worker. |
| Frontend | Admin | Connected | Connected | Connected | Yes | PASS | User creation, roles, audit/platform status and RBAC exercised. | Secure production session model/SSO/MFA. |
| Frontend | Settings | Connected | Connected | Connected | Partial | PARTIAL | Provider readiness and copilot settings UI exist. | Full source/scheduler/security configuration UI. |
| Backend | PostgreSQL persistence | Connected | Connected | Connected | Yes | PASS | Compose health, smoke writes/reads, persistence tests. | Production credentials, TLS, backups and restore. |
| Backend | Redis | Indirect | Connected | Persistent service | Yes | PASS | Copilot verification and Compose health passed. | External TLS/load/recovery qualification. |
| Backend | Elasticsearch | Indirect | Connected | Persistent service | Yes | PASS | IOC correlation/graph and Compose health passed. | Production auth/TLS and cluster validation. |
| Backend | Migrations | None | Connected | Partial | Partial | PARTIAL | Alembic source pipeline head/compile passed. Legacy tables still use `create_all`. | Reviewed baseline for all legacy tables; disable production `create_all`. |
| Backend | NLP/AI entity processing | None | Partial | Connected | Partial | PARTIAL | Deterministic IOC/CVE extraction persisted as entities/events; malware/actor/campaign NLP absent. | Broader safe entity extraction and evaluation. |
| Backend | Event detection | None | Connected | Connected | Yes | PASS | Entity and keyword events persisted with evidence/dedupe. | More configurable detection rules/correlation. |
| Backend | Risk scoring | Partial | Partial | Connected | Partial | PARTIAL | Operational scores and evidence exist; not a unified scoring engine. | Explainable factor model across all intelligence. |
| Backend | Alerting | Connected | Connected | Connected | Yes | PASS | Deduplicated alerts, triage and notification verification passed. | Delivery worker and event/alert model unification. |
| Backend | Authentication | Connected | Connected | Connected | Yes | PASS | Login/logout/revocation/invalid token tests and smoke passed. | HttpOnly production cookies, SSO/MFA, brute-force controls. |
| Backend | RBAC | Connected | Connected | Connected | Yes | PASS | Role changes, viewer restrictions and admin flows passed. | Formal permission model and broader negative endpoint matrix. |
| Backend | Tenant isolation | Indirect | Connected | Connected | Yes | PASS | Container smoke and copilot tests isolate tenants. PostgreSQL RLS absent. | Database-level RLS. |
| Backend | GraphQL | No dedicated page | Connected | Connected | Yes | PASS | Authenticated GraphQL verification passed. | Complexity/load controls. |
| Backend | WebSocket | Dashboard usage | Connected | Connected | Yes | PASS | Authenticated WebSocket verification passed through Nginx. | Reconnect/load testing. |
| Backend | Scheduler | None | Connected | Connected | Yes | PARTIAL | Live custom-interval scheduler cycle returned one scheduled crawl. | Retry/backoff, robots, concurrency/rate policy, worker metrics. |
| Backend | Backup/restore | None | Persistent volumes | Volumes | No | NOT TESTED | Named volumes exist; restore was not executed. | Tested PostgreSQL/Elasticsearch backup and restore. |
| Deployment | Docker | N/A | N/A | N/A | Yes | PASS | Compose services healthy; API/web images build. | Production secrets/authenticated data services. |
| Deployment | Nginx/TLS | Nginx connected | Connected | N/A | Partial | PARTIAL | `nginx -t` passes; local HTTP routes work. TLS certificate/HTTPS endpoint not tested. | Real TLS deployment. |
| Deployment | Kubernetes | N/A | Manifests | External services | Render only | PARTIAL | `kubectl kustomize` passes; no cluster apply/rollout. | Cluster, ingress TLS, secrets, storage, GPU and policy enforcement. |
| Deployment | CI/CD | N/A | Workflow | N/A | Syntax only | PARTIAL | YAML contains tests/build/audit/secret/image jobs; GitHub run not observed locally. | Verify hosted workflow and add integration/recovery jobs. |
| Observability | Metrics/logging/health | Partial | Connected | Partial | Partial | PARTIAL | Request IDs, Prometheus metrics and readiness exist. | Structured fields, scrape/retention/alerting deployment. |

## Mock/demo/hardcoded assessment

- No production intelligence is inserted as demo data; tenant workspaces start empty and CISA records carry source provenance.
- Test doubles occur in unit tests (`unittest.mock`, `httpx.MockTransport`) and are correctly scoped to tests.
- The source-management unit test uses a fake HTTP response; the live audit separately used CISA through Docker, so this does not prove external source behavior by itself.
- UI placeholders are form guidance, not persisted demo records.
- The dashboard empty-state counters are real zero values from backend data, not hardcoded demo telemetry.
- Broad `except Exception` blocks exist in fault-isolation/startup/cleanup paths. They are risk points for observability, but not proof of fake behavior.
- Documentation contains stale claims in places: older reports say no scheduler/versioned migration, while the current code has a scheduler and Alembic source-pipeline migration. This audit reflects current runtime/code evidence.

## Broken features found

No core local workflow was observed as broken during this audit. The following are implemented but incomplete rather than marked PASS:

- Scheduled reports and outbound webhook delivery remain pending external workers.
- Cloud AI providers are not all live-verified; OpenAI previously returned HTTP 429.
- Host-side PostgreSQL integration test is configuration-sensitive and skipped when pointed at localhost; containerized verification is the valid Compose evidence.
- YARA, documents and events lack dedicated frontend workflows.

## Not implemented or not tested

- No licensed live dark-web collector.
- No arbitrary remote MCP process/OAuth management.
- No calibrated predictive threat model.
- No complete NVD/EPSS asset matching pipeline.
- No browser accessibility/full visual regression suite.
- No production TLS certificate test.
- No tested backup restore.
- No live Kubernetes rollout.
- No representative load/performance qualification.
- No independent penetration test.
- No live Gemini/Anthropic/Groq/OpenRouter/custom/Ollama provider verification in this audit.

## End-to-end pipeline result

**PASS for the implemented public CISA/manual/scheduled source path.** Fresh evidence:

1. Registered a temporary tenant and source.
2. Validated CISA URL: HTTP 200 / HEALTHY.
3. Enabled source.
4. Crawled real CISA KEV JSON.
5. Stored one document and crawl history.
6. Extracted 100 CVE entities.
7. Persisted 100 threat events.
8. Retrieved documents/entities/events through API.
9. Rejected a private `127.0.0.1` source with HTTP 422.
10. Temporary audit tenant records were removed after the probe; no audit test workspace was intentionally retained.

The pipeline is not complete for RSS/Atom/JSON-specific parsing, multi-page crawling, advanced NLP entities, broad correlation, or scheduled retry policies.

## Module summary

| Module | Status |
| --- | --- |
| Frontend | PARTIAL |
| Backend architecture | PASS |
| NLP / AI | PARTIAL |
| Database / processing | PARTIAL |
| Event detection | PASS |
| Alerting | PASS |
| APIs | PASS |
| Authentication | PASS |
| RBAC | PASS |
| Tenant isolation | PASS |
| Source management | PASS |
| Crawler | PARTIAL |
| Extraction | PASS for HTML/text |
| Normalization | PASS for HTML/text |
| Deduplication | PASS |
| IOC | PASS for supported deterministic types |
| Correlation | PASS for exact IOC/graph paths |
| Threat Graph | PASS |
| Threat Map | PASS |
| Reports | PASS manual exports |
| WebSocket | PASS |
| GraphQL | PASS |
| AI Copilot | PASS local |
| Docker | PASS |
| Nginx | PASS local |
| CI/CD | PARTIAL |
| Observability | PARTIAL |
| Security | PARTIAL |
| Deployment | PARTIAL |
