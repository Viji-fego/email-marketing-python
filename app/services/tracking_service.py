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
            if campaign_contact_id:
                contact = db.query(CampaignContact).filter_by(id=campaign_contact_id).first()
                if not contact:
                    logger.warning("Campaign contact not found by ID: %s", campaign_contact_id)
                return contact

            contact = db.query(CampaignContact).filter_by(
                provider_message_id=provider_message_id
            ).first()
            if not contact:
                logger.warning("Campaign contact not found by message_id: %s", provider_message_id)
            return contact

        except SQLAlchemyError as e:
            logger.error("Database error finding campaign_contact: %s", e)
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
        """Create EmailEvent record (audit trail)."""
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
            logger.error("Failed to create email event: %s", e)
            return None

    @staticmethod
    def update_campaign_contact_snapshot(
        db: Session,
        campaign_contact: CampaignContact,
        internal_event: InternalEvent,
    ) -> bool:
        """Update CampaignContact snapshot fields based on event."""
        try:
            event_type = internal_event.event_type

            if event_type == EmailEventType.DELIVERED:
                campaign_contact.delivered_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.DELIVERED.value
            elif event_type == EmailEventType.OPENED:
                campaign_contact.opened_at = internal_event.timestamp
                campaign_contact.status = DeliveryStatus.OPENED.value
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
    ) -> bool:
        """Process a single email event (atomic transaction)."""
        try:
            if TrackingService.check_duplicate_event(
                db, internal_event.provider_message_id, internal_event.event_type
            ):
                logger.info("Duplicate event ignored: %s", internal_event.event_type.value)
                return True

            email_event = TrackingService.create_email_event(
                db, campaign_contact.id, internal_event
            )
            if not email_event:
                logger.error("Failed to create email event")
                db.rollback()
                return False

            if not TrackingService.update_campaign_contact_snapshot(
                db, campaign_contact, internal_event
            ):
                logger.error("Failed to update contact snapshot")
                db.rollback()
                return False

            db.commit()
            logger.info("Event processed: contact=%s, type=%s", campaign_contact.id, internal_event.event_type.value)
            return True

        except SQLAlchemyError as e:
            logger.error("Database transaction failed: %s", e)
            db.rollback()
            return False
        except Exception as e:
            logger.error("Unexpected error processing event: %s", e)
            db.rollback()
            return False
