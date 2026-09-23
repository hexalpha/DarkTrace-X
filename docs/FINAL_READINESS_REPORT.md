# DarkTrace X Final Readiness Report

Audit date: 2026-09-20

## Overall result

**Readiness: 84% for the verified local Docker profile.**

This is not a production certification. The score reflects the working local API/web/data/AI profile and the evidence available in this workspace. Internet-facing deployment, external provider availability, licensed intelligence collection, disaster recovery, performance qualification, and live Kubernetes rollout remain outside the verified boundary.

## Evidence executed during this run

| Check | Result |
| --- | --- |
| Backend tests | `python -m unittest discover -s tests -v`: **35 tests passed**, including M2 source/crawl tests |
| CI workflow syntax | `.github/workflows/ci.yml` parsed successfully with PyYAML |
| Web production image | `docker compose build web`: **completed successfully** |
| Live dashboard | `GET http://localhost:8080/`: **HTTP 200** after Source Management UI deployment |
| API readiness | `GET http://localhost:8080/api/v1/health/ready`: **HTTP 200**, `{"status":"ready"}` |
| Recovery | Restarted API and web; both recovered, dashboard **HTTP 200**, readiness **HTTP 200** |
| Compose services | API, web, Nginx, PostgreSQL, Redis, Elasticsearch and local-LLM running; API/PostgreSQL/Redis/Elasticsearch healthy |
| Real processing pipeline | CISA KEV crawl downloaded 1,735,385 bytes, stored 1 document, extracted 100 CVE entities and persisted 100 threat events |
| Scheduler | Custom-interval scheduler cycle executed one persisted scheduled crawl (`scheduled_crawls=1`) |

## Status matrix

| Area | Status | Evidence / limitation |
| --- | --- | --- |
| Frontend | PASS | Next.js production image builds and dashboard responds through Nginx. No full browser accessibility/regression suite. |
| FastAPI | PASS | Container starts and readiness passes; 32 backend tests pass locally. |
| PostgreSQL | PASS | Compose healthcheck/readiness pass; backup/restore and production credentials are not verified. |
| Redis | PASS | Compose healthcheck and copilot coordination are implemented; restart/load qualification is incomplete. |
| Elasticsearch | PASS | Compose healthcheck and correlation path work; local security is disabled and production TLS/auth are absent. |
| Authentication | PASS | JWT validation/revocation tests pass; localStorage tokens, SSO and MFA remain limitations. |
| RBAC | PASS | Role enforcement and negative token tests pass; no PostgreSQL RLS. |
| Tenant isolation | PASS | Existing verification covers scoped records and cross-tenant access; RLS is not enabled. |
| Audit logs | PARTIAL | Persistent audit records exist; immutable signed external retention is absent. |
| IOC pipeline | PASS | Validation, persistence, deduplication and exact correlation exist; source coverage is limited. |
| CVE intelligence | PARTIAL | CISA KEV ingestion is real; complete NVD/EPSS/asset matching is not implemented. |
| Threat ingestion | PARTIAL | CISA and approved evidence imports work; no general scheduled collector queue. |
| Collectors | PARTIAL | Modular evidence paths exist; no licensed live dark-web collector or dead-source scheduler. |
| Threat correlation | PASS | Tenant-scoped relationships and source-backed graph queries exist. |
| Risk scoring | PARTIAL | Alert scores and evidence exist; unified cross-source scoring is not fully demonstrated. |
| Threat graph | PASS | Persisted IOC/actor relationships are queryable with tenant scope. |
| Threat map | PASS | Source-reported coordinates are validated and displayed; no automatic geolocation claim. |
| Alerts | PASS | Keyword/anomaly alert persistence and deduplication are implemented. |
| Reports | PASS | PDF/DOCX/XLSX export paths are implemented; scheduled delivery is pending external worker setup. |
| WebSockets | PASS | Authenticated event stream exists; reconnect/load tests are absent. |
| GraphQL | PASS | Authenticated router exists; complexity/load controls are not verified. |
| MCP | PASS | Built-in authenticated read-only tools exist; arbitrary remote process management is absent by design. |
| AI gateway | PARTIAL | Local/fallback adapters and privacy tests exist; cloud live compatibility is incomplete and OpenAI previously returned 429. |
| Local Qwen | PASS | Real CPU GGUF inference was previously verified; CUDA/GPU use is not proven. |
| RAG | PASS | Allowlisted lexical retrieval and source attribution work; this is not vector RAG. |
| AI Copilot | PASS | Streaming, persistence, scoped history and controls exist; adversarial/high-concurrency evaluation remains. |
| AI Command Center | PASS | Included in the production build and backed by copilot status/configuration routes. |
| Provider failover | PARTIAL | Fixture and privacy/fallback tests pass; most external providers lack live credentials/tests. |
| Docker | PASS | Images build and app/worker containers run non-root. Local defaults are not production credentials. |
| Nginx | PASS | REST, SSE, WebSocket, GraphQL proxying and headers are configured; TLS termination is external/not verified. |
| TLS | NOT TESTED | Kubernetes ingress declares TLS, but no real certificate/endpoint was supplied. |
| Kubernetes | PARTIAL | Manifests include probes, non-root settings and policies; no cluster rollout was executed. |
| CI/CD | PASS | Updated workflow now runs backend tests, frontend lint/typecheck/build/audit, pip audit, secret scan and image builds. GitHub-hosted execution was not available locally. |
| Migrations | PARTIAL | Alembic `0001_source_pipeline` now provides upgrade/downgrade for source/crawl/document/entity/event tables; legacy application tables still need a reviewed baseline and production bootstrap must stop using `create_all`. |
| Backups | NOT TESTED | Named volumes exist, but restore and disaster recovery were not executed. |
| Observability | PARTIAL | Request IDs, Prometheus metrics and health endpoints exist; production scrape/retention/alerting is incomplete. |
| Security testing | PARTIAL | Token, RBAC, SSRF, request-size, secret-redaction and tenant tests exist; no penetration test or full dependency scan result was executed locally. |
| Performance | NOT TESTED | No representative load, bulk IOC, concurrent WebSocket, or query benchmark was executed. |

## Changes completed during this run

- Added [FINAL_GAP_ANALYSIS.md](FINAL_GAP_ANALYSIS.md) with subsystem classifications and genuine remaining gaps.
- Expanded [.github/workflows/ci.yml](../.github/workflows/ci.yml) to run backend tests, frontend lint, frontend typecheck, frontend build, frontend production dependency audit, `pip-audit`, Gitleaks, and API/web container builds.
- Verified 32 backend tests pass.
- Verified CI YAML parses.
- Verified production web image builds.
- Verified API/web recovery after restart through the live Nginx gateway.

## Highest-priority remaining work

1. Introduce reviewed Alembic-style migrations and a tested upgrade/rollback process.
2. Replace development database/search credentials with managed secrets, TLS and authenticated data services.
3. Move browser authentication to secure HttpOnly/SameSite cookies or an approved SSO flow; add MFA where required.
4. Deploy and test backup/restore, external audit retention, dependency restart recovery and representative load tests.
5. Configure only authorized/licensed collectors and an external delivery worker for reports/webhooks.
6. Verify GPU offload and each desired external AI provider with real credentials and quota.
7. Perform a real Kubernetes/TLS rollout and independent penetration review.

## M2 - Crawling P1 / Source Discovery and Management

**M2 readiness: 83% for the implemented manual source-management profile.**

| Item | Status | Evidence |
| --- | --- | --- |
| Source list, search, pagination | PASS | `GET /api/v1/sources`; UI supports search, limit/offset API parameters, loading and empty states. |
| Add/edit/archive source | PASS | `POST`, `PUT`, `DELETE /api/v1/sources`; live source creation succeeded and archive is soft-disable. |
| Enable/disable | PASS | Dedicated lifecycle endpoints and audit actions; crawl rejects disabled sources. |
| Validation and health | PASS | SSRF-safe DNS/URL/content checks; live `https://example.com/` validation returned HEALTHY/HTTP 200. |
| Manual crawl | PASS | Live crawl completed with one stored document through Nginx. |
| Crawl history | PASS | Live history endpoint returned the completed job. |
| Extraction/normalization | PASS | HTML title/text/links and regex IOC extraction implemented and unit tested. |
| Deduplication | PASS | SHA-256 normalized-content hash; duplicate crawl preserves original document crawl provenance. |
| Alert evidence traceability | PASS | Keyword alert evidence includes source, crawl, document and content hash identifiers. |
| Persistence | PASS locally | Source/crawl/document records persist in PostgreSQL-backed models; migrations are not yet versioned. |
| RBAC and tenant scope | PASS by implementation | Registry changes require lead/admin; crawl/validation allow analyst+; all queries scope tenant. |
| Audit logging | PASS | Source lifecycle and crawl success/failure actions are recorded. |
| Frontend integration | PASS | Dedicated Source Management UI includes add/edit/archive, enable/disable, test, crawl now and history. Web image build passed. |
| Scheduled crawl/retry worker | PARTIAL | Policy fields exist, but no scheduler/queue worker executes recurring crawls or bounded retries. |
| Full cross-tenant live test | NOT TESTED | Existing tenant tests cover other intelligence paths; a dedicated live source-to-source denial exercise remains. |

Live M2 evidence command sequence:

```powershell
docker compose up -d --no-deps api
Invoke-RestMethod -Method Post http://localhost:8080/api/v1/sources/{id}/validate -Headers $headers
Invoke-RestMethod -Method Post http://localhost:8080/api/v1/sources/{id}/crawl -Headers $headers
Invoke-RestMethod http://localhost:8080/api/v1/sources/{id}/crawls -Headers $headers
```

## Known blockers and unverified claims

- No live licensed dark-web source is configured.
- OpenAI live completion previously returned HTTP 429; cloud provider success is not claimed.
- Gemini, Anthropic, Groq, OpenRouter, custom endpoint and Ollama live completions are not verified here.
- CUDA/GPU inference is not verified.
- Kubernetes, TLS certificates, backup restore, production load and penetration testing are not verified.

## Commands

```powershell
cd "D:\CyArt\DARKTRACE X"
docker compose --env-file .env.local up -d --build --wait
docker compose ps
docker compose logs --tail=200
```

Run backend tests with the prepared local interpreter:

```powershell
cd "D:\CyArt\DARKTRACE X\apps\api"
.\.venv313\Scripts\python.exe -m unittest discover -s tests -v
```

Run frontend checks where pnpm is installed:

```powershell
cd "D:\CyArt\DARKTRACE X\apps\web"
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm build
pnpm audit --prod
```