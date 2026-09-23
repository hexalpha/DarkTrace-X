# DarkTrace X architecture

Next.js provides the authenticated analyst dashboard, feature workspaces and persistent floating copilot. /ai-command-center opens the expanded copilot using the same authentication gate. Nginx forwards REST and streaming traffic to FastAPI; GraphQL and WebSocket are separate API entry points.

FastAPI validates locally issued JWTs against current PostgreSQL users, tenant activity and revocation records. Viewer, analyst, lead and administrator permissions remain enforced by the existing dependencies. PostgreSQL stores users, intelligence, alerts, source evidence, telemetry, conversations and copilot configuration. Elasticsearch holds tenant-scoped IOC and actor indexes. Redis backs copilot rate limits and per-user generation leases.

The copilot extends existing services through explicit read-only tools: alerts, IOC records, CVEs, feeds, actors, health, mentions, events, assets, project knowledge and live CISA retrieval. It cannot execute shell commands, Python, SQL, arbitrary filesystem reads or administrative operations. Tool arguments do not accept tenant IDs. The caller supplies tenant/user scope through authentication.

One isolated inference worker loads the configured GGUF once and serializes requests. It resets model KV state per request and accepts only API-authenticated internal calls. Generation is streamed through the API with cancellation and timeouts. CPU inference is always supported by the default image. GPU offload is attempted only when the installed backend supports it; failed GPU loading falls back to CPU. The supplied CPU build is not proof of GPU acceleration.

The unified copilot gateway supports local GGUF, Ollama, LM Studio, OpenAI, Gemini, Anthropic, Groq, OpenRouter and custom compatible endpoints. Tenant administrators configure primary/fallback/offline slots. Cloud transmission is opt-in per request. Stored provider keys are encrypted; existing environment keys are referenced without returning them to the browser. The legacy AI endpoints remain available for compatibility.

Project RAG uses lexical TF-IDF retrieval from an explicit documentation allowlist; it does not crawl the filesystem or index .env files. Notifications come from real high/critical operational alerts or failed service probes, with persistent deduplication, source cooldown and user mute/snooze controls. Source dates and retrieval timestamps accompany retrieved intelligence. No licensed dark-web collector is configured; imported approved evidence can be analyzed.

Not implemented: OIDC/SAML/MFA, PostgreSQL RLS, immutable audit storage, arbitrary third-party extensions, scheduled reports/webhook delivery workers, geographic threat enrichment or autonomous dark-web crawling. These are not implied by the presence of infrastructure manifests.
