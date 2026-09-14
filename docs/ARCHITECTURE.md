# DarkTrace X architecture

DarkTrace X separates the operator-facing **experience plane**, the tenant-aware **intelligence control plane**, and the isolated **data/enrichment plane**. This keeps incoming untrusted intelligence, provider credentials, and analyst sessions from sharing a trust boundary.

```mermaid
flowchart LR
  Analyst["Analyst / Admin"] --> Edge["Nginx + WAF / OIDC"]
  Edge --> Web["Next.js Console\nDashboard · Graph · Reports"]
  Edge --> API["FastAPI Control Plane\nREST · GraphQL · WebSocket"]

  API --> Auth["RBAC + Tenant Context\nAudit Middleware"]
  API --> Intel["Intel Service\nIOCs · CVEs · Alerts · Cases"]
  API --> AI["AI Gateway\nPolicy · Memory · Failover"]
  API --> Queue["Redis Streams\nJobs · Notifications"]
  API --> PG[("PostgreSQL + pgvector\nSystem of record")]
  API --> Search[("Elasticsearch\nSearch / timeline")]

  Intel --> Workers["Isolated Enrichment Workers"]
  Workers --> Approved["Approved feeds / OSINT / internal telemetry"]
  Workers --> PG
  Workers --> Search
  AI --> Providers["OpenAI · Gemini · Claude · Groq\nOpenRouter · Local / custom LLM"]
  Queue --> Integrations["Email · Slack · Discord · Telegram · Webhooks"]
```

## Defensive data lifecycle

```mermaid
sequenceDiagram
  participant F as Approved source / connector
  participant W as Isolated worker
  participant C as Correlation engine
  participant A as Analyst console
  participant S as AI SOC assistant
  F->>W: Signed/polled intelligence item
  W->>W: Validate schema, provenance, allowlist, rate limits
  W->>C: Normalized observable + source confidence
  C->>C: Deduplicate, enrich, score, MITRE/CVE map
  C-->>A: Tenant-scoped alert/event
  A->>S: Analyst asks for defensive summary
  S-->>A: Grounded explanation with confidence and sources
  C->>A: Immutable audit event and case timeline
```

## Design decisions

- **Tenant boundary first:** every persisted intelligence object contains `tenant_id`; enforce it with PostgreSQL RLS in production and a request-scoped database role.
- **Provenance over volume:** raw source record, collection time, source terms, confidence, and transformation history are retained with each indicator.
- **AI is an assistive layer:** model calls are policy-scoped, sources are supplied as context, results are labeled as generated, and failover ends with an explicit unavailable status—never a fictional conclusion.
- **Async by default:** ingest, enrichment, export, and notifications run through queues so analyst interactions stay fast.
- **Zero trust between planes:** use workload identity, mTLS, egress allowlists, encrypted queues, and a dedicated secret manager in production.

