# Deployment

## Verified local installation

On this Windows machine, run `./start-local.ps1` from the project root. It starts portable PostgreSQL and Elasticsearch plus the API and production-built Next.js dashboard. Open http://localhost:3000 and create your workspace. Logs are under `.runtime`. The launcher verifies service readiness. It uses separate loopback ports and does not replace system database services.

Backend changes require `./start-local.ps1 -RestartApi`. Frontend changes require `npm run build` in `apps/web` and restarting the project-owned Next.js server. Preserve `.runtime/postgres-data`, `.runtime/postgres.password` and `.runtime/jwt.key`. Use database-native backups rather than copying a running data directory.

The API reads server configuration from its environment settings. Never put AI keys into `NEXT_PUBLIC_*` settings. The Windows launcher overrides database, search, JWT and local origins for this isolated installation. Cloud keys remain in the existing server configuration.

## Containers and Kubernetes

Docker Desktop is now running. Both Linux application images built successfully, and all seven Compose services are running. The API readiness probe checks PostgreSQL and Elasticsearch. API and web run as UID 10001. The Docker dashboard is available at http://localhost:8080 through Nginx, bound to loopback.

On 2026-09-15, the complete Docker integration workflow passed through Nginx: registration/login, immediate role changes, tenant isolation, IOC correlation and graph, actor profiles, anomaly/forecast, replay protection, alert triage, source matching, marketplace, MCP, 1,710 live CISA records, PDF/DOCX/XLSX exports, local LM Studio completion, conversation isolation and logout revocation. Temporary test workspaces were removed. Two AI regression tests also passed inside the image, covering empty/truncated responses and preventing cloud fallback on local-provider timeouts.

The Windows dashboard on port 3000 and Docker dashboard on port 8080 use separate databases. Existing Docker volumes were preserved during the update; Windows data was not migrated. Use the workspace/account belonging to the chosen installation, or create a workspace there.

Start or update Docker with `python scripts/setup_copilot.py` followed by `docker compose --env-file .env.local up -d --build --wait`. Stop services without deleting data with `docker compose stop`. Do not use `down -v` unless you intend to erase the Docker database/search volumes. For container integration verification, run `docker compose -f docker-compose.yml -f docker-compose.verify.yml run --rm --no-deps verify`. This uses isolated temporary test tenants and removes them afterward.

The API has an outbound network for public feeds and configured AI providers. Database, Redis and Elasticsearch remain on the internal network with no published ports. Local AI endpoints use `host.docker.internal` to reach Windows-hosted runtimes. Kubernetes rollout remains unverified; Docker verification does not establish Kubernetes readiness.

Local OpenAI-compatible models default to 128 output tokens to accommodate slower hardware within the response timeout. Set `LOCAL_AI_MAX_OUTPUT_TOKENS` in server configuration to adjust this (32–4096); increasing it can cause timeouts on slow hardware. Responses that hit the length limit include an explicit notice. Provider timeouts are reported as `response_timeout` without exposing credentials or provider request payloads.

For Compose, set non-placeholder secrets from `.env.example`, review published ports, then use `docker compose up --build`. For Kubernetes, follow `infra/k8s/README.md`: supply actual images, namespace secrets, external PostgreSQL and Elasticsearch endpoints, ingress hostname and TLS. Ensure network policy permits those dependencies. Configure probes against the deployed API prefix.

Database startup creates missing tables with a PostgreSQL advisory lock to serialize replicas. This is not a versioned schema migration system. Introduce reviewed migrations before changing existing columns in production, and test upgrade/rollback against a backup.

## Verification

From `apps/api`, run `.venv313/Scripts/python -m unittest discover -s tests -v`. Live integration: `.venv313/Scripts/python -m scripts.smoke_workspace`; this needs local services, outbound CISA access and a working LM Studio chat model. It creates isolated temporary workspaces and removes their records afterward, retaining public CISA data.

From `apps/web`, run `npm run typecheck` and `npm run build`. Both passed here. Live tests also passed for persistence, tenant isolation, roles, detection, reports and local AI completion. See the root README for feature limits and `SECURITY.md` for remaining production controls.

## Copilot deployment

See COPILOT.md for all LOCAL_LLM_* settings. The local-llm service runs on internal port 8091 with one persistent CPU model worker; no host port is published. The GGUF file is mounted read-only and excluded from version control. The API also needs Redis for copilot rate limits and generation leases, COPILOT_WORKER_KEY for service authentication, AI_SECRET_KEY for encrypted provider keys, and the read-only knowledge mount. The Windows portable launcher has not been upgraded to launch the GGUF worker or Redis; use Docker for the verified copilot deployment.

Run `docker compose -f docker-compose.yml -f docker-compose.verify.yml run --rm --no-deps verify python -m scripts.verify_copilot` for the new live verification. Kubernetes manifests predate the GGUF worker and require additional service, secret and persistent-model-volume configuration before cluster use.
