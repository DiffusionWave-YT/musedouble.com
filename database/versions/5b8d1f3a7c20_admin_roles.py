"""admin owner and permissions"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '5b8d1f3a7c20'
down_revision = '143fab749f42'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('owner', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))

def downgrade():
    op.drop_column('users', 'permissions')
    op.drop_column('users', 'owner')
