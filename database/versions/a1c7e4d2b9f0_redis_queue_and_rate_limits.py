"""redis_queue_and_rate_limits: jobs.enqueued_at; rate limits move to Redis."""
from alembic import op
import sqlalchemy as sa

revision = 'a1c7e4d2b9f0'
down_revision = '76906dba89e1'
branch_labels = None
depends_on = None


def upgrade():
    # NULL means "never handed to Redis": the sweeper picks such queued jobs up.
    op.add_column('jobs', sa.Column('enqueued_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_table('rate_events')


def downgrade():
    op.create_table(
        'rate_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('scope', sa.String(length=80), nullable=False),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_rate_events_scope', 'rate_events', ['scope'])
    op.create_index('ix_rate_events_key', 'rate_events', ['key'])
    op.create_index('ix_rate_events_created_at', 'rate_events', ['created_at'])
    op.drop_column('jobs', 'enqueued_at')
