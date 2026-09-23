# DarkTrace-X Pending Features

Audit date: 2026-09-20

This list is derived from the current repository audit. It is intentionally limited to observed gaps and unverified production requirements. It does not treat test doubles or empty-state UI as production defects.

## P0 - Critical blockers

| Problem | Current state | Expected behavior | Affected modules/files | Recommended fix | Complexity |
| --- | --- | --- | --- | --- | --- |
| Legacy schema bootstrap is not fully production-safe | `Base.metadata.create_all` remains in `apps/api/app/storage/database.py`; Alembic only covers the source pipeline tables. | Every production schema change is versioned, reviewable, upgradeable and reversible. | `apps/api/app/storage/database.py`, `apps/api/migrations/`, `apps/api/app/storage/models.py` | Create a reviewed baseline migration for legacy tables, run migrations before startup, and fail production startup when schema is behind. | HIGH |
| No tested backup/restore | PostgreSQL/Elasticsearch named volumes exist, but restore has not been executed. | Backups are automated, encrypted, monitored and restorable with documented RPO/RTO. | `docs/DEPLOYMENT.md`, data services, operations runbooks | Add backup jobs, restore fixtures and a repeatable recovery test for PostgreSQL and Elasticsearch; document Redis AOF recovery. | HIGH |
| Production TLS and identity hardening absent | Local Nginx HTTP works; Kubernetes declares TLS but no live certificate/ingress was tested. JWT is stored in browser localStorage; no SSO/MFA. | Internet-facing traffic uses HTTPS, secure cookies/CSRF controls, SSO/MFA where required, and secret rotation. | `infra/nginx/default.conf`, `infra/k8s/ingress.yaml`, `apps/api/app/core/security.py`, frontend auth | Deploy trusted TLS ingress, choose HttpOnly cookie or approved SSO architecture, add MFA and login abuse controls. | HIGH |
| No independent security assessment | Local negative tests exist, but no penetration test or production threat model validation. | IDOR/BOLA, SSRF, session, file, dependency and tenant-isolation risks are independently assessed. | Entire platform | Run authorized application/security testing against a staging deployment and remediate findings. | HIGH |

## P1 - Important reliability and completeness work

| Problem | Current state | Expected behavior | Affected modules/files | Recommended fix | Complexity |
| --- | --- | --- | --- | --- | --- |
| Source scheduler lacks retries and advanced policy enforcement | Scheduler runs custom/hourly/daily/weekly due sources and persists next-run timestamps. No exponential retry, robots policy, multi-page depth, or per-source rate/concurrency controls. | Crawls retry safely, respect robots/source policy, avoid overload, and expose failure/queue metrics. | `apps/api/app/services/scheduler.py`, `apps/api/app/services/source_management.py`, `apps/api/app/storage/models.py` | Add retry state/backoff, robots.txt policy checks, per-source leases/rate limits, bounded page depth and worker metrics. | HIGH |
| Documents, entities and events have no dedicated analyst UI | APIs exist and live data was retrieved, but frontend has no dedicated pages for these records. | Analysts can browse, filter, paginate, inspect provenance and pivot document → entity → event → alert. | `apps/web/components/feature-workspace.tsx`, new workspace components | Add real API-backed pages and route/navigation entries with loading/error/empty states. | MEDIUM |
| Crawl jobs have no standalone workspace | History is embedded in Source Management only. | Operators can filter jobs by status/source/date, inspect failures and retry authorized jobs. | `apps/web/components/source-management-workspace.tsx`, new crawl workspace | Add crawl job API filtering and a dedicated UI. | MEDIUM |
| Extraction is HTML/text focused | Deterministic extraction works for text and CISA JSON represented as text. RSS, Atom and JSON-specific parsing are not separately implemented. | Parser adapters normalize supported formats with date/author/links/metadata preservation. | `apps/api/app/services/source_management.py` | Add format-specific parser adapters and parser-level tests. | MEDIUM |
| NLP coverage is deterministic IOC-only | CVE/IP/domain/URL/email/hash extraction is persisted. Malware, actor, campaign, organization, vendor, product and ATT&CK extraction are not integrated. | AI/NLP outputs are provenance-labeled, confidence-scored and never overwrite source facts. | `apps/api/app/services/source_management.py`, AI gateway, entity models | Add evaluated deterministic dictionaries/models first, then optional AI enrichment as separate untrusted annotations. | HIGH |
| Event/alert models are not fully unified | Entity and keyword events exist; older operational alerts and intelligence alerts remain separate paths. | All detections share event schema, factorized risk score, alert linkage and state transitions. | `apps/api/app/storage/models.py`, detection/intelligence services | Introduce explicit event-alert relationships and a single scoring/deduplication service. | HIGH |
| Report/webhook delivery workers absent | Schedules and webhook subscriptions persist and validate, but delivery remains pending/external. | Approved workers deliver signed webhooks/reports with retries, status, dead-letter handling and audit. | `apps/api/app/services/webhooks.py`, `report_schedules.py`, worker/deployment config | Add an external-worker/queue design with secure delivery, retries and integration tests. | HIGH |
| Host integration test configuration differs from Compose | `tests.integration_advanced` skipped because host localhost PostgreSQL was unavailable; containerized smoke is the working path. | Test commands select the correct environment and clearly distinguish skipped from passed. | `apps/api/tests/integration_advanced.py`, `docker-compose.verify.yml`, docs | Add a documented container integration command to CI and avoid misleading host defaults. | LOW |
| CI does not execute full live integration/recovery path | Workflow has unit/build/audit/container jobs; GitHub-hosted live Compose verification was not observed. | CI or a protected nightly workflow runs integration, recovery and migration checks. | `.github/workflows/ci.yml`, verification Compose | Add service-backed integration job with isolated data and explicit cleanup. | MEDIUM |

## P2 - Improvements

| Problem | Current state | Expected behavior | Affected modules/files | Recommended fix | Complexity |
| --- | --- | --- | --- | --- | --- |
| Threat Graph relationship coverage is narrow | Exact IOC correlation, tags and actor techniques work; broad domain/IP/malware/campaign/CVE relationships are limited. | Evidence-backed relationship edges cover supported entity types with confidence and timestamps. | `apps/api/app/search/service.py`, entity/observation models, graph UI | Index observation/relationship edges and add pivot/detail UI. | HIGH |
| Risk scoring is not unified | Operational alert scores exist, but a single transparent factor model is not applied to every IOC/event. | Analysts see repeatable factors, weights, source reliability and score history. | detection/intelligence/alert services and schemas | Implement a centralized scoring service and factor persistence. | MEDIUM |
| No load/performance qualification | No representative bulk IOC, crawl, WebSocket or concurrent API benchmark was run. | Capacity thresholds and failure behavior are measured before deployment. | CI/ops scripts, API/search/worker services | Add bounded benchmark harnesses and resource dashboards. | MEDIUM |
| No browser accessibility/visual regression suite | Production build and runtime HTTP checks pass; no Playwright/accessibility suite was executed. | Critical flows are browser-tested across desktop/mobile and themes. | `apps/web`, CI | Add Playwright smoke/accessibility checks for auth, source crawl, alerts, reports and copilot. | MEDIUM |
| Cloud provider coverage incomplete | Local GGUF is verified; OpenAI previously returned 429 and other providers lack live credentials. | Each enabled provider has health, timeout, quota and fallback evidence. | AI gateway/configuration/docs | Run credentialed staging tests and publish provider-specific status. | MEDIUM |
| GPU inference unverified | Local model works on CPU; CUDA offload is not proven. | Target deployment documents verified GPU mode, fallback and resource requirements. | `apps/llm`, Docker/Kubernetes manifests | Build/test a CUDA profile on target hardware. | HIGH |
| Metrics/logging production wiring incomplete | Request IDs, Prometheus metrics and health endpoints exist. | Structured logs, scrape targets, retention and alerting operate in deployment. | `apps/api/app/observability.py`, infra manifests | Add structured fields, Prometheus deployment, dashboards and alert rules. | MEDIUM |
| Stale documentation claims remain | Some README/readiness text predates the current scheduler/Alembic/entity pipeline. | Docs describe current tested state and mark historical evidence clearly. | `README.md`, `docs/READINESS_REPORT.md`, `docs/FINAL_READINESS_REPORT.md` | Consolidate current audit/readiness references and remove contradictory historical limits. | LOW |
| Licensed collection integration absent | Approved evidence import exists; no licensed live dark-web/authorized collection source configured. | A lawful connector can be installed, monitored, rate-limited and audited. | source adapters, deployment and legal/config docs | Add only after provider/legal requirements are supplied. | HIGH |

## Recommended implementation order

1. Establish the full legacy migration baseline and production startup gate.
2. Deploy TLS, secure session/identity controls, managed secrets and tested backups.
3. Harden scheduler/crawler retries, robots, rate/concurrency and worker recovery.
4. Add documents/entities/events/crawl-jobs analyst UI.
5. Unify event, alert and risk-scoring models.
6. Add parser adapters and evaluated NLP enrichment.
7. Add live integration/recovery/performance/browser CI coverage.
8. Validate target cloud providers, GPU mode and authorized licensed sources.
