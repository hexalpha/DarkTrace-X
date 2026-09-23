"""Rotating browser sessions with tenant/user references."""
from alembic import op
revision = '0002_browser_sessions'
down_revision = '0001_source_pipeline'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE browser_sessions (
        digest VARCHAR(64) PRIMARY KEY, family VARCHAR(36) NOT NULL,
        tenant_id VARCHAR(80) NOT NULL REFERENCES tenants(id),
        user_id VARCHAR(36) NOT NULL REFERENCES users(id), csrf VARCHAR(64) NOT NULL,
        revoked BOOLEAN NOT NULL DEFAULT FALSE, expires_at TIMESTAMPTZ NOT NULL)''')
    for column in ('family', 'tenant_id', 'user_id'):
        op.create_index('ix_browser_sessions_'+column, 'browser_sessions', [column])


def downgrade():
    op.drop_table('browser_sessions')
