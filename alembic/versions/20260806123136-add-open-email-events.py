"""Add open_confidence column to email_events table.

Revision ID: 20260806123136
Revises: 20260806123136
Create Date: 2026-08-06 12:32:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260806123136'
down_revision = '20260805120008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add open_confidence column to email_events table."""
    op.add_column(
        'email_events',
        sa.Column(
            'open_confidence',
            sa.String(50),
            nullable=True,
            comment='genuine | likely_prefetch | likely_bot_scan | null (non-opens)'
        )
    )
    op.create_index(
        'ix_email_events_open_confidence',
        'email_events',
        ['open_confidence']
    )


def downgrade() -> None:
    """Remove open_confidence column from email_events table."""
    op.drop_index('ix_email_events_open_confidence', table_name='email_events')
    op.drop_column('email_events', 'open_confidence')
