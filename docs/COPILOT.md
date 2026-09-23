# Local cybersecurity copilot

Open the bottom-right DARKTRACE AI button on an authenticated page, or /ai-command-center. Conversations and incident context are scoped to the signed-in user and workspace. Search history, start a conversation, stop generation, regenerate a saved response, copy Markdown, expand/minimize the panel, or delete conversations. Settings in the Command Center control memory and deletion; disabled memory does not retain new chat messages. Secret redaction is a defense-in-depth heuristic: do not paste credentials into chat.

Settings → AI configures the local Qwen model or one optional OpenAI-compatible external provider. Only administrators can change these settings. External keys are write-only, masked in the UI, encrypted at rest, and never returned to browser JavaScript. External AI is disabled by default and is never selected automatically. There is no cloud fallback.

The default provider is `local`, backed by the Qwen3 4B Cybersecurity Heretic 16bit worker. If it is unavailable, the API returns a clear unavailable response. Older persisted provider names are normalized for compatibility, but no legacy provider adapter or endpoint is executed.

## Local worker

LOCAL_LLM_ENABLED enables the service. LOCAL_LLM_MODEL_PATH selects the GGUF path in the Compose environment (default supplied model filename); it is mounted read-only. LOCAL_LLM_CONTEXT_SIZE defaults to 4096, LOCAL_LLM_THREADS to 4, LOCAL_LLM_GPU_LAYERS to -1, LOCAL_LLM_TEMPERATURE to 0.2 and LOCAL_LLM_MAX_TOKENS to 512. Use `docker compose --env-file .env.local up -d --build` if these values are stored in .env.local. The worker runs once, not per request; restart it when changing model or load settings.

The default Docker runtime uses llama-cpp-python with a CPU backend. Backend GPU support is detected; a GPU-capable build can offload configured layers and retry on CPU if GPU loading fails. Installing CUDA drivers alone does not make a CPU-only image GPU accelerated. Missing model files or load failures leave copilot local-model state OFFLINE/ERROR while the existing API remains available. Docker bind configuration also rejects a nonexistent model source without creating a directory in its place.

COPILOT_WORKER_KEY protects internal worker calls. AI_SECRET_KEY is a Fernet key for stored external provider secrets. Both are generated into ignored .runtime/copilot.env by setup; keep this file private and back it up securely. LOCAL_LLM_SERVICE_URL and PROJECT_KNOWLEDGE_ROOT configure service discovery/document mount roots. EXTERNAL_AI_BASE_URL must be HTTPS and explicitly allowlisted. Do not expose the worker port publicly.

## Evidence and actions

Project knowledge only reads README.md and the explicitly named architecture, API, database, deployment, security, detection and copilot docs. Reindex is administrator-only. Retrieval is lexical, not vector embedding. SOC tools receive bounded typed arguments and run under the current caller's identity. At most three model rounds are allowed. A model may return a strict JSON ToolCall, for example {"tool":"alerts","query":"critical","limit":3}; unknown tools/extra arguments are rejected.

Ask AI on an alert supplies its identifier, then the backend retrieves authorized evidence. Model explanations must distinguish facts from assessments. Source-backed confidence, asset and MITRE information can be absent; the assistant must say so rather than invent it. Approved monitoring results can be summarized or compared by the model, but no new monitoring coverage is inferred.

Live intelligence currently retrieves CISA KEV from a fixed official endpoint, with bounded size, timeout and per-user rate limit. It provides vulnerability intelligence, not comprehensive cybersecurity news. Persisted feeds retain ingestion timestamps. No local model is described as having inherent live internet knowledge.

Notification actions are user-scoped; marking the underlying alert resolved requires analyst permissions and explicit confirmation. The model cannot invoke this mutation. There is no arbitrary autonomous action executor. Proactive messages are rule/event driven, not randomly generated prompts.

## Setup and private key entry

From the repository root run `python scripts/setup_copilot.py` once. Existing keys are preserved. Configure the optional external provider in Settings or through the server environment. Keys never appear in command arguments or the dashboard. The helper connects only to the local gateway on port 8080.

Stop generation before deleting conversations, deleting memory, or changing preferences. The backend returns 409 while generation is active to prevent deleted memory being recreated. Notification creation is serialized per user with a PostgreSQL transaction lock; duplicate polling cannot bypass cooldown decisions.

Production deployment requires TLS, protected infrastructure credentials, versioned schema migrations and a tested backup/restore policy. The bundled Compose file is a loopback-only local deployment.

GGUF exports without tokenizer.chat_template are detected. Qwen architectures use ChatML in this case; LOCAL_LLM_CHAT_FORMAT can explicitly override the runtime chat format for future models. Runtime format selection follows the [llama-cpp-python documentation](https://llama-cpp-python.readthedocs.io/en/latest/).

Setup also preserves or generates a strong JWT signing key in ignored `.runtime/api-security.env`, loaded only by the API. Replacing an old short signing key invalidates old sessions; users sign in again with their existing accounts. Account data is unchanged. Keep this file with encrypted backups and never mount it into the model worker.
