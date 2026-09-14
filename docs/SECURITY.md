# Security practices

## Security invariants

1. **No client-side secrets.** All LLM, feed, notification, database, and encryption credentials live in a workload-bound external secret manager.
2. **Tenant-first authorization.** Every query derives `tenant_id` from verified identity, never from a browser parameter. PostgreSQL RLS backs application checks.
3. **Provenance is immutable.** Store source, terms, collection timestamp, transformation, confidence, and analyst change history for every intelligence decision.
4. **Human authority remains decisive.** AI may summarize and prioritize. It cannot execute blocking, notification, enrichment, or export actions without policy checks and an authorized identity.
5. **Untrusted inputs are contained.** Parse feeds, files, archives, URLs, and metadata in isolated workers with CPU/memory/time/network limits; scan uploads and disable macros.

## Required production controls

- OIDC/SAML with MFA, SCIM lifecycle, short-lived sessions, service workload identity, and separate break-glass accounts.
- AES-256 envelope encryption for sensitive fields, TLS 1.2+ in transit, separate KMS keys per environment/tenant tier, scheduled rotation, and no plaintext key logs.
- Strict CSP, HSTS, `HttpOnly; Secure; SameSite=Lax` session cookies when cookies are used, CSRF protection for browser mutations, rate limits, request-size limits, and signed exports.
- Append-only audit stream exported to a separate security account; alert on privilege changes, bulk exports, API-key events, source changes, and cross-tenant authorization failures.
- Egress allowlists and per-connector credentials. Do not directly connect to anonymous networks or unapproved sources from the control plane.
- SBOM, dependency update policy, SAST/DAST, secret scanning, image signing, admission policy, runtime anomaly detection, and regular external penetration testing.
- Retention and deletion policy by data class. Classify data before AI use; redact personal data/secrets and record provider, model, policy version, and source references for each completion.

## AI safety controls

- Treat all retrieved intelligence as untrusted context; delimit and label it before model use to reduce prompt injection.
- Apply prompt/response policy filters for offensive requests, credential material, personal data, and prohibited automated actions.
- Limit AI tools to least-privilege, typed functions. Require user confirmation and approval policy for side effects.
- Use per-tenant provider routing, quotas, timeouts, circuit breakers, and structured logs without prompt/body secrets.
- Evaluate summaries and risk scoring against curated incident cases before deployment; monitor hallucination, citation coverage, refusal quality, bias, latency, and cost.

## Legal and ethical source policy

Monitor only public, licensed, customer-authorized, or otherwise legally permitted sources. Respect source terms, robots/rate limits where applicable, privacy law, breach-notification law, and data residency. The platform is designed for analysis and defensive response—not for purchasing leaked credentials, contacting criminal actors, bypassing access controls, or collecting illicit content.

