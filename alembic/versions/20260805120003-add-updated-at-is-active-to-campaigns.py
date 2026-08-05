"""Add updated_at and is_active to campaigns table

Revision ID: 20260805120003
Revises: 20260805120002
Create Date: 2026-08-05 12:00:03.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '20260805120003'
down_revision: Union[str, Sequence[str], None] = '20260805120002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add updated_at and is_active to campaigns table."""
    op.add_column('campaigns', sa.Column('updated_at', mysql.DATETIME(), nullable=True))
    op.add_column('campaigns', sa.Column('is_active', mysql.ENUM('0', '1'), server_default='1', nullable=False))


def downgrade() -> None:
    """Remove updated_at and is_active from campaigns table."""
    op.drop_column('campaigns', 'is_active')
    op.drop_column('campaigns', 'updated_at')
