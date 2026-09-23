# DarkTrace X readiness report

Verified snapshot: 2026-09-16T10:30:09.183165+00:00

**DARKTRACE X STATUS: PARTIALLY READY — 76.87%**

## 1. Overall readiness
51.5/67 weighted points = **76.87%**. PASS=1, PARTIAL=0.5, FAIL/NOT TESTED=0, with every checklist row equally weighted. This measures verified coverage of the stated checklist, not security certification, model accuracy or probability of reliability.

Counts: {'PASS': 44, 'PARTIAL': 15, 'FAIL': 1, 'NOT TESTED': 7}.

## 2. Production ready
**NO.** The local Docker installation runs real inference and core workflows, but external providers, licensed collection, production security/deployment and several advanced capabilities remain incomplete. Do not interpret a working local dashboard as an enterprise production deployment.

## 3. Working features

| Feature | Status | Exact evidence or limitation |
|---|---|---|
| Frontend production build | PASS | Optimized Next.js build completed locally and in Docker, including /ai-command-center; final PostCSS override build passed. |
| TypeScript | PASS | pnpm typecheck exited 0. |
| Lint | PASS | pnpm lint exited 0 with no project lint warnings. Next build notes that its optional framework ESLint plugin is not configured. |
| Backend startup and REST routes | PASS | FastAPI startup and authenticated REST workflows verified through Nginx. |
| Python compilation and unit tests | PASS | Backend compilation passed; the prior deployed Docker suite had 28 backend tests and 3 model-worker fault tests, and 4 new webhook/report-schedule validation tests pass locally. Docker rebuild of the latest API change is pending host usage approval. |
| Authentication and logout | PASS | Live registration/login/logout/revocation tested; expired, missing-claim, wrong issuer/audience and unsigned token tests passed. |
| RBAC | PASS | Live role changes take effect on existing sessions; viewer model writes and knowledge reindex return 403. |
| Tenant and user isolation | PASS | Two isolated live workspaces tested across IOC, graph, actors, alerts, tools, conversations and notifications; unauthorized conversation access returns 404. |
| PostgreSQL | PASS | Real connection, writes, deletes, scoped reads and readiness verified. |
| Redis | PASS | Real ping, request counters and active-generation lease checks passed; memory mutation rejects an active generation. |
| Elasticsearch | PASS | Real connection and tenant-scoped IOC correlation/graph queries passed. |
| WebSocket | PASS | Authenticated /ws/events delivered a telemetry.pulse through Nginx. |
| GraphQL | PASS | Authenticated dashboard query passed through Nginx; anonymous query returned 401. |
| Local GGUF loading | PASS | The supplied 2,497,277,408-byte Qwen GGUF loaded once in the persistent worker; ONLINE on CPU. |
| Local inference | PASS | Actual answer after chat-template fix: PostgreSQL is connected. A verified API response took 20,773 ms; browser response took about 24.4 seconds. |
| Missing/corrupt model handling | PASS | Separate missing-file container returned OFFLINE; simulated corrupt-model load returned ERROR without crashing the API. |
| Provider fallback and privacy | PASS | Tests cover cloud opt-in, local-only fallback, unreadable encrypted-key fallback and no second answer after partial generation failure. |
| Streaming chat | PASS | Real local generation delivered SSE deltas, sources, completion and persisted messages through Nginx and the browser. |
| Floating assistant and responsive workspace | PASS | Authenticated floating panel, minimize/expand and desktop/mobile layout inspected. /ai-command-center is included in the production build. The latest source locks the sidebar and topbar to the viewport, gives the workspace its own scroll surface, and adds a mobile navigation drawer; the updated image should be rebuilt before live browser recheck. |
| Conversation history/search | PASS | Live messages persisted; history search matched; cross-tenant reads/deletes rejected. Browser history survived container recreation. |
| Stop and regenerate controls | PASS | Browser Stop cancelled a generation; regeneration of the persisted local conversation completed with source attribution in 25.8 seconds. Cross-provider cancellation stress testing remains part of the untested load exercise. |
| Memory controls | PASS | Scoped preferences/redaction/deletion and disabled legacy chat persistence passed; active generation prevents deletion races. Audit records are intentionally retained. |
| Provider configuration and secret storage | PASS | Live admin settings, encrypted ciphertext storage, secret-presence-only reads and validation non-echo verified; terminal helper supports hidden key entry. |
| Project knowledge/RAG | PASS | Explicit allowlist and lexical retrieval verified; .env exclusion tested. API and schema docs corrected to actual implementation. This is lexical retrieval, not vector embeddings. |
| AI proactive notifications | PASS | Real scoped operational alert generated a notification; snooze, mute, dismiss/resolve authorization and event-only behavior verified. |
| Notification deduplication | PASS | Repeated and concurrent polling produced one notification; per-user database serialization enforces cooldown decisions. Sustained multi-user rate-load testing not performed. |
| Live intelligence | PASS | Actual CISA retrieval returned records, source URL and retrieval timestamp. Coverage is CISA KEV, not comprehensive current cybersecurity news. |
| Threat feed ingestion | PASS | Real CISA ingestion retrieved 1,710 source records during the full smoke workflow; no generated production detections. |
| IOC functionality and correlation | PASS | Persistence, exact correlation, source metadata and tenant isolation passed with real PostgreSQL/Elasticsearch. |
| CVE dashboard | PASS | Real CISA records displayed; missing CVSS/EPSS values are not fabricated. This is not a complete NVD/asset-version matching service. |
| Reports | PASS | Authenticated PDF, DOCX and XLSX outputs returned expected file signatures and recorded evidence. Pixel-by-pixel layout review not repeated in this audit. |
| Threat map data | PASS | Source-reported telemetry coordinates are validated, tenant/time scoped and plotted on a latitude/longitude grid. Real database replay counts, provenance and tenant isolation passed; browser import and empty/populated views verified. No automatic IP geolocation or verified attacker-origin claim. |
| Intelligence graph and actors | PASS | Persisted IOC relationships and analyst-supplied actor records passed tenant-scoped live tests. |
| AI anomaly detection | PASS | Statistical baselines, spikes, cold start, stale evidence, entity isolation and telemetry-to-alert flow passed. No machine-learning accuracy claim is made. |
| MCP integration | PASS | Authenticated built-in read-only MCP lifecycle, schemas, tool execution and tenant isolation passed. |
| Audit logging | PASS | Authentication/operations/copilot changes write scoped audit records. Immutable external audit retention is not configured. |
| Health endpoints | PASS | Live/readiness and authenticated copilot dependency/model status endpoints verified. |
| Docker images and Compose | PASS | API, web and local-LLM images built; all seven services started. API/web/worker run as non-root. Compose validation passed. |
| Nginx configuration | PASS | nginx -t passed; REST/SSE/WebSocket/GraphQL paths verified. Gateway binds only to 127.0.0.1:8080. |
| Persistent volumes | PASS | Existing PostgreSQL/Redis/Elasticsearch named volumes preserved across recreation; saved QA conversation survived. Disaster recovery restore was not tested. |
| Environment configuration | PASS | Configurable model/runtime settings, generated persistent worker/encryption/signing keys and non-overwriting setup verified. Secrets are not returned in reports. |
| Frontend dependency audit | PASS | PostCSS upgraded via override to 8.5.28; final pnpm production audit reports zero known vulnerabilities. |
| Backend dependency audit | PASS | Patched FastAPI/Starlette/PyJWT/pip image scanned after remediation; see security verification evidence below. |
| No fake production intelligence | PASS | Empty workspaces remain empty; CISA data is sourced; test evidence is isolated and cleaned. Unavailable integrations are labeled. |

## 4. Partially working features

| Feature | Status | Exact evidence or limitation |
|---|---|---|
| GPU acceleration | PARTIAL | Backend capability detection and simulated GPU allocation failure/CPU retry pass. Actual CUDA/GPU inference was not tested; bundled image is CPU-only. |
| Unified AI gateway | PARTIAL | New copilot and default legacy dashboard chat share private primary/fallback/offline routing. Explicit legacy-provider requests retain their older environment configuration for compatibility. |
| Provider adapter protocols | PARTIAL | Fixture parsing tests pass for GGUF, Ollama, Gemini, Anthropic, Groq, OpenRouter, custom and LM Studio. Fixtures do not establish live cloud service compatibility; OpenAI Responses has no dedicated streaming fixture. |
| LM Studio live completion | PARTIAL | Discovery and earlier real completion passed, but the final explicit LM Studio regression timed out (HTTP 503 response_timeout). The built-in GGUF worker is the verified default; optional host-runtime reliability remains unresolved. |
| Markdown/code/copy rendering | PARTIAL | Safe Markdown pipeline, code highlighting and copy control implemented; real prose rendering inspected. Comprehensive malicious-Markdown/browser clipboard tests not performed. |
| SOC tools/function calling | PARTIAL | Strict read-only tools, bounded arguments, authenticated data retrieval and forbidden tool rejection verified. Autonomous multi-round model tool selection has not received a full semantic evaluation. |
| Outbound webhook delivery | PARTIAL | Admin HTTPS subscriptions, encrypted signing secrets, SSRF protection, severity/event filters, signed payloads and failure tracking are implemented with unit validation. The updated API image could not be rebuilt/live-tested in this turn because Docker approval is blocked by the host usage limit; external receiver delivery remains unverified. |
| Ask AI alert explanation | PARTIAL | Alert-center button and structured authorized alert lookup implemented. Full incident-quality/MITRE explanation evaluation not performed; model assessments remain untrusted. |
| Dark-web monitoring pipeline | PARTIAL | Approved evidence import, keyword matches, provenance, deduplication and tenant isolation passed. No licensed live dark-web collector exists; live coverage is UNAVAILABLE. |
| Predictive threat engine | PARTIAL | Evidence-linked trend forecast and persistence pass. Forecast is not a calibrated probability or independently validated prediction of future attacks. |
| Plugin marketplace | PARTIAL | Three real built-in extensions install/enable/disable/execute correctly. Arbitrary third-party plugin distribution, signing and sandboxing are not implemented. |
| Observability | PARTIAL | Persistent latency/usage/tool history, event metrics and health are implemented. Local token counts are unavailable, not estimated; production scrape/retention/load monitoring not deployed. |
| Database migrations | PARTIAL | Additive SQLAlchemy create_all bootstrap works, including copilot_records. Versioned upgrade/rollback migrations are absent. |
| Basic application security | PARTIAL | RBAC, scoped queries, strict schemas, rate limits, size limits, redaction and encrypted provider keys tested. TLS, SSO/MFA, RLS, immutable audit and a penetration test remain outstanding. |
| Kubernetes deployment | PARTIAL | Eight YAML resources parse, including a non-root local GGUF worker Deployment, protected model PVC, separate worker-secret contract and API-to-worker NetworkPolicy. No cluster rollout, TLS, external-secret, network-policy enforcement or GPU scheduling test. |

## 5. Broken/unavailable requested features

| Feature | Status | Exact evidence or limitation |
|---|---|---|
| OpenAI live completion | FAIL | The already configured key returned HTTP 429, reason unclassified. No successful cloud completion verified; account/provider quota must be resolved externally. |

## 6. Features not tested

| Feature | Status | Exact evidence or limitation |
|---|---|---|
| Gemini live completion | NOT TESTED | No configured working Gemini key available; protocol fixture only. |
| Anthropic live completion | NOT TESTED | No configured working Anthropic key available; protocol fixture only. |
| Groq live completion | NOT TESTED | No configured working Groq key available; protocol fixture only. |
| OpenRouter live completion | NOT TESTED | No configured working OpenRouter key available; protocol fixture only. |
| Custom endpoint live completion | NOT TESTED | No configured authorized custom service available; protocol fixture only. |
| Ollama live completion | NOT TESTED | No Ollama runtime responded at the configured host endpoint; protocol fixture only. |
| Production load/backup recovery | NOT TESTED | No representative concurrency benchmark, failover exercise or database restore environment supplied. |

## 7. Security concerns

- Local Compose is bound to loopback and remains a development profile. PostgreSQL uses a development password; Elasticsearch security is disabled on its internal network. Configure unique service credentials and TLS before any shared deployment.
- A short API signing key was replaced with a strong persistent key; existing accounts remain, but old sessions require sign-in again. Provider secrets use Fernet; protect the master key and host file permissions.
- JWT sessions use browser localStorage. No SSO/MFA, database RLS, immutable audit sink, penetration test or production retention policy is supplied.
- Model output and retrieved text are untrusted. Prompt policy is defense in depth, not a guarantee against injection. No model tool can execute shell, SQL, Python or privileged writes. Secret redaction is heuristic; never paste credentials.
- Frontend dependency scan initially found four PostCSS advisories; patched override removed the findings. Backend scan initially reported 33 findings (including duplicate advisory IDs) in four packages; vulnerable JWT dependencies were removed and the HTTP/runtime packages patched. A dependency scan does not audit container OS packages or application logic.

## 8. Missing dependencies

No dependency is missing for the verified Docker CPU workflow. A CUDA-enabled llama.cpp build and GPU container setup are required for actual GPU acceleration. Ollama is not running. Production ingress/TLS, Kubernetes cluster, secret manager and backup infrastructure are not supplied.

## 9. Required external services

Docker supplies PostgreSQL, Redis, Elasticsearch and the GGUF worker. Public CISA access is needed for fresh vulnerability intelligence. Cloud models require valid provider credentials, quota and egress. Live dark-web coverage requires an authorized licensed feed/collector; none is configured. LM Studio must remain running for its optional fallback.

## 10. Environment variables

Required/configured variables: `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL`, `ELASTICSEARCH_URL`, `COPILOT_WORKER_KEY`, `AI_SECRET_KEY`, `LOCAL_LLM_ENABLED`, `LOCAL_LLM_MODEL_PATH`, `LOCAL_LLM_SERVICE_URL`, `LOCAL_LLM_CONTEXT_SIZE`, `LOCAL_LLM_THREADS`, `LOCAL_LLM_GPU_LAYERS`, `LOCAL_LLM_TEMPERATURE`, `LOCAL_LLM_MAX_TOKENS`, `PROJECT_KNOWLEDGE_ROOT`.
Optional integrations: `LOCAL_LLM_CHAT_FORMAT`, `AI_ENDPOINT_ALLOWLIST`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `CUSTOM_LLM_API_KEY`, `LM_STUDIO_BASE_URL`, `OLLAMA_BASE_URL`.
Run setup once. It preserves `.runtime/copilot.env` and `.runtime/api-security.env`; do not commit these files. `.env.local` is server-only. Model path uses Compose environment interpolation; pass `--env-file .env.local` when storing model overrides there. No secret values are included in this report.

## 11. Docker/container status

Seven local services: api, web, nginx, postgres, redis, elasticsearch and local-llm. API/database/cache/search readiness verified. Application/worker processes are non-root; database/search volumes are preserved. Only Nginx publishes a host port (127.0.0.1:8080). The model worker exposes authenticated health internally; it does not have a Docker HEALTHCHECK instruction.

## 12. Local LLM results

Model: `qwen3-4b-cybersecurity-heretic-16bit-q4_k_m.gguf`, metadata name Qwen3 4B Cybersecurity Heretic 16bit. Runtime llama-cpp-python 0.3.35, CPU, context 4096, default four threads. The export omitted tokenizer.chat_template; architecture-aware ChatML fallback fixed repeated Llama-2 formatting tokens. Real API response: “PostgreSQL is connected.” (20,773 ms in one recorded run); browser answer: “Yes, PostgreSQL is connected.” (~24.4 seconds). This is a functional smoke test, not a cybersecurity reasoning benchmark. Missing-file and corrupt/GPU fault paths tested separately. Local token counts are unavailable and not fabricated.

## 13. Cloud AI provider results

OpenAI: actual HTTP 429, exact provider reason unclassified. Gemini/Anthropic/Groq/OpenRouter/custom: no live credential-backed completion tested. Protocol fixtures cover their parsers except OpenAI Responses. No keys were created, purchased, exposed or sent to the browser. Local privacy routing and fallback tests passed. Explicit LM Studio completion timed out in the final legacy-provider run; default GGUF completion is verified independently.

## 14. Database/Redis/Elasticsearch

All three responded ONLINE. Live tests wrote scoped records, correlated in Elasticsearch and removed only temporary tenants. Public CISA feed records remain. Redis enforces rate limits and active-generation coordination; copilot fails closed if Redis is unavailable. Backup/restore and multi-node failure recovery are not tested.

## 15. Frontend build

PASS: production Next.js build, TypeScript and lint were verified in the deployed Docker image; the latest source typecheck and lint pass locally. A local Next worker cannot spawn in this restricted Windows runtime (EPERM), so the updated image requires Docker rebuild before a live browser recheck. Final production dependency audit: zero reported advisories. No full visual regression suite or accessibility certification was performed.

## 16. Backend tests

The prior deployed Docker suite passed 28 backend unit tests and three inference-worker fault tests; 4 new webhook/report-schedule validation tests pass locally. A Windows sandbox run encountered a temporary-folder permission error in one knowledge test; the complete pre-webhook suite passed in the deployed Linux image. The updated API image could not be rebuilt in this turn because the host usage limit blocked Docker approval. `scripts.smoke_workspace` covers authentication, RBAC, IOC/assets/hunts, graph/actors, detection/forecast, monitoring imports, CISA/CVEs, reports, plugins/MCP, local provider and logout. `scripts.verify_copilot` covers GraphQL/WebSocket, health, RAG, live CISA retrieval, strict tools, admin/tenant checks, request size, encryption, notifications, actual GGUF streaming/persistence, memory coordination and default legacy routing. Synthetic evidence is confined to disposable QA tenants.

## 17. Known bugs and limits

Automatic IP geographic enrichment and country-boundary basemaps are not supplied; geography uses explicit collector coordinates. There is no versioned database migration engine, complete arbitrary-plugin sandbox, automatic collection scheduler or calibrated predictive threat score. Report schedules are durably registered but remain pending until an SMTP/approved delivery worker is configured. Explicit legacy AI provider requests still use legacy environment settings. GPU inference, cross-provider regeneration/cancellation stress behavior, autonomous multi-round tool reasoning and comprehensive malicious-Markdown tests remain unverified. Large prompts can exceed the conservative context budget or time out on this CPU. Model generation is serialized. The Windows portable launcher is a separate installation and is not the verified copilot entrypoint; it requires Redis/worker configuration for new copilot functionality. The current running container may still serve the previous web image until Docker Desktop is available for a rebuild.

## 18. Recommended fixes

Resolve the OpenAI service error and validate each desired cloud provider with synthetic evidence. Connect a licensed monitoring source. Add production TLS/credentials/SSO/MFA, reviewed migrations and tested backups. Add optional approved geographic enrichment, a production collection queue and external notification delivery. Validate GPU offload and run realistic concurrency, adversarial model/tool and incident-answer evaluations. Deploy external Redis with TLS and validate the Kubernetes worker PVC upload, secret manager, rollout, ingress TLS and GPU scheduling on the target cluster.

## 19. Exact run commands

From PowerShell on this existing workspace (Docker Desktop running, existing `.env.local` and GGUF file present):

```powershell
cd "D:\CyArt\DARKTRACE X"
python scripts/setup_copilot.py
docker compose --env-file .env.local up -d --build --wait
docker compose ps
```

Open the gateway and sign in with the existing Docker workspace account, or register a new empty workspace. The port-3000 Windows installation uses a different database. Verification commands:

```powershell
docker compose -f docker-compose.yml -f docker-compose.verify.yml run --rm --no-deps verify python -m unittest discover -s tests -v
docker compose -f docker-compose.yml -f docker-compose.verify.yml run --rm --no-deps verify python -m scripts.verify_copilot
docker compose -f docker-compose.yml -f docker-compose.verify.yml run --rm --no-deps verify python -m scripts.smoke_workspace
```

Frontend checks:

```powershell
cd "D:\CyArt\DARKTRACE X\apps\web"
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm build
pnpm audit --prod
```

To stop without deleting data: `docker compose stop`. Never use `down -v` when preserving database/search data.

## 20. URLs and ports

| Service | URL/address | Published on host |
|---|---|---|
| Dashboard / gateway | http://localhost:8080/ | Yes, loopback only |
| AI Command Center | http://localhost:8080/ai-command-center | Yes, loopback only |
| REST | http://localhost:8080/api/v1 | Yes, loopback only |
| GraphQL | http://localhost:8080/graphql | Yes, loopback only |
| WebSocket | ws://localhost:8080/ws/events | Yes, loopback only |
| API | http://api:8000 | No, internal only |
| Web | http://web:3000 | No, internal only |
| GGUF worker | http://local-llm:8091 | No, internal only |
| PostgreSQL | postgres:5432 | No, internal only |
| Redis | redis:6379 | No, internal only |
| Elasticsearch | http://elasticsearch:9200 | No, internal only |

Supporting documentation: [Copilot](COPILOT.md), [API](API.md), [Database](DATABASE.md), [Deployment](DEPLOYMENT.md), [machine-readable report](readiness-report.json).

No claim is made that source-code presence alone establishes a working integration.
