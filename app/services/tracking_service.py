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
            logger.info("STEP 2: Searching campaign contact...")
            if campaign_contact_id:
                logger.info("  Lookup by id: %s", campaign_contact_id)
                contact = db.query(CampaignContact).filter_by(id=campaign_contact_id).first()
                if not contact:
                    logger.warning("✗ Contact not found by id=%s", campaign_contact_id)
                    return None
                logger.info("  ✓ Found by id: %s", contact.id)
                return contact

            logger.info("  Lookup by msgid: %s", provider_message_id)
            contact = db.query(CampaignContact).filter_by(
                provider_message_id=provider_message_id
            ).first()
            if not contact:
                logger.warning("✗ Contact not found by msgid=%s", provider_message_id)
                return None
            logger.info("  ✓ Found by msgid: %s", contact.id)
            return contact

        except SQLAlchemyError as e:
            logger.error("✗ Database error: %s", e)
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
        open_confidence: Optional[str] = None,
    ) -> Optional[EmailEvent]:
        """Create EmailEvent record (audit trail)."""
        try:
            email_event = EmailEvent(
                campaign_contact_id=campaign_contact_id,
                provider_message_id=internal_event.provider_message_id,
                event_type=internal_event.event_type.value,
                provider=internal_event.provider,
                payload=internal_event.payload,
                created_at=internal_event.timestamp,
                open_confidence=open_confidence,
            )
            db.add(email_event)
            db.flush()
            return email_event
        except SQLAlchemyError as e:
            logger.error("Failed to create email event: %s", e)
            return None

    @staticmethod
    def update_campaign_contact_snapshot(
        db: Session,
        campaign_contact: CampaignContact,
        internal_event: InternalEvent,
        open_confidence: Optional[str] = None,
    ) -> bool:
        """Update CampaignContact snapshot fields based on event."""
        try:
            event_type = internal_event.event_type

            if event_type == EmailEventType.DELIVERED:
                campaign_contact.delivered_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.DELIVERED.value
            elif event_type == EmailEventType.UNIQUE_OPENED:
                # Same "genuine only" gate as OPENED below — unique_opened is
                # just Brevo's other open signal, and is just as capable of
                # being a prefetch/bot hit, so it must be classified too.
                if open_confidence == "genuine" and not campaign_contact.opened_at:
                    campaign_contact.opened_at = internal_event.timestamp
                    campaign_contact.status = DeliveryStatus.OPENED.value
                    logger.info("  ✓ Unique open recorded from Brevo")
                elif open_confidence != "genuine":
                    logger.info("  ℹ️  Skipping opened_at (not genuine): %s", open_confidence)
                else:
                    logger.info("  ℹ️  Skipping opened_at update (already opened at %s)", campaign_contact.opened_at)
            elif event_type == EmailEventType.OPENED:
                # Raw open event - only set if classification says genuine
                if open_confidence == "genuine" and not campaign_contact.opened_at:
                    campaign_contact.opened_at = internal_event.timestamp
                    campaign_contact.status = DeliveryStatus.OPENED.value
                    logger.info("  ✓ Genuine open recorded")
                elif open_confidence != "genuine":
                    logger.info("  ℹ️  Skipping opened_at (not genuine): %s", open_confidence)
                else:
                    logger.info("  ℹ️  Skipping opened_at (already opened at %s)", campaign_contact.opened_at)
            elif event_type == EmailEventType.CLICKED:
                campaign_contact.clicked_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.CLICKED.value
            elif event_type == EmailEventType.HARD_BOUNCE:
                campaign_contact.bounced_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.BOUNCED.value
            elif event_type == EmailEventType.SOFT_BOUNCE:
                campaign_contact.bounced_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.DEFERRED.value
            elif event_type == EmailEventType.BLOCKED:
                campaign_contact.bounced_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.BLOCKED.value
            elif event_type == EmailEventType.SPAM:
                campaign_contact.bounced_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.SPAM.value
            elif event_type == EmailEventType.UNSUBSCRIBED:
                campaign_contact.unsubscribed_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.UNSUBSCRIBED.value
            elif event_type == EmailEventType.DEFERRED:
                campaign_contact.status = DeliveryStatus.DEFERRED.value

            campaign_contact.last_event = event_type.value
            campaign_contact.last_event_at = internal_event.timestamp
            campaign_contact.updated_at = datetime.now(timezone.utc)

            db.merge(campaign_contact)
            return True

        except Exception as e:
            logger.error("Error updating campaign_contact: %s", e)
            return False

    @staticmethod
    def process_event(
        db: Session,
        campaign_contact: CampaignContact,
        internal_event: InternalEvent,
        open_confidence: Optional[str] = None,
    ) -> bool:
        """Process a single email event (atomic transaction)."""
        try:
            if TrackingService.check_duplicate_event(
                db, internal_event.provider_message_id, internal_event.event_type
            ):
                return True

            email_event = TrackingService.create_email_event(
                db, campaign_contact.id, internal_event, open_confidence=open_confidence
            )
            if not email_event:
                db.rollback()
                return False

            if not TrackingService.update_campaign_contact_snapshot(
                db, campaign_contact, internal_event, open_confidence=open_confidence
            ):
                db.rollback()
                return False

            db.commit()
            logger.info("✅ Event saved | type=%s | contact=%s | status=%s | confidence=%s",
                       internal_event.event_type.value, campaign_contact.id[:8],
                       campaign_contact.status, open_confidence or "N/A")
            return True

        except SQLAlchemyError as e:
            logger.error("✗ Database error: %s", e)
            db.rollback()
            return False
        except Exception as e:
            logger.error("✗ Event processing error: %s", e)
            db.rollback()
            return False
