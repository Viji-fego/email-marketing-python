"""Add contact_list_id to campaigns table

Revision ID: 20260805120008
Revises: 20260805120007
Create Date: 2026-08-05 12:00:08.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '20260805120008'
down_revision: Union[str, Sequence[str], None] = '20260805120007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add contact_list_id to campaigns table."""
    op.add_column('campaigns', sa.Column('contact_list_id', mysql.VARCHAR(length=36), nullable=True))
    op.create_foreign_key('fk_campaigns_contact_list_id', 'campaigns', 'contact_lists', ['contact_list_id'], ['id'])
    op.create_index(op.f('ix_campaigns_contact_list_id'), 'campaigns', ['contact_list_id'])


def downgrade() -> None:
    """Remove contact_list_id from campaigns table."""
    op.drop_index(op.f('ix_campaigns_contact_list_id'), table_name='campaigns')
    op.drop_constraint('fk_campaigns_contact_list_id', 'campaigns', type_='foreignkey')
    op.drop_column('campaigns', 'contact_list_id')
