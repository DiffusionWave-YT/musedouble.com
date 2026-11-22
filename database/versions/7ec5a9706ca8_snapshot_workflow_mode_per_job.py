from alembic import op
import sqlalchemy as sa

revision = '7ec5a9706ca8'
down_revision = '272ec2daf48a'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('jobs', sa.Column('workflow_mode', sa.String(length=16), nullable=True))
    op.execute('UPDATE jobs SET workflow_mode=workflows.mode FROM workflows WHERE jobs.workflow_id=workflows.id')
    op.alter_column('jobs', 'workflow_mode', nullable=False)

def downgrade():
    op.drop_column('jobs', 'workflow_mode')
