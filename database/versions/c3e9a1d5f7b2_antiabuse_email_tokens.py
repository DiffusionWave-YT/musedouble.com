"""email verification and recovery tokens"""
from alembic import op
import sqlalchemy as sa

revision = 'c3e9a1d5f7b2'
down_revision = '5b8d1f3a7c20'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.create_table('email_tokens',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('purpose', sa.String(12), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_email_tokens_user_id', 'email_tokens', ['user_id'])
    op.create_index('ix_email_tokens_expires_at', 'email_tokens', ['expires_at'])

def downgrade():
    op.drop_table('email_tokens')
    op.drop_column('users', 'email_verified')
