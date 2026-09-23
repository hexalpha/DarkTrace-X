# Copilot upgrade plan

Extend the existing FastAPI/Next.js application; retain all existing API contracts and database tables. Existing state: PostgreSQL tenant/user authentication and revocation, intelligence JSON records, CISA feed ingestion, Elasticsearch graph/correlation, telemetry detection, marketplace, MCP, reports, and a non-streaming provider gateway. Redis is present but not yet used by the API. Existing docs contain aspirational OIDC/queues/RLS descriptions that must be corrected before knowledge indexing. No licensed dark-web feed is configured. A 2.50 GB GGUF file is present and the host has an NVIDIA GTX 1650 (4 GB).

1. Add isolated, persistent GGUF inference worker, model health, CPU fallback, environment configuration and protected provider settings. Keep model loading out of API replicas.
2. Add scoped conversations/preferences/incident context, streaming/cancellation, gateway routing, bounded read-only SOC tools, explicit knowledge allowlist, source-attributed live retrieval, persistent deduplicated notifications, limits and audit/metrics.
3. Add authenticated floating copilot and /ai-command-center with history, Markdown, model settings, health/source/tool visibility and notification actions. Connect existing alert surfaces through Ask AI.
4. Verify existing and new paths using real services and isolated temporary tenants. Record exact evidence and limitations. Compute readiness from a published checklist: PASS=1, PARTIAL=0.5, FAIL/NOT TESTED=0; no unverified capability receives full credit.

Model tools cannot execute code, SQL, filesystem operations or administrative mutations. Provider settings are admin-only; keys are write-only and encrypted. Cloud use requires per-request opt-in. Conversation data is user/tenant scoped, redacted and deletable. No mock production intelligence is introduced.
