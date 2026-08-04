"""Create campaign_contacts table

Revision ID: 20260804150234
Revises: 20260804150233
Create Date: 2026-08-04 15:02:34.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '20260804150234'
down_revision: Union[str, Sequence[str], None] = '20260804150233'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create campaign_contacts table."""
    op.create_table('campaign_contacts',
    sa.Column('id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('campaign_id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('contact_id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('status', mysql.VARCHAR(length=50), nullable=True),
    sa.Column('sent_at', mysql.DATETIME(), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='MyISAM'
    )
    # Add foreign key constraints
    op.create_foreign_key('fk_campaign_contacts_campaign_id', 'campaign_contacts', 'campaigns', ['campaign_id'], ['id'])
    op.create_foreign_key('fk_campaign_contacts_contact_id', 'campaign_contacts', 'contacts', ['contact_id'], ['id'])


def downgrade() -> None:
    """Drop campaign_contacts table."""
    op.drop_constraint('fk_campaign_contacts_contact_id', 'campaign_contacts', type_='foreignkey')
    op.drop_constraint('fk_campaign_contacts_campaign_id', 'campaign_contacts', type_='foreignkey')
    op.drop_table('campaign_contacts')
