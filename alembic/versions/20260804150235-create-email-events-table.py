"""Create email_events table

Revision ID: 20260804150235
Revises: 20260804150234
Create Date: 2026-08-04 15:02:35.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '20260804150235'
down_revision: Union[str, Sequence[str], None] = '20260804150234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create email_events table."""
    op.create_table('email_events',
    sa.Column('id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('campaign_contact_id', mysql.VARCHAR(length=36), nullable=False),
    sa.Column('event_type', mysql.VARCHAR(length=50), nullable=False),
    sa.Column('detail', mysql.TEXT(), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='MyISAM'
    )
    # Add foreign key constraint
    op.create_foreign_key('fk_email_events_campaign_contact_id', 'email_events', 'campaign_contacts', ['campaign_contact_id'], ['id'])


def downgrade() -> None:
    """Drop email_events table."""
    op.drop_constraint('fk_email_events_campaign_contact_id', 'email_events', type_='foreignkey')
    op.drop_table('email_events')
