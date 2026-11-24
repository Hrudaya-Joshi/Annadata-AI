
"""Add pickup PIN to rescue missions

Revision ID: 29a03fd2a4af
Revises: e8a71b2d4c01
Create Date: 2026-11-24 12:31:56.515120
"""

from alembic import op
import sqlalchemy as sa


revision = '29a03fd2a4af'
down_revision = 'e8a71b2d4c01'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rescue_missions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('pickup_pin', sa.String(length=10), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('rescue_missions', schema=None) as batch_op:
        batch_op.drop_column('pickup_pin')
