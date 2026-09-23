"""Add source crawling, normalized document, entity and event tables."""

from alembic import op

revision = "0001_source_pipeline"
down_revision = "0000_legacy_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS intelligence_sources (
      tenant_id VARCHAR(80) NOT NULL, id VARCHAR(36) NOT NULL, name VARCHAR(160) NOT NULL,
      url VARCHAR(2048) NOT NULL, canonical_url VARCHAR(2048) NOT NULL, source_type VARCHAR(32) NOT NULL,
      category VARCHAR(64) NOT NULL, description TEXT NOT NULL DEFAULT '', enabled BOOLEAN NOT NULL DEFAULT FALSE,
      health VARCHAR(16) NOT NULL DEFAULT 'UNTESTED', crawl_policy VARCHAR(16) NOT NULL DEFAULT 'manual',
      frequency_minutes INTEGER NOT NULL DEFAULT 0, priority INTEGER NOT NULL DEFAULT 50, trust_level VARCHAR(16) NOT NULL DEFAULT 'medium',
      parser_type VARCHAR(16) NOT NULL DEFAULT 'html', robots_status VARCHAR(16) NOT NULL DEFAULT 'unknown',
      last_checked_at TIMESTAMP WITH TIME ZONE, last_crawled_at TIMESTAMP WITH TIME ZONE, last_success_at TIMESTAMP WITH TIME ZONE,
      last_failed_at TIMESTAMP WITH TIME ZONE, next_scheduled_at TIMESTAMP WITH TIME ZONE, failure_count INTEGER NOT NULL DEFAULT 0,
      last_error TEXT, tags JSON NOT NULL, created_at TIMESTAMP WITH TIME ZONE NOT NULL, updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
      PRIMARY KEY (tenant_id, id), CONSTRAINT uq_source_tenant_canonical_url UNIQUE (tenant_id, canonical_url)
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS source_crawl_jobs (
      tenant_id VARCHAR(80) NOT NULL, id VARCHAR(36) NOT NULL, source_id VARCHAR(36) NOT NULL, status VARCHAR(16) NOT NULL,
      started_at TIMESTAMP WITH TIME ZONE NOT NULL, finished_at TIMESTAMP WITH TIME ZONE, pages_requested INTEGER NOT NULL DEFAULT 1,
      pages_successful INTEGER NOT NULL DEFAULT 0, pages_failed INTEGER NOT NULL DEFAULT 0, bytes_downloaded INTEGER NOT NULL DEFAULT 0,
      records_extracted INTEGER NOT NULL DEFAULT 0, duplicates_found INTEGER NOT NULL DEFAULT 0, error TEXT,
      PRIMARY KEY (tenant_id, id)
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS source_documents (
      tenant_id VARCHAR(80) NOT NULL, id VARCHAR(36) NOT NULL, source_id VARCHAR(36) NOT NULL, crawl_id VARCHAR(36) NOT NULL,
      source_url VARCHAR(2048) NOT NULL, canonical_url VARCHAR(2048) NOT NULL, title VARCHAR(512) NOT NULL, raw_content TEXT NOT NULL,
      normalized_text TEXT NOT NULL, content_hash VARCHAR(64) NOT NULL, collected_at TIMESTAMP WITH TIME ZONE NOT NULL,
      published_at TIMESTAMP WITH TIME ZONE, first_seen TIMESTAMP WITH TIME ZONE NOT NULL, last_seen TIMESTAMP WITH TIME ZONE NOT NULL,
      source_category VARCHAR(64) NOT NULL, language VARCHAR(16) NOT NULL DEFAULT 'unknown', status VARCHAR(16) NOT NULL DEFAULT 'processed',
      metadata_json JSON NOT NULL, tags JSON NOT NULL, PRIMARY KEY (tenant_id, id), CONSTRAINT uq_source_document_tenant_hash UNIQUE (tenant_id, content_hash)
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS intelligence_entities (
      tenant_id VARCHAR(80) NOT NULL, id VARCHAR(64) NOT NULL, entity_type VARCHAR(32) NOT NULL, value VARCHAR(2048) NOT NULL,
      confidence INTEGER NOT NULL DEFAULT 95, extraction_method VARCHAR(32) NOT NULL DEFAULT 'deterministic',
      first_seen TIMESTAMP WITH TIME ZONE NOT NULL, last_seen TIMESTAMP WITH TIME ZONE NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'active',
      metadata_json JSON NOT NULL, PRIMARY KEY (tenant_id, id), CONSTRAINT uq_entity_tenant_type_value UNIQUE (tenant_id, entity_type, value)
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS entity_observations (
      tenant_id VARCHAR(80) NOT NULL, id VARCHAR(36) NOT NULL, entity_id VARCHAR(64) NOT NULL, document_id VARCHAR(36) NOT NULL,
      source_id VARCHAR(36) NOT NULL, confidence INTEGER NOT NULL DEFAULT 95, observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
      PRIMARY KEY (tenant_id, id), CONSTRAINT uq_entity_observation_document UNIQUE (tenant_id, entity_id, document_id)
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS threat_events (
      id VARCHAR(36) PRIMARY KEY, tenant_id VARCHAR(80) NOT NULL, event_type VARCHAR(64) NOT NULL, dedupe_key VARCHAR(240) NOT NULL,
      source_id VARCHAR(36) NOT NULL, document_id VARCHAR(36) NOT NULL, entity_id VARCHAR(64), severity VARCHAR(16) NOT NULL DEFAULT 'medium',
      confidence INTEGER NOT NULL DEFAULT 50, reason TEXT NOT NULL, evidence JSON NOT NULL, status VARCHAR(24) NOT NULL DEFAULT 'new',
      created_at TIMESTAMP WITH TIME ZONE NOT NULL, CONSTRAINT uq_threat_event_tenant_key UNIQUE (tenant_id, dedupe_key)
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_source_crawl_jobs_source_id ON source_crawl_jobs(source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_source_documents_source_id ON source_documents(source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_intelligence_entities_entity_type ON intelligence_entities(entity_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_entity_observations_entity_id ON entity_observations(entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_threat_events_tenant_id ON threat_events(tenant_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS threat_events")
    op.execute("DROP TABLE IF EXISTS entity_observations")
    op.execute("DROP TABLE IF EXISTS intelligence_entities")
    op.execute("DROP TABLE IF EXISTS source_documents")
    op.execute("DROP TABLE IF EXISTS source_crawl_jobs")
    op.execute("DROP TABLE IF EXISTS intelligence_sources")