# DarkTrace X Final Gap Analysis

Audit date: 2026-09-20

This is an evidence-based snapshot of the existing implementation. `PASS` means the repository contains a relevant implementation and the available local evidence supports it. `PARTIAL` means the core path exists but an important production concern remains. `NOT TESTED` means the dependency or deployment target was not available for verification. No status below is based on source presence alone.

## Status matrix

| Subsystem | Status | Evidence and genuine gap |
| --- | --- | --- |
| Next.js frontend | PASS | Docker production build succeeds; dashboard is served through Nginx with HTTP 200. Full browser regression and accessibility testing remain absent. |
| FastAPI REST API | PASS | API container starts and `/api/v1/health/ready` returns `{"status":"ready"}`. Full backend tests are not installed in the production image. |
| PostgreSQL | PASS | Compose healthcheck and API readiness pass. Credentials are development defaults and backup/restore is not verified. |
| Redis | PASS | Compose healthcheck passes and copilot coordination uses Redis. TLS, external deployment and restart/recovery are not tested. |
| Elasticsearch | PASS | Compose healthcheck passes and tenant-scoped correlation is implemented. Security is disabled for local Compose and production auth/TLS is not configured. |
| Authentication and sessions | PASS | JWT expiry, issuer/audience, revocation and active-user checks are implemented and covered by token tests. Browser tokens remain in localStorage; SSO/MFA are absent. |
| RBAC and tenant isolation | PASS | Current database role and tenant-scoped queries are enforced in backend dependencies/services. PostgreSQL RLS is not enabled, so isolation depends on application correctness. |
| Audit logging | PARTIAL | Persistent audit records exist for important operations. Records are not immutable, signed, or shipped to an external retention system. |
| IOC pipeline | PASS | Validation, persistence, deduplication, Elasticsearch correlation and source metadata are implemented. Broad multi-source ingestion is not configured. |
| CVE intelligence | PARTIAL | Real CISA KEV ingestion is implemented. This is not a complete NVD/EPSS/CVSS asset-version matching service. |
| Threat ingestion | PARTIAL | CISA and approved evidence import paths are real and provenance-aware. There is no general scheduled collection queue. |
| Authorized collectors | PARTIAL | Evidence import and source validation exist. No licensed live dark-web collector, parser isolation worker, scheduler, or dead-source monitor is connected. |
| Correlation and threat graph | PASS | Tenant-scoped IOC relationships and actor techniques are persisted and queried. Confidence aggregation/source weighting needs broader cross-source validation. |
| Risk scoring | PARTIAL | Operational alert scores and evidence factors exist. A unified explainable scoring contract across every intelligence type is not demonstrated. |
| Reports | PASS | PDF, DOCX and XLSX exports are implemented and tested in the existing verification workflow. Scheduled delivery remains `pending_external_delivery`. |
| WebSockets | PASS | Authenticated event streaming exists and is proxied by Nginx. Reconnect/load behavior is not tested. |
| GraphQL | PASS | Authenticated GraphQL router exists. Query-depth/complexity limits and load testing are not demonstrated. |
| MCP | PASS | Built-in authenticated read-only MCP server is implemented. Arbitrary remote MCP lifecycle/OAuth/process management is intentionally absent. |
| AI gateway | PARTIAL | Local and multiple provider adapters, privacy routing and fallback tests exist. Live cloud provider compatibility is not established; OpenAI previously returned HTTP 429. |
| Local Qwen GGUF | PASS | Persistent local-LLM service and real CPU inference were verified in the existing readiness evidence. Actual CUDA/GPU offload is not tested. |
| RAG/project knowledge | PASS | Allowlisted lexical retrieval and source attribution are implemented. This is not vector retrieval and production index lifecycle is not configured. |
| AI copilot/command center | PASS | Floating copilot, streaming, persisted history and admin controls exist. Adversarial model-output and high-concurrency testing remain incomplete. |
| Docker | PASS | API, web and worker images build; application containers run non-root. Database/search credentials and Elasticsearch security are local-development defaults. |
| Nginx | PASS | REST, SSE, WebSocket and GraphQL proxy routes plus request limits/security headers exist. TLS termination is not supplied. |
| Kubernetes | PARTIAL | Manifests include deployments, probes, non-root settings and network policy. No cluster rollout, TLS, external secrets, storage recovery, or GPU scheduling was verified. |
| CI/CD | PARTIAL | Workflow installs dependencies, compiles Python, typechecks and builds web. It does not run backend tests, lint/security scans, container scans, or recovery tests. |
| Migrations | PARTIAL | Startup calls SQLAlchemy `Base.metadata.create_all`; no versioned migration/rollback system was found. |
| Observability | PARTIAL | Prometheus metrics, request IDs and dependency readiness exist. Structured log schema, scrape deployment, retention and alerting are incomplete. |
| Security posture | PARTIAL | RBAC, validation, SSRF checks, size limits and secret redaction are present. TLS, MFA/SSO, RLS, immutable audit, secret manager and penetration testing remain. |
| Backups and recovery | NOT TESTED | Named volumes are present, but no tested backup/restore or dependency restart exercise was found in this audit. |
| Performance | NOT TESTED | No representative concurrency, large-IOC, bulk-ingestion, WebSocket, or query benchmark was executed in this audit. |

## Search findings requiring disposition

- `apps/api/app/storage/database.py` bootstraps with `Base.metadata.create_all`; this is not a substitute for reviewed migrations in production.
- `.github/workflows/ci.yml` does not execute the backend test suite or dependency/container/secret scanning.
- Report schedules are durable but deliberately remain `pending_external_delivery` until a delivery worker is deployed.
- No scheduled intelligence collection worker or licensed dark-web source is configured.
- The production API image does not include test dependencies, so tests must run through the dedicated verification image/compose path.
- Existing `pass`/broad exception sites are mostly deliberate base-class, cleanup, or fault-isolation paths, but each should remain covered by targeted tests rather than being treated as proof of readiness.

## Immediate implementation priorities

1. Make CI run backend tests, frontend checks, security/dependency checks, and image builds.
2. Add a versioned migration workflow and stop relying on `create_all` outside an explicit development/test mode.
3. Add a documented recovery test for PostgreSQL, Redis, Elasticsearch, API, web, and local AI restart behavior.
4. Keep external provider, licensed collection, TLS, Kubernetes, backup, and performance claims explicitly conditional until their real dependencies are supplied.

## M2 - Crawling P1 / Source Discovery and Management

| Acceptance item | Status | Evidence / remaining gap |
| --- | --- | --- |
| Source list/search/pagination | PASS | `GET /api/v1/sources` is tenant-scoped with query, limit and offset; Source Management UI renders loading, empty and error states. |
| Add source | PASS | `POST /api/v1/sources` persists validated public source metadata and writes `source.created` audit events. |
| Edit source | PASS | `PUT /api/v1/sources/{id}` persists lifecycle fields and writes `source.updated`; UI action is wired. |
| Delete/archive | PASS | `DELETE /api/v1/sources/{id}` archives by disabling rather than deleting history; UI confirmation is wired. |
| Enable/disable | PASS | Dedicated endpoints update enabled/health state and audit events; disabled sources cannot crawl. |
| URL validation/SSRF defense | PASS | Absolute HTTP(S), credentials, DNS and private/link-local/reserved targets are rejected; live `127.0.0.1` attempt returned HTTP 422. |
| Connectivity/health | PASS | `POST /api/v1/sources/{id}/validate` records status, latency, response type, last check, failure state and error; live public fixture returned HTTP 200/HEALTHY. |
| Manual crawl | PASS | `POST /api/v1/sources/{id}/crawl` fetched `https://example.com/`, completed one document, and returned a crawl job. |
| Crawl policy | PARTIAL | Policy/frequency are persisted and displayed; no scheduler worker currently executes hourly/daily/weekly jobs. |
| Crawl history | PASS | `GET /api/v1/sources/{id}/crawls` returned the completed live job. |
| Normalization/extraction | PASS | HTML title/text/link normalization and regex IOC extraction are covered by tests; NLP model entity extraction is not claimed. |
| Content deduplication | PASS | SHA-256 normalized-content deduplication preserves original document provenance and records duplicate crawl counts. |
| Event/alert provenance | PASS | Keyword alerts include source, crawl, document and content-hash evidence; cross-source NLP correlation remains future work. |
| Database persistence | PASS locally | New source, crawl and document tables bootstrap in the current schema and survive service requests; versioned migrations remain a production gap. |
| Tenant isolation | PASS by implementation | Every source/job/document query includes tenant scope; dedicated live cross-tenant crawl test is still required. |
| RBAC | PASS by implementation | Lead/admin manage registry; analyst/lead/admin validate and crawl; viewer is denied by route dependencies. |
| Audit logging | PASS | Create/update/enable/disable/archive/crawl success/failure actions create persistent audit records. |
| Frontend/API integration | PASS | Dedicated Source Management navigation and workspace call all registry, health, crawl and history endpoints; web production build succeeds. |
| Scheduler/retry/concurrency | NOT TESTED | No scheduler/queue worker, exponential retry loop, or sustained concurrency test is present yet. |

**M2 readiness: 83% for the implemented manual source-management profile.** The core registry, validation, health, manual crawl, provenance, deduplication, persistence, RBAC, audit and UI flow are demonstrated. Scheduled crawling, retry/backoff workers, multi-page depth, robots policy enforcement and a full live cross-tenant API test remain before calling M2 production-complete.

## Current end-to-end pipeline matrix

| Module | Status | Evidence |
| --- | --- | --- |
| Backend architecture / NLP integration | PARTIAL | Source service, scheduler and deterministic extraction are modular; AI/NLP entity enrichment and malware/actor/campaign models are not yet integrated. |
| Data / database / processing | PARTIAL | PostgreSQL persists sources, jobs, documents, entities, observations and events with tenant uniqueness/indexes; legacy tables still use development `create_all`. |
| Event detection / alerting | PASS for implemented detections | Entity detection and keyword-match events are persisted with severity, confidence, reason and evidence; operational alerts deduplicate by tenant key. Broader correlation rules remain. |
| APIs / authentication / services | PASS | Source, document, entity and event APIs are authenticated and tenant-scoped; existing JWT/RBAC tests remain green. |
| Source discovery / management | PASS | Live add, enable, validate, crawl, history, archive and UI integration were demonstrated previously. |
| Crawling engine | PARTIAL | Manual and scheduled single-page HTTP crawling, SSRF checks, content limits, health and duplicate-job protection work. Retries, robots policy, multi-page depth and rate/concurrency controls remain. |
| Data quality / deduplication / monitoring | PASS for current formats | Empty/oversized content rejection, normalized SHA-256 deduplication, source health and crawl counters work; broader document corruption/format coverage remains. |
| Content extraction / normalization | PASS for HTML/text | HTML title/text/link extraction and text normalization are tested; RSS/Atom/JSON parser-specific normalization is not yet implemented. |

Live pipeline evidence from 2026-09-20: CISA KEV JSON crawl downloaded 1,735,385 bytes, created one document, persisted 100 CVE entities and 100 threat events. A custom-interval scheduler cycle returned `scheduled_crawls=1`.