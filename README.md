# DarkTrace X

A defensive threat-intelligence workspace with a FastAPI API, Next.js dashboard, PostgreSQL storage, Elasticsearch correlation and a provider-connected SOC assistant. Tenant workspaces start empty; the application does not insert demonstration intelligence.

## Start on this Windows workspace

Docker is also prepared: run `python scripts/setup_copilot.py`, then `docker compose --env-file .env.local up -d --build --wait` and open http://localhost:8080. Both application images and the complete Docker integration workflow, including local AI and logout, passed on 2026-09-15. Docker uses its own persistent database volumes, separate from the Windows installation below. See [deployment](docs/DEPLOYMENT.md) for restart and verification commands.

Run `./start-local.ps1` from this directory, then open http://localhost:3000. Create your workspace and first administrator through registration. Keep the workspace ID for later login. Use Administration to create analyst, lead or viewer accounts.

The launcher uses the prepared Python 3.13 environment and portable services in `.runtime`. PostgreSQL listens on 127.0.0.1:15432, Elasticsearch on 127.0.0.1:19200, the API on 127.0.0.1:8000 and the dashboard on 127.0.0.1:3000. It verifies readiness before reporting success. `./start-local.ps1 -RestartApi` reloads backend changes. Logs and generated database/JWT secrets remain in ignored `.runtime`; retain that directory to preserve data and sessions.

This launcher is prepared for this machine. A fresh machine needs Python 3.13, Node, dependencies installed from `apps/api/requirements.txt` and `apps/web/pnpm-lock.yaml`, a Next.js build, and service archives obtained by `apps/api/scripts/download_runtime.py`. See [deployment](docs/DEPLOYMENT.md).

## Local AI copilot

The authenticated dashboard includes a persistent floating cybersecurity copilot and `/ai-command-center`. A separate GGUF worker reuses loaded weights; model path and runtime settings are configurable. Primary/fallback/offline routing, encrypted provider keys, scoped memory, source-attributed read tools, allowlisted project knowledge and evidence-driven notifications are integrated. See [copilot setup](docs/COPILOT.md) and the current [verified readiness report](docs/READINESS_REPORT.md). The readiness report supersedes historical counts below.

## Features and verification

| Feature | Implemented behavior |
| --- | --- |
| Login, multi-tenancy, RBAC | Persistent users; explicit workspace login; current roles checked per request; logout revokes tokens |
| IOC intelligence and correlation | Validated observables, source/confidence, persistent records, Elasticsearch exact correlation and tenant-scoped graph |
| Threat actors | Source-backed analyst records and reported technique relationships |
| Threat feed and CVE dashboard | Real CISA Known Exploited Vulnerabilities ingestion; unavailable CVSS/EPSS values remain absent |
| Source management and manual crawling | Tenant-scoped source registry with SSRF-safe validation, health, manual crawl, normalized documents, content-hash deduplication, crawl history and audit traceability |
| Monitoring and alerts | Keyword matching on imported evidence; deduplicated alerts; analyst status changes and audit records |
| Anomaly detection | Statistical entity baselines, evidence-linked findings and persistent alerts from telemetry ingestion |
| Threat forecast | Evidence-linked trend priority; requires baseline data and is not a calibrated attack probability |
| SOC assistant | Actual provider completion with tenant evidence and private persisted conversation history |
| MCP | Authenticated built-in read-only Streamable HTTP server |
| Marketplace | Three built-in extensions with installation, enable/disable and execution controls |
| Reports | Authenticated PDF, DOCX and XLSX exports of recorded evidence |
| Kubernetes | Non-root deployment manifests, probes and network policy; cluster deployment remains unverified |

Administrators can register signed outbound alert webhooks at `/api/v1/integrations/webhooks`; HTTPS, public-address, event and severity checks are enforced and secrets are encrypted. Leads and administrators can register validated five-field report schedules at `/api/v1/reports/schedules`. Schedule records are durable and audited, while actual email/report delivery remains `pending_external_delivery` until an SMTP or approved delivery worker is configured.

The current verification snapshot is documented in [READINESS_REPORT.md](docs/READINESS_REPORT.md). The Docker image suite passes 28 backend tests, including source-reported telemetry geography validation. The live integration workflow passes against PostgreSQL, Redis, Elasticsearch and the persistent GGUF worker, covering authentication, role changes, tenant isolation, correlation, graph, actor records, anomaly/forecast, replay handling, triage, keyword evidence, marketplace, MCP, reports, AI and logout. CISA ingestion retrieved 1,710 real source records. Test tenants are removed after verification. See [detection details](docs/DETECTION_EXTENSIONS.md).

## External dependencies and current limits

- Local LM Studio completed a real SOC request. Ollama integration is implemented but its runtime is not running on this machine.
- The existing OpenAI key was reused, but the live API returned HTTP 429; the precise provider reason was unavailable. Gemini needs a configured key. These adapters are not a claim of successful live provider verification.
- No licensed dark-web provider is configured. Keyword matching and evidence import work, but there is no live dark-web coverage or autonomous crawling. Ingest approved evidence through Exposure Watch or `/api/v1/exposure/ingest`.
- CISA refresh, source validation, manual crawling and telemetry/source ingestion are explicit actions. There is no scheduled collection worker in this release.
- Marketplace extensions are bundled code; arbitrary third-party package installation and remote MCP process management are not implemented.
- Notification webhooks and scheduled reports return 501 until a delivery worker is implemented. Manual exports work. Legacy alert-rule definitions are stored but are not an active rule engine.

See [security](docs/SECURITY.md) for implemented controls and remaining production work. This locally verified application has not undergone a production penetration test, load qualification or live Kubernetes rollout.
