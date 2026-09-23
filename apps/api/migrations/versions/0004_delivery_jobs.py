"""Durable delivery queue and report artifacts."""
from alembic import op
revision='0004_delivery_jobs'
down_revision='0003_crawl_reliability'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('''CREATE TABLE delivery_jobs (
        id VARCHAR(36) PRIMARY KEY, tenant_id VARCHAR(80) NOT NULL REFERENCES tenants(id),
        kind VARCHAR(16) NOT NULL, target_id VARCHAR(36) NOT NULL, dedupe_key VARCHAR(180) NOT NULL,
        payload JSON NOT NULL, status VARCHAR(24) NOT NULL, attempts INTEGER NOT NULL,
        next_attempt_at TIMESTAMPTZ NOT NULL, last_error VARCHAR(120), result JSON NOT NULL,
        created_at TIMESTAMPTZ NOT NULL, CONSTRAINT uq_delivery_tenant_dedupe UNIQUE(tenant_id,dedupe_key))''')
    op.create_index('ix_delivery_jobs_tenant_id','delivery_jobs',['tenant_id'])
    op.create_index('ix_delivery_jobs_due','delivery_jobs',['status','next_attempt_at'])


def downgrade():
    op.drop_table('delivery_jobs')
