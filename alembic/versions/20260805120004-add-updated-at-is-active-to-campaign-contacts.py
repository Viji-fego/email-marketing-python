"""Add updated_at and is_active to campaign_contacts table

Revision ID: 20260805120004
Revises: 20260805120003
Create Date: 2026-08-05 12:00:04.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '20260805120004'
down_revision: Union[str, Sequence[str], None] = '20260805120003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active to campaign_contacts table."""
    op.add_column('campaign_contacts', sa.Column('is_active', mysql.ENUM('0', '1'), server_default='1', nullable=False))


def downgrade() -> None:
    """Remove is_active from campaign_contacts table."""
    op.drop_column('campaign_contacts', 'is_active')
