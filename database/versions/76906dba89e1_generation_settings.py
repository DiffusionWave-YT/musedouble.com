from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '76906dba89e1'
down_revision = '7ec5a9706ca8'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('app_settings',
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.PrimaryKeyConstraint('name')
    )

def downgrade():
    op.drop_table('app_settings')
