"""Add webhook tracking columns and indexes.

Revision ID: 20260804150236
Revises: 20260804150235
Create Date: 2026-08-04 15:02:36.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260804150236"
down_revision = "20260804150235"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add webhook tracking columns to campaign_contacts and extend email_events."""
    # Modify email_events table
    op.add_column(
        "email_events",
        sa.Column("provider_message_id", sa.String(100), nullable=True, index=True),
    )
    op.add_column(
        "email_events",
        sa.Column("provider", sa.String(50), nullable=False, server_default="brevo"),
    )
    op.add_column(
        "email_events",
        sa.Column("payload", sa.JSON(), nullable=True),
    )

    # Add indexes to email_events
    op.create_index(
        "idx_event_type",
        "email_events",
        ["event_type"],
    )
    op.create_index(
        "idx_event_type_created",
        "email_events",
        ["event_type", "created_at"],
    )
    op.create_index(
        "idx_campaign_contact_event",
        "email_events",
        ["campaign_contact_id", "event_type"],
    )

    # Modify campaign_contacts table
    op.add_column(
        "campaign_contacts",
        sa.Column("provider_message_id", sa.String(100), nullable=True, index=True),
    )
    op.add_column(
        "campaign_contacts",
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "campaign_contacts",
        sa.Column("opened_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "campaign_contacts",
        sa.Column("clicked_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "campaign_contacts",
        sa.Column("bounced_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "campaign_contacts",
        sa.Column("unsubscribed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "campaign_contacts",
        sa.Column("last_event", sa.String(50), nullable=True),
    )
    op.add_column(
        "campaign_contacts",
        sa.Column("last_event_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "campaign_contacts",
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )

    # Add indexes to campaign_contacts
    op.create_index(
        "idx_campaign_status",
        "campaign_contacts",
        ["campaign_id", "status"],
    )
    op.create_index(
        "idx_campaign_contact_status",
        "campaign_contacts",
        ["status"],
    )
    op.create_index(
        "idx_campaign_contact_created",
        "campaign_contacts",
        ["created_at"],
    )

    # Add unique constraint using raw SQL (to avoid index size issues)
    op.execute("ALTER TABLE campaign_contacts ADD UNIQUE KEY uk_provider_message_id (provider_message_id(60))")


def downgrade() -> None:
    """Remove webhook tracking columns and indexes."""
    # Remove unique constraint
    op.execute("ALTER TABLE campaign_contacts DROP KEY uk_provider_message_id")

    # Remove indexes from campaign_contacts
    op.drop_index("idx_campaign_contact_created", table_name="campaign_contacts")
    op.drop_index("idx_campaign_contact_status", table_name="campaign_contacts")
    op.drop_index("idx_campaign_status", table_name="campaign_contacts")

    # Remove columns from campaign_contacts
    op.drop_column("campaign_contacts", "updated_at")
    op.drop_column("campaign_contacts", "last_event_at")
    op.drop_column("campaign_contacts", "last_event")
    op.drop_column("campaign_contacts", "unsubscribed_at")
    op.drop_column("campaign_contacts", "bounced_at")
    op.drop_column("campaign_contacts", "clicked_at")
    op.drop_column("campaign_contacts", "opened_at")
    op.drop_column("campaign_contacts", "delivered_at")
    op.drop_column("campaign_contacts", "provider_message_id")

    # Remove indexes from email_events
    op.drop_index("idx_campaign_contact_event", table_name="email_events")
    op.drop_index("idx_event_type_created", table_name="email_events")
    op.drop_index("idx_event_type", table_name="email_events")

    # Remove columns from email_events
    op.drop_column("email_events", "payload")
    op.drop_column("email_events", "provider")
    op.drop_column("email_events", "provider_message_id")
