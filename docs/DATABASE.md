# Database schema

PostgreSQL is authoritative. Elasticsearch is a derived index. Redis stores copilot rate limits and active-generation leases with expiry; it is not an implemented job queue. Tenant isolation is enforced in application queries, not PostgreSQL RLS. Current startup uses SQLAlchemy create_all for additive table creation; versioned upgrade/downgrade migrations are not implemented.

The following table/column inventory is extracted from the actual SQLAlchemy models. No live row values or credentials are included.

## copilot_records

| Column | Python mapped type |
|---|---|
| `tenant_id` | `Mapped[str]` |
| `user_id` | `Mapped[str]` |
| `kind` | `Mapped[str]` |
| `id` | `Mapped[str]` |
| `payload` | `Mapped[dict]` |
| `updated_at` | `Mapped[datetime]` |

## tenant_intelligence

| Column | Python mapped type |
|---|---|
| `tenant_id` | `Mapped[str]` |
| `collection` | `Mapped[str]` |
| `id` | `Mapped[str]` |
| `payload` | `Mapped[dict]` |
| `updated_at` | `Mapped[datetime]` |

## revoked_tokens

| Column | Python mapped type |
|---|---|
| `digest` | `Mapped[str]` |
| `expires_at` | `Mapped[datetime]` |

## behavior_telemetry

| Column | Python mapped type |
|---|---|
| `tenant_id` | `Mapped[str]` |
| `id` | `Mapped[str]` |
| `entity` | `Mapped[str]` |
| `metric` | `Mapped[str]` |
| `observed_at` | `Mapped[datetime]` |
| `payload` | `Mapped[dict]` |

## tenant_extensions

| Column | Python mapped type |
|---|---|
| `tenant_id` | `Mapped[str]` |
| `id` | `Mapped[str]` |
| `enabled` | `Mapped[bool]` |
| `installed_at` | `Mapped[datetime]` |

## tenants

| Column | Python mapped type |
|---|---|
| `id` | `Mapped[str]` |
| `name` | `Mapped[str]` |
| `active` | `Mapped[bool]` |
| `created_at` | `Mapped[datetime]` |

## users

| Column | Python mapped type |
|---|---|
| `id` | `Mapped[str]` |
| `tenant_id` | `Mapped[str]` |
| `email` | `Mapped[str]` |
| `display_name` | `Mapped[str]` |
| `password_hash` | `Mapped[str]` |
| `role` | `Mapped[str]` |
| `active` | `Mapped[bool]` |
| `created_at` | `Mapped[datetime]` |

## keyword_monitors

| Column | Python mapped type |
|---|---|
| `id` | `Mapped[str]` |
| `tenant_id` | `Mapped[str]` |
| `term` | `Mapped[str]` |
| `categories` | `Mapped[list[str]]` |
| `enabled` | `Mapped[bool]` |
| `created_by` | `Mapped[str]` |
| `created_at` | `Mapped[datetime]` |

## threat_feed_items

| Column | Python mapped type |
|---|---|
| `id` | `Mapped[str]` |
| `source` | `Mapped[str]` |
| `external_id` | `Mapped[str]` |
| `title` | `Mapped[str]` |
| `summary` | `Mapped[str]` |
| `severity` | `Mapped[str]` |
| `published_at` | `Mapped[datetime]` |
| `raw` | `Mapped[dict]` |
| `ingested_at` | `Mapped[datetime]` |

## operational_alerts

| Column | Python mapped type |
|---|---|
| `id` | `Mapped[str]` |
| `tenant_id` | `Mapped[str]` |
| `dedupe_key` | `Mapped[str]` |
| `title` | `Mapped[str]` |
| `severity` | `Mapped[str]` |
| `score` | `Mapped[int]` |
| `status` | `Mapped[str]` |
| `evidence` | `Mapped[dict]` |
| `created_at` | `Mapped[datetime]` |

## audit_events

| Column | Python mapped type |
|---|---|
| `id` | `Mapped[str]` |
| `tenant_id` | `Mapped[str]` |
| `actor_id` | `Mapped[str]` |
| `action` | `Mapped[str]` |
| `resource_type` | `Mapped[str]` |
| `resource_id` | `Mapped[str]` |
| `outcome` | `Mapped[str]` |
| `metadata_json` | `Mapped[dict]` |
| `occurred_at` | `Mapped[datetime]` |

## conversation_messages

| Column | Python mapped type |
|---|---|
| `id` | `Mapped[str]` |
| `tenant_id` | `Mapped[str]` |
| `user_id` | `Mapped[str]` |
| `conversation_id` | `Mapped[str]` |
| `role` | `Mapped[str]` |
| `content` | `Mapped[str]` |
| `provider` | `Mapped[str]` |
| `model` | `Mapped[str]` |
| `created_at` | `Mapped[datetime]` |

Copilot records use a composite tenant_id/user_id/kind/id key. Provider settings use the reserved owner tenant and encrypted Fernet key ciphertext. Conversations, preferences, incident context, notifications, tool history and usage are user-scoped kinds. Public threat_feed_items have no tenant ownership because they contain shared CISA advisories. Passwords are hashed. Master encryption keys are outside the database.

Named Docker volumes preserve PostgreSQL, Elasticsearch and Redis across container recreation. Backup/restore and disaster recovery have not been verified.
