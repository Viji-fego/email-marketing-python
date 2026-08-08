"""Add user_id to campaigns table

Revision ID: 20260808122335
Revises: 20260806123136
Create Date: 2026-08-08 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '20260808122335'
down_revision: Union[str, Sequence[str], None] = '20260806123136'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id column to campaigns table."""
    op.add_column('campaigns', sa.Column('user_id', mysql.VARCHAR(length=36), nullable=True))
    op.create_foreign_key('fk_campaigns_user_id', 'campaigns', 'users', ['user_id'], ['id'])
    op.create_index(op.f('ix_campaigns_user_id'), 'campaigns', ['user_id'])

    # Set user_id for existing rows - assign to first user if exists, otherwise to a default
    op.execute("""
        UPDATE campaigns SET user_id = (SELECT id FROM users LIMIT 1) WHERE user_id IS NULL
    """)

    # Now make the column non-nullable
    op.alter_column('campaigns', 'user_id', existing_type=mysql.VARCHAR(length=36), nullable=False)


def downgrade() -> None:
    """Remove user_id column from campaigns table."""
    op.drop_index(op.f('ix_campaigns_user_id'), table_name='campaigns')
    op.drop_constraint('fk_campaigns_user_id', 'campaigns', type_='foreignkey')
    op.drop_column('campaigns', 'user_id')
