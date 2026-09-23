# Security implementation and deployment requirements

## Implemented

Protected REST endpoints, GraphQL and MCP require a signed bearer token. Authentication checks expiry, issuer/audience, revocation, active user and active tenant. Authorization uses the current database role, so role changes affect existing sessions. Tenant identity comes from the authenticated user. Application queries scope private intelligence, telemetry, alerts, extensions and conversations to that tenant; public CISA records are shared.

Passwords are hashed. AI and database credentials stay on the server. Local secrets are generated under ignored `.runtime`. Logout stores a token digest for revocation. Conversation history is scoped to tenant and user. Selecting a local AI provider does not allow cloud fallback unless explicitly configured. Analysts should review supplied evidence and AI responses.

Telemetry has batch, value and timestamp validation. MCP has a bounded request body, origin checks and read-only tools. Marketplace execution uses three bundled handlers with no network egress. Source import records provenance and deduplicates keyword alerts. Audit events are persistent application records. XLSX cells escape formula prefixes; PDF text is escaped before rendering.

Admin webhook subscriptions are tenant-scoped and accept HTTPS endpoints only. URLs cannot contain credentials, query strings or fragments and local, private or metadata targets are rejected at registration and delivery. Each subscription supplies a 32-character shared secret that is encrypted with the existing AI secret key and never returned. Alert payloads are redacted, signed with HMAC-SHA256 and sent without redirects; failures are counted for operator review. Supported filters are explicit event names or `*` with a minimum severity threshold. Use `POST /api/v1/integrations/webhooks`, `GET /api/v1/integrations/webhooks` and `DELETE /api/v1/integrations/webhooks/{id}` as an administrator.

Report schedules are now durably registered per tenant with bounded five-field cron syntax, validated recipients and audit records. They return `delivery_status=pending_external_delivery` until an SMTP or approved delivery worker is configured; no report is claimed as sent without that service. Use `POST /api/v1/reports/schedules`, `GET /api/v1/reports/schedules` and `DELETE /api/v1/reports/schedules/{id}` as a lead or administrator.

Prepared Windows services bind to loopback. Local Elasticsearch security is disabled and must remain loopback-only. Container and Kubernetes application processes use non-root users; manifests include probes and network policy.

## Remaining production requirements

PostgreSQL row-level security is not enabled: tenant isolation currently depends on application query filters. Audit records are not immutable or cryptographically signed. Database fields are not envelope-encrypted. The browser stores its bearer token locally; this is not an HttpOnly cookie session. OIDC/SAML, MFA, recovery flows, SCIM and centralized secret management are not implemented. Source ingestion is not an isolated malware-analysis sandbox. No compliance certification, independent penetration testing or predictive accuracy is claimed.

Before an internet-facing rollout, configure HTTPS and trusted ingress, authentication rate limits, request limits, protected metrics, database/search authentication and TLS, restricted egress, monitored backups with tested restores, retention policies and secret rotation. Add SSO/MFA and tenant RLS for the intended operating model. Review dependencies and run penetration and capacity tests against the actual deployment. Lock down self-service registration if invitation-only onboarding is required.

No licensed dark-web collection service is connected. Feed access and retention obligations must match the selected source. A source type entered during import is provenance supplied by the uploader; it does not independently verify their license.
