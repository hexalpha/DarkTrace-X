"""Crawl retry diagnostics and tenant-aware lookup indexes."""
from alembic import op
import sqlalchemy as sa
revision = '0003_crawl_reliability'
down_revision = '0002_browser_sessions'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('source_crawl_jobs', sa.Column('retry_count',sa.Integer(),nullable=False,server_default='0'))
    op.add_column('source_crawl_jobs', sa.Column('duration_ms',sa.Integer(),nullable=True))
    op.add_column('source_crawl_jobs', sa.Column('error_type',sa.String(80),nullable=True))
    op.create_index('ix_crawls_tenant_source_status','source_crawl_jobs',['tenant_id','source_id','status'])
    op.create_index('ix_documents_tenant_collected','source_documents',['tenant_id','collected_at'])
    op.create_index('ix_events_tenant_created','threat_events',['tenant_id','created_at'])


def downgrade():
    op.drop_index('ix_events_tenant_created',table_name='threat_events')
    op.drop_index('ix_documents_tenant_collected',table_name='source_documents')
    op.drop_index('ix_crawls_tenant_source_status',table_name='source_crawl_jobs')
    for name in ('error_type','duration_ms','retry_count'):
        op.drop_column('source_crawl_jobs',name)
