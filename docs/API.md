# API reference

The API is versioned under `/api/v1`. Interactive OpenAPI documentation is available at `/docs` outside production. The REST service serves analyst applications; worker-to-worker traffic should use mTLS, workload identity, and a separate internal gateway.

## Authentication and tenancy

Production requests require an OIDC-issued bearer token. DarkTrace X exchanges the identity-provider token at the edge or validates its JWKS, then binds these claims to every request:

| Claim | Purpose |
|---|---|
| `sub` | Immutable user/service identity |
| `tenant_id` | Mandatory row-level-security scope |
| `role` | `viewer`, `analyst`, `lead`, or `admin` |
| `email` | Audit display identity |

The development profile intentionally uses a visible demo analyst only when `APP_ENV` is not `production`. There is no anonymous production path.

## REST endpoints

| Method | Path | Role | Purpose |
|---|---|---:|---|
| `GET` | `/health/live` | public network probe | Process liveness |
| `GET` | `/health/ready` | internal probe | Dependency readiness |
| `GET` | `/dashboard/overview` | viewer+ | Tenant-scoped command-center metrics and timeline |
| `GET` | `/iocs?q=` | viewer+ | Search normalized indicators |
| `POST` | `/iocs` | analyst+ | Create a manually validated IOC |
| `GET` | `/alerts?severity=` | viewer+ | Priority alert queue |
| `GET` | `/cves` | viewer+ | CVE risk and mitigation intelligence |
| `GET` | `/ai/providers` | viewer+ | Configured provider capability status; no secrets |
| `POST` | `/ai/chat` | viewer+ | Defensive SOC assistant with failover |
| `POST` | `/integrations/webhooks` | admin | Register an outbound alert webhook |
| `GET` | `/metrics` | internal only | Prometheus scrape endpoint |
| `WS` | `/ws/events` | viewer+ | Tenant-scoped telemetry/event stream |
| `POST` | `/graphql` | viewer+ | Read-oriented GraphQL endpoint |

### Create IOC

```json
POST /api/v1/iocs
Authorization: Bearer <access-token>

{
  "type": "domain",
  "value": "suspicious.example",
  "confidence": 82,
  "tags": ["phishing", "brand-watch"],
  "source": "analyst-validation"
}
```

The service normalizes the observable, attaches analyst provenance, scores it through the correlation policy, and writes an audit event. Live deployments must validate each type (IP parser, PSL-aware domain parser, canonical URL, hash length/algorithm) before persistence.

### Ask the AI SOC assistant

```json
POST /api/v1/ai/chat
{
  "message": "Summarize the latest alert and safe first containment checks.",
  "provider": "openai",
  "model": "gpt-5.6",
  "source_refs": ["alert:01J...", "ioc:01J..."],
  "language": "en"
}
```

Response fields identify the provider/model used and whether failover occurred. `503` means no configured provider completed the request; the client must surface that condition rather than treating it as analysis. The provider gateway only accepts server-side keys and keeps model errors out of analyst-facing payloads.

### GraphQL

```graphql
query CommandCenter {
  dashboard {
    protectedAssets
    activeAlerts
    riskScore
    eventRate
  }
}
```

Expand GraphQL only through persisted queries in production; disable the explorer and apply the same tenant/RBAC context as REST.

## Event contracts

WebSocket payloads use a namespaced event type, UTC timestamp, monotonic sequence number, `tenant_id` only on the internal bus, and typed data. Browser payloads never expose tenant ids or raw source credentials.

```json
{
  "type": "alert.created",
  "id": "evt_01J...",
  "occurred_at": "2026-09-14T05:00:00Z",
  "data": { "alert_id": "01J...", "severity": "high", "score": 84 }
}
```

Use an outbox table plus idempotency key for at-least-once delivery. Verify outbound webhook signatures with `X-DarkTrace-Timestamp` and an HMAC over the raw body; rotate a webhook secret independently for each subscription.

