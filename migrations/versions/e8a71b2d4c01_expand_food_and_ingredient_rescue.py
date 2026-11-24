"""expand_food_and_ingredient_rescue

Revision ID: e8a71b2d4c01
Revises: 0026fcf6a44b
Create Date: 2026-11-24 08:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e8a71b2d4c01'
down_revision = '0026fcf6a44b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ngos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('accepted_categories', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('storage_facilities', sa.String(length=200), nullable=True))

    with op.batch_alter_table('food_donations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('donation_category', sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column('produce_type', sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column('freshness_condition', sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column('harvest_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('ingredient_name', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('packaging_condition', sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column('storage_requirements', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('image_url', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('requires_human_verification', sa.Boolean(), nullable=True))
        batch_op.alter_column('preparation_time', existing_type=sa.DateTime(), nullable=True)

    with op.batch_alter_table('food_safety_assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('requires_human_verification', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('category_checks', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('safety_recommendations', sa.Text(), nullable=True))

    with op.batch_alter_table('beneficiary_demands', schema=None) as batch_op:
        batch_op.add_column(sa.Column('donation_category', sa.String(length=40), nullable=True))

    with op.batch_alter_table('impact_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('donation_category', sa.String(length=40), nullable=True))


def downgrade():
    with op.batch_alter_table('impact_records', schema=None) as batch_op:
        batch_op.drop_column('donation_category')

    with op.batch_alter_table('beneficiary_demands', schema=None) as batch_op:
        batch_op.drop_column('donation_category')

    with op.batch_alter_table('food_safety_assessments', schema=None) as batch_op:
        batch_op.drop_column('safety_recommendations')
        batch_op.drop_column('category_checks')
        batch_op.drop_column('requires_human_verification')

    with op.batch_alter_table('food_donations', schema=None) as batch_op:
        batch_op.alter_column('preparation_time', existing_type=sa.DateTime(), nullable=False)
        batch_op.drop_column('requires_human_verification')
        batch_op.drop_column('image_url')
        batch_op.drop_column('storage_requirements')
        batch_op.drop_column('packaging_condition')
        batch_op.drop_column('ingredient_name')
        batch_op.drop_column('harvest_date')
        batch_op.drop_column('freshness_condition')
        batch_op.drop_column('produce_type')
        batch_op.drop_column('donation_category')

    with op.batch_alter_table('ngos', schema=None) as batch_op:
        batch_op.drop_column('storage_facilities')
        batch_op.drop_column('accepted_categories')
