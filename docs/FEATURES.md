# Complete feature catalog

This catalog describes the September 23, 2026 local-preview source. Included behavior is not a guarantee of external-provider availability. Screenshots use an isolated documentation workspace.

| Workspace area | Included behavior | Boundary |
| --- | --- | --- |
| Overview | Counts, alert priority, telemetry, geography and assistant | Fresh workspaces have zero records. |
| Intelligence | Validated IOCs, provenance/confidence, exact correlation | No comprehensive global coverage claim. |
| Threat Hunt | Search recorded indicators/evidence | Works on supplied data, not arbitrary remote hosts. |
| Exposure Watch | Evidence imports and keyword matches | No licensed live dark-web provider bundled. |
| Asset Discovery | Asset inventory and associated evidence | No autonomous network-discovery agent. |
| Intel Graph | Scoped IOC relationships and graph | Relationships depend on source evidence. |
| CVE Dashboard | CISA KEV ingestion and display | Not complete NVD/EPSS/asset matching. |
| Threat Actors | Analyst records and reported techniques | Attribution remains an analyst/source claim. |
| Alert Center | Persistent alerts, triage, evidence, audit | Human review is required. |
| AI Anomalies | Statistical baselines, spikes and telemetry imports | Not a classifier with measured accuracy. |
| Threat Forecast | Evidence-linked trend prioritization | Not calibrated attack probabilities. |
| AI Studio | Provider-connected assistant interfaces | Cloud services require opt-in and credentials. |
| AI Command Center | Model/dependency status and provider/knowledge controls | CPU inference; CUDA remains unverified. |
| Floating Copilot | Streaming, history/search, stop/regenerate, sources, memory | Scoped read tools; no autonomous remediation. |
| Automations | Webhooks, report schedules and delivery-job status | Receivers/SMTP must be configured; legacy rules are not a complete rule engine. |
| MCP Servers | Authenticated built-in read-only server/tools | No arbitrary remote process management. |
| Marketplace | Three bundled extensions and enable/execute controls | No arbitrary third-party package installation. |
| Source Management | URL validation, source health, tags, priorities, policies | Approved public/licensed sources only. |
| Documents | Normalized content, provenance, hash deduplication | Content reflects retrieved sources. |
| Entities | Extracted indicators/CVEs and source links | Bounded by implemented parsers. |
| Events | Processing events and evidence links | Not an unconfigured enterprise SIEM stream. |
| Crawl Jobs | Manual/recurring crawl history and failures | Scheduler is embedded in API, not a distributed collection cluster. |
| Reports | PDF/DOCX/XLSX evidence exports | Scheduled email requires SMTP and verification. |
| Administration | User management and admin/lead/analyst/viewer roles | SSO/MFA and database RLS are absent. |
| Settings | Workspace controls, preferences and language selection | Secret/provider settings are role-scoped. |

## Platform capabilities

PostgreSQL persistence and Alembic migrations; Redis coordination; Elasticsearch correlation with optional TLS profile; HttpOnly browser sessions and CSRF protection; JWT validation/revocation; persistent audit records; durable webhook/report jobs with retries; REST, GraphQL, WebSockets and metrics; non-root application containers; backup/recovery helpers; Kubernetes manifests.

Historical reports may predate the session, migration, scheduler and delivery-worker implementations. See [release verification](RELEASE_VERIFICATION.md) for current checks. Production load, recovery qualification, live Kubernetes, GPU use and broad cloud-provider compatibility remain separate tasks.
