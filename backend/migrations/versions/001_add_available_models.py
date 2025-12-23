"""Add available_models column to ai_settings

Revision ID: 001_add_available_models
Revises: 
Create Date: 2024-12-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_available_models'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add available_models column to ai_settings table
    op.add_column(
        'ai_settings',
        sa.Column('available_models', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('ai_settings', 'available_models')

