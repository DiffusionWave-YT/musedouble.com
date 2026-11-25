"""redeem codes"""
from alembic import op
import sqlalchemy as sa

revision = '143fab749f42'
down_revision = 'a1c7e4d2b9f0'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('redeem_codes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('credits', sa.Integer(), nullable=False),
    sa.Column('max_uses', sa.Integer(), nullable=False),
    sa.Column('uses', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('note', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('credits > 0'),
    sa.CheckConstraint('max_uses > 0'),
    sa.CheckConstraint('uses >= 0'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('redemptions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['code_id'], ['redeem_codes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code_id', 'user_id')
    )
    op.create_index(op.f('ix_redemptions_code_id'), 'redemptions', ['code_id'], unique=False)
    op.create_index(op.f('ix_redemptions_user_id'), 'redemptions', ['user_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_redemptions_user_id'), table_name='redemptions')
    op.drop_index(op.f('ix_redemptions_code_id'), table_name='redemptions')
    op.drop_table('redemptions')
    op.drop_table('redeem_codes')
