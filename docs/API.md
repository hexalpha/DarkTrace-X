# API reference

REST routes are rooted at `/api/v1`. Authentication uses locally issued JWT bearer tokens validated against active users, tenants and logout revocations. Roles are viewer, analyst, lead and admin; permissions are enforced by route dependencies. There is no implemented OIDC/JWKS integration or automatic demo identity.

Copilot model changes and knowledge reindex require admin. Read tools and conversations require an authenticated identity and are scoped to that tenant/user. Public CISA records are shared public intelligence. `/graphql` is an authenticated dashboard query; `/ws/events` authenticates using the first JSON message containing a token. Neither accepts an anonymous workspace.

## Registered route inventory

These routes are extracted from source decorators. Schema details are available from FastAPI OpenAPI on the internal API outside production. A listed route is not evidence of successful external integration; see READINESS_REPORT.md.

| Method | Path | Handler |
|---|---|---|
| POST | `/api/v1/telemetry` | `ingest` |
| GET | `/api/v1/detection/overview` | `detection` |
| GET | `/api/v1/marketplace` | `marketplace` |
| PUT | `/api/v1/marketplace/{plugin_id}` | `install` |
| DELETE | `/api/v1/marketplace/{plugin_id}` | `uninstall` |
| POST | `/api/v1/marketplace/{plugin_id}/run` | `run_plugin` |
| GET | `/api/v1/mcp/servers` | `mcp_servers` |
| GET | `/api/v1/mcp` | `mcp_stream` |
| POST | `/api/v1/mcp` | `mcp_rpc` |
| GET | `/api/v1/copilot/preferences` | `preferences` |
| PUT | `/api/v1/copilot/preferences` | `save_preferences` |
| DELETE | `/api/v1/copilot/memory` | `delete_memory` |
| GET | `/api/v1/copilot/sessions` | `sessions` |
| GET | `/api/v1/copilot/sessions/{ident}` | `conversation` |
| DELETE | `/api/v1/copilot/sessions/{ident}` | `delete_conversation` |
| GET | `/api/v1/copilot/models` | `models` |
| PUT | `/api/v1/copilot/models/{slot}` | `configure` |
| GET | `/api/v1/copilot/status` | `status` |
| POST | `/api/v1/copilot/knowledge/reindex` | `reindex` |
| POST | `/api/v1/copilot/tools` | `tool` |
| GET | `/api/v1/copilot/notifications` | `notices` |
| POST | `/api/v1/copilot/notifications/{ident}` | `notice_action` |
| POST | `/api/v1/copilot/chat` | `chat` |
| GET | `/api/v1/auth/me` | `me` |
| POST | `/api/v1/auth/logout` | `logout` |
| POST | `/api/v1/assets` | `create_asset` |
| PATCH | `/api/v1/operational-alerts/{alert_id}` | `update_alert` |
| DELETE | `/api/v1/monitors/keywords/{monitor_id}` | `delete_monitor` |
| POST | `/api/v1/exposure/ingest` | `ingest_exposure` |
| GET | `/api/v1/platform/status` | `platform_status` |
| POST | `/api/v1/intelligence/reindex` | `reindex` |
| GET | `/api/v1/health/live` | `liveness` |
| GET | `/api/v1/health/ready` | `readiness` |
| POST | `/api/v1/auth/register` | `register_user` |
| POST | `/api/v1/auth/login` | `login_user` |
| GET | `/api/v1/tenants/me` | `current_tenant` |
| GET | `/api/v1/tenants/users` | `tenant_users` |
| POST | `/api/v1/tenants/users` | `create_tenant_user` |
| PATCH | `/api/v1/tenants/users/{user_id}/role` | `set_tenant_user_role` |
| GET | `/api/v1/audit/events/operational` | `operational_audit_events` |
| GET | `/api/v1/monitors/keywords` | `list_keyword_monitors` |
| POST | `/api/v1/monitors/keywords` | `create_keyword_monitor` |
| GET | `/api/v1/threat-feeds/items` | `list_feed_items` |
| POST | `/api/v1/threat-feeds/cisa-kev/ingest` | `ingest_cisa_kev` |
| GET | `/api/v1/operational-alerts` | `list_operational_alerts` |
| GET | `/api/v1/cve/dashboard` | `cve_dashboard` |
| POST | `/api/v1/intelligence/iocs` | `index_ioc` |
| GET | `/api/v1/intelligence/iocs/correlate` | `correlate_ioc` |
| GET | `/api/v1/intelligence/graph` | `intelligence_graph` |
| POST | `/api/v1/threat-actors` | `create_actor_profile` |
| GET | `/api/v1/threat-actors/verified` | `list_verified_actor_profiles` |
| GET | `/api/v1/dashboard/overview` | `dashboard` |
| GET | `/api/v1/iocs` | `list_iocs` |
| POST | `/api/v1/iocs` | `create_ioc` |
| GET | `/api/v1/alerts` | `list_alerts` |
| GET | `/api/v1/cves` | `list_cves` |
| POST | `/api/v1/reputation/{indicator_type}` | `lookup_reputation` |
| GET | `/api/v1/assets` | `list_assets` |
| GET | `/api/v1/threat-actors` | `list_threat_actors` |
| POST | `/api/v1/hunts` | `run_hunt` |
| GET | `/api/v1/alert-rules` | `list_alert_rules` |
| POST | `/api/v1/alert-rules` | `create_alert_rule` |
| GET | `/api/v1/audit/events` | `list_audit_events` |
| GET | `/api/v1/ai/providers` | `list_ai_providers` |
| GET | `/api/v1/ai/models/scan` | `scan_local_ai_models` |
| POST | `/api/v1/ai/chat` | `chat_with_soc_assistant` |
| GET | `/api/v1/ai/conversations/{conversation_id}` | `get_soc_conversation` |
| GET | `/api/v1/automations` | `list_automations` |
| POST | `/api/v1/automations` | `create_automation` |
| POST | `/api/v1/automations/{automation_id}/run` | `run_automation` |
| POST | `/api/v1/integrations/webhooks` | `register_webhook` |
| GET | `/api/v1/integrations/webhooks` | `list_webhooks` |
| DELETE | `/api/v1/integrations/webhooks/{webhook_id}` | `delete_webhook` |
| GET | `/api/v1/exposure/mentions` | `exposure_mentions` |
| GET | `/api/v1/yara-rules` | `list_yara_rules` |
| GET | `/api/v1/plugins` | `list_plugins` |
| POST | `/api/v1/reports/{format_name}` | `export_report` |
| POST | `/api/v1/reports/schedules` | `schedule_report` |
| GET | `/api/v1/reports/schedules` | `list_report_schedules` |
| DELETE | `/api/v1/reports/schedules/{schedule_id}` | `delete_report_schedule` |

Webhook subscriptions now validate HTTPS/public destinations, encrypt a shared signing secret, filter real alert events by severity and sign redacted payloads with HMAC-SHA256. Report schedules validate bounded five-field cron and recipients, persist per tenant and return `pending_external_delivery` until an SMTP or approved delivery worker is configured. Automation triggers other than manual remain unavailable. The copilot streams SSE with session, provider, tool, delta, usage/notice, fallback, error and done events. Errors after headers arrive are SSE errors, not a changed HTTP status.
