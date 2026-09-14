# Deployment guide

## Local validation

1. Create a local `.env.local` from `.env.example`; do not place secrets in Docker Compose or source control.
2. Run `docker compose up --build`.
3. Visit `http://localhost:8080`. The edge routes `/` to the web console and `/api/` to FastAPI.
4. Confirm `/api/v1/health/live`, `/api/v1/health/ready`, and `/metrics` from the internal network.

The included data is representative demo intelligence, not live intelligence. Add only approved, legally permitted integrations after the production controls below are in place.

## Kubernetes production baseline

```bash
kubectl apply -k infra/k8s
kubectl -n darktracex set image deployment/darktracex-api api=registry.example/darktracex/api:<immutable-sha>
kubectl -n darktracex set image deployment/darktracex-web web=registry.example/darktracex/web:<immutable-sha>
```

Before applying:

- Replace image placeholders with immutable digest-pinned images.
- Create `darktracex-runtime` using External Secrets, CSI Secrets Store, or the cloud secret manager—not a checked-in manifest.
- Point `DATABASE_URL`, `REDIS_URL`, and `ELASTICSEARCH_URL` at managed private services. Enable TLS and auth on all three.
- Use managed ingress/WAF with valid certificates; set `APP_ENV=production` and precise `CORS_ORIGINS`.
- Add network policies so only API/workers reach the data plane and only approved workers have internet egress.
- Run migrations as a signed, one-off job before rolling out API replicas.

## Scaling model

| Workload | Scale signal | Notes |
|---|---|---|
| Next.js console | CPU / request rate | Stateless; CDN-cache assets |
| FastAPI control plane | p95 latency / concurrent requests | Stateless; horizontal pods; use connection pooling |
| Enrichment workers | queue depth / oldest job age | Isolate untrusted parsers and connectors |
| PostgreSQL | IOPS / active sessions | Use HA, PITR, RLS, read replicas for reporting |
| Elasticsearch | shard pressure / query latency | Keep derived timeline indexes; ILM hot/warm/cold |
| Redis | stream lag / memory | Separate cache, rate-limit, and job pools when large |

## CI/CD gates

Every merge should run format, type, unit, dependency, secret, container, and IaC scans. A release promotion should require signed artifacts, SBOM, image digest attestations, migrations reviewed separately, canary health thresholds, and a rollback plan. The included GitHub Actions workflow is intentionally deployment-agnostic.

## Operations runbook

- **AI provider degraded:** mark the provider unavailable in the model panel, confirm fallback behavior, and preserve analyst requests in the conversation audit trail. Do not silently substitute provider output.
- **Feed source unhealthy:** pause its connector, retain the last successful provenance timestamp, and lower freshness—not confidence—until validation resumes.
- **Suspected tenant leak:** revoke active sessions, rotate service credentials, snapshot immutable audit storage, quarantine relevant queues/indexes, and investigate with a separate incident tenant.
- **Data retention request:** follow tenant contract and legal hold. Delete system-of-record rows through a logged workflow, then expire derived search/cache artifacts with verifiable job receipts.

