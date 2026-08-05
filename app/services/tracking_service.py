"""Email tracking service for processing webhook events.

Responsibilities:
- Find campaign_contact by message ID
- Create EmailEvent records
- Update CampaignContact snapshot
- Prevent duplicate processing
- Handle errors gracefully
"""

import logging
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models import CampaignContact, EmailEvent
from app.enums import EmailEventType, DeliveryStatus
from app.services.event_processor import InternalEvent

logger = logging.getLogger(__name__)


class TrackingService:
    """Handle email tracking and event processing."""

    @staticmethod
    def find_campaign_contact(
        db: Session,
        provider_message_id: str,
        campaign_contact_id: Optional[str] = None,
    ) -> Optional[CampaignContact]:
        """
        Find CampaignContact by primary key (campaign_contact_id) or fallback to message ID.

        Lookup strategy:
        1. If campaign_contact_id is provided (from webhook tag), use it directly (most reliable)
        2. If not provided, fall back to message_id lookup (for backward compatibility)

        Args:
            db: Database session
            provider_message_id: Message ID from email provider (fallback)
            campaign_contact_id: Internal campaign_contact UUID (primary, if available)

        Returns:
            CampaignContact or None if not found
        """
        try:
            # Primary lookup: by campaign_contact_id (from webhook tag)
            if campaign_contact_id:
                logger.info("🔍 Finding campaign_contact by ID (from tag): %s", campaign_contact_id)
                contact = db.query(CampaignContact).filter_by(id=campaign_contact_id).first()
                if contact:
                    logger.info("✅ Found campaign_contact by ID: ID=%s, Status=%s", contact.id, contact.status)
                    return contact
                else:
                    logger.warning("❌ Campaign contact NOT found by ID: %s", campaign_contact_id)
                    # Don't fall back to message_id if ID was provided but not found
                    # (indicates a data mismatch or webhook tampering)
                    return None

            # Fallback: by message_id (for emails sent before tag support was added)
            logger.info("🔍 Finding campaign_contact by message_id (fallback): %s", provider_message_id)
            contact = db.query(CampaignContact).filter_by(
                provider_message_id=provider_message_id
            ).first()
            if contact:
                logger.info("✅ Found campaign_contact by message_id: ID=%s, Status=%s", contact.id, contact.status)
            else:
                logger.warning("❌ Campaign contact NOT found for message_id: %s", provider_message_id)
            return contact

        except SQLAlchemyError as e:
            logger.error("❌ Database error finding campaign_contact: %s", e)
            return None

    @staticmethod
    def check_duplicate_event(
        db: Session, provider_message_id: str, event_type: EmailEventType
    ) -> bool:
        """
        Check if event already exists (duplicate protection).

        Args:
            db: Database session
            provider_message_id: Message ID from email provider
            event_type: Type of event

        Returns:
            True if event already exists, False otherwise
        """
        try:
            existing = db.query(EmailEvent).filter_by(
                provider_message_id=provider_message_id,
                event_type=event_type.value,
            ).first()
            return existing is not None
        except SQLAlchemyError as e:
            logger.error("Database error checking duplicate: %s", e)
            return False

    @staticmethod
    def create_email_event(
        db: Session,
        campaign_contact_id: str,
        internal_event: InternalEvent,
    ) -> Optional[EmailEvent]:
        """
        Create EmailEvent record (audit trail).

        Args:
            db: Database session
            campaign_contact_id: Campaign contact ID
            internal_event: Normalized internal event

        Returns:
            Created EmailEvent or None if failed
        """
        try:
            email_event = EmailEvent(
                campaign_contact_id=campaign_contact_id,
                provider_message_id=internal_event.provider_message_id,
                event_type=internal_event.event_type.value,
                provider=internal_event.provider,
                payload=internal_event.payload,
                created_at=internal_event.timestamp,
            )
            db.add(email_event)
            db.flush()
            return email_event
        except SQLAlchemyError as e:
            logger.error("Database error creating email_event: %s", e)
            return None

    @staticmethod
    def update_campaign_contact_snapshot(
        db: Session,
        campaign_contact: CampaignContact,
        internal_event: InternalEvent,
    ) -> bool:
        """
        Update CampaignContact snapshot fields based on event.

        Snapshot fields represent the latest known state of the email.

        Args:
            db: Database session
            campaign_contact: Campaign contact to update
            internal_event: Event that occurred

        Returns:
            True if successful, False otherwise
        """
        try:
            event_type = internal_event.event_type
            old_status = campaign_contact.status

            logger.info("📝 Updating snapshot for contact %s, event: %s", campaign_contact.id, event_type.value)
            logger.info("   Previous status: %s", old_status)

            # Update timestamp field based on event type
            if event_type == EmailEventType.DELIVERED:
                campaign_contact.delivered_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.DELIVERED.value
                logger.info("   ✓ Set delivered_at = %s", internal_event.timestamp)
            elif event_type == EmailEventType.OPENED:
                campaign_contact.opened_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.OPENED.value
                logger.info("   ✓ Set opened_at = %s", internal_event.timestamp)
            elif event_type == EmailEventType.CLICKED:
                campaign_contact.clicked_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.CLICKED.value
                logger.info("   ✓ Set clicked_at = %s", internal_event.timestamp)
            elif event_type == EmailEventType.HARD_BOUNCE:
                campaign_contact.bounced_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.BOUNCED.value
                logger.info("   ✓ Set bounced_at = %s", internal_event.timestamp)
            elif event_type == EmailEventType.SOFT_BOUNCE:
                campaign_contact.bounced_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.DEFERRED.value
                logger.info("   ✓ Set bounced_at = %s (soft bounce)", internal_event.timestamp)
            elif event_type == EmailEventType.BLOCKED:
                campaign_contact.bounced_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.BLOCKED.value
                logger.info("   ✓ Set bounced_at = %s (blocked)", internal_event.timestamp)
            elif event_type == EmailEventType.SPAM:
                campaign_contact.bounced_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.SPAM.value
                logger.info("   ✓ Set bounced_at = %s (spam)", internal_event.timestamp)
            elif event_type == EmailEventType.UNSUBSCRIBED:
                campaign_contact.unsubscribed_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.UNSUBSCRIBED.value
                logger.info("   ✓ Set unsubscribed_at = %s", internal_event.timestamp)
            elif event_type == EmailEventType.DEFERRED:
                campaign_contact.status = DeliveryStatus.DEFERRED.value
                logger.info("   ✓ Status set to deferred")

            # Update last event tracking
            campaign_contact.last_event = event_type.value
            campaign_contact.last_event_at = internal_event.timestamp
            campaign_contact.updated_at = datetime.now(timezone.utc)

            logger.info("   New status: %s → %s", old_status, campaign_contact.status)
            logger.info("   ✓ last_event = %s", event_type.value)

            # DEBUG: Log state before merge
            from sqlalchemy.inspection import inspect as sqlalchemy_inspect
            insp_before = sqlalchemy_inspect(campaign_contact)
            logger.info("🔧 DEBUG: Before db.merge()")
            logger.info(f"   Object ID (Python): {id(campaign_contact)}")
            logger.info(f"   Persistent: {bool(insp_before.persistent)}")
            logger.info(f"   Modified: {insp_before.modified}")
            logger.info(f"   Status value: {campaign_contact.status}")

            db.merge(campaign_contact)

            # DEBUG: Log state after merge
            insp_after = sqlalchemy_inspect(campaign_contact)
            logger.info("🔧 DEBUG: After db.merge() - return value NOT captured")
            logger.info(f"   Object ID (Python): {id(campaign_contact)}")
            logger.info(f"   Persistent: {bool(insp_after.persistent)}")
            logger.info(f"   Modified: {insp_after.modified}")
            logger.info(f"   Status value: {campaign_contact.status}")

            return True

        except Exception as e:
            logger.error("❌ Error updating campaign_contact snapshot: %s", e)
            return False

    @staticmethod
    def process_event(
        db: Session,
        campaign_contact: CampaignContact,
        internal_event: InternalEvent,
    ) -> bool:
        """
        Process a single email event (atomic transaction).

        Args:
            db: Database session
            campaign_contact: Campaign contact for this email
            internal_event: Normalized event from provider

        Returns:
            True if processed successfully, False otherwise
        """
        try:
            logger.info("=" * 80)
            logger.info("PROCESSING EMAIL EVENT")
            logger.info("=" * 80)

            # Check for duplicate (idempotency)
            logger.info("1️⃣ Checking for duplicate event...")
            if TrackingService.check_duplicate_event(
                db, internal_event.provider_message_id, internal_event.event_type
            ):
                logger.warning(
                    "⚠️ Duplicate event ignored: %s %s",
                    internal_event.provider_message_id,
                    internal_event.event_type.value,
                )
                return True

            logger.info("✅ Not a duplicate - proceeding...")

            # Create audit log entry
            logger.info("2️⃣ Creating audit trail entry in email_events table...")
            email_event = TrackingService.create_email_event(
                db, campaign_contact.id, internal_event
            )
            if not email_event:
                logger.error("❌ Failed to create email_event for %s", campaign_contact.id)
                db.rollback()
                return False
            logger.info("✅ Audit trail entry created: ID=%s", email_event.id)

            # Update snapshot
            logger.info("3️⃣ Updating campaign_contacts snapshot fields...")
            if not TrackingService.update_campaign_contact_snapshot(
                db, campaign_contact, internal_event
            ):
                logger.error("❌ Failed to update snapshot for %s", campaign_contact.id)
                db.rollback()
                return False

            # Commit transaction
            logger.info("4️⃣ Committing transaction to database...")
            db.commit()
            logger.info("✅ Transaction committed successfully")

            logger.info("=" * 80)
            logger.info("✅ EVENT PROCESSED SUCCESSFULLY")
            logger.info("Contact ID: %s", campaign_contact.id)
            logger.info("Event Type: %s", internal_event.event_type.value)
            logger.info("Timestamp: %s", internal_event.timestamp.isoformat())
            logger.info("Message ID: %s", internal_event.provider_message_id)
            logger.info("=" * 80)

            return True

        except SQLAlchemyError as e:
            logger.error("❌ Database transaction failed: %s", e)
            db.rollback()
            return False
        except Exception as e:
            logger.error("❌ Unexpected error processing event: %s", e)
            db.rollback()
            return False
