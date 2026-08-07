"""Webhook service for handling email provider webhooks.

Orchestrates the webhook processing pipeline:
1. Normalize provider payload using EventProcessor
2. Find campaign_contact using message ID
3. Process event using TrackingService
4. Return status
"""

import logging
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.services.event_processor import EventProcessor
from app.services.tracking_service import TrackingService
from app.models import CampaignContact

logger = logging.getLogger(__name__)


class WebhookService:
    """Handle webhook processing and coordination."""

    @staticmethod
    def process_brevo_webhook(
        db: Session, payload: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a Brevo webhook event.

        Args:
            db: Database session
            payload: Webhook payload from Brevo

        Returns:
            Tuple of (success: bool, response: dict)
        """
        try:
            internal_event = EventProcessor.process_brevo_event(payload)

            if not internal_event:
                return True, {"status": "ignored", "reason": "Failed to normalize event"}

            # Tags-first correlation for opens/clicks (email & message-id unreliable for these)
            event_type = payload.get("event", "").lower()
            campaign_contact = None

            if event_type in ["opened", "unique_opened", "click", "clicked"]:
                # Primary: use campaign_contact_id from tags
                tags = payload.get("tags", [])
                if tags and isinstance(tags, list) and len(tags) > 0:
                    campaign_contact_id = tags[0]
                    campaign_contact = db.query(CampaignContact).filter_by(id=campaign_contact_id).first()
                    if campaign_contact:
                        logger.info("✓ Correlated by tags: %s", campaign_contact_id)
                    else:
                        logger.warning("✗ Open/click event: contact not found by tags=%s", campaign_contact_id)
                else:
                    logger.warning("✗ Open/click event missing tags; attempting message-id fallback")
                    campaign_contact = TrackingService.find_campaign_contact(
                        db,
                        provider_message_id=internal_event.provider_message_id,
                        campaign_contact_id=internal_event.campaign_contact_id,
                    )
            else:
                # Fallback: message-id for sent/delivered/bounce
                campaign_contact = TrackingService.find_campaign_contact(
                    db,
                    provider_message_id=internal_event.provider_message_id,
                    campaign_contact_id=internal_event.campaign_contact_id,
                )

            if not campaign_contact:
                return True, {"status": "not_found", "reason": "Campaign contact not found"}

            # Classify opens before processing
            open_confidence = None
            event_type = payload.get("event", "").lower()
            if event_type in ["opened", "unique_opened"]:
                from app.services.event_processor import classify_open_event
                from app.config.settings import settings
                open_confidence = classify_open_event(
                    payload,
                    campaign_contact,
                    prefetch_threshold_seconds=settings.OPEN_PREFETCH_THRESHOLD_SECONDS
                )
                logger.info("→ STEP 3: Open classified as: %s for contact=%s", open_confidence, campaign_contact.id)

            logger.info("→ STEP 3: Starting event processing for contact=%s", campaign_contact.id)
            success = TrackingService.process_event(
                db, campaign_contact, internal_event, open_confidence=open_confidence
            )

            if success:
                logger.info("✅ Event processed | type=%s | contact=%s | confidence=%s",
                           internal_event.event_type.value, campaign_contact.id[:8],
                           open_confidence or "N/A")
                return True, {
                    "status": "success",
                    "campaign_contact_id": campaign_contact.id,
                    "event_type": internal_event.event_type.value,
                    "open_confidence": open_confidence,
                }

            logger.warning("⚠️  Event failed to process | type=%s", internal_event.event_type.value)
            return True, {"status": "error", "reason": "Failed to process event"}

        except Exception as e:
            logger.error("✗ Webhook error: %s", str(e))
            return True, {"status": "error", "reason": str(e)}

    @staticmethod
    def process_sendgrid_webhook(
        db: Session, payload: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a SendGrid webhook event.

        Args:
            db: Database session
            payload: Webhook payload from SendGrid

        Returns:
            Tuple of (success: bool, response: dict)
        """
        try:
            internal_event = EventProcessor.process_sendgrid_event(payload)

            if not internal_event:
                logger.warning("Failed to normalize SendGrid event")
                return True, {"status": "ignored", "reason": "Failed to normalize event"}

            campaign_contact = TrackingService.find_campaign_contact(
                db,
                provider_message_id=internal_event.provider_message_id,
                campaign_contact_id=internal_event.campaign_contact_id,
            )

            if not campaign_contact:
                logger.warning("Campaign contact not found")
                return True, {"status": "not_found", "reason": "Campaign contact not found"}

            success = TrackingService.process_event(db, campaign_contact, internal_event)

            if success:
                return True, {
                    "status": "success",
                    "campaign_contact_id": campaign_contact.id,
                    "event_type": internal_event.event_type.value,
                }
            return True, {"status": "error", "reason": "Failed to process event"}

        except Exception as e:
            logger.error("Error processing SendGrid webhook: %s", e)
            return True, {"status": "error", "reason": str(e)}

    @staticmethod
    def process_webhook(
        db: Session, provider: str, payload: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Route webhook to provider-specific processor.

        Args:
            db: Database session
            provider: Email provider name (brevo, sendgrid, etc.)
            payload: Webhook payload

        Returns:
            Tuple of (success: bool, response: dict)
        """
        provider = provider.lower()

        if provider == "brevo":
            return WebhookService.process_brevo_webhook(db, payload)
        elif provider == "sendgrid":
            return WebhookService.process_sendgrid_webhook(db, payload)
        else:
            logger.warning("Unknown webhook provider: %s", provider)
            return (
                True,
                {
                    "status": "error",
                    "reason": f"Unknown provider: {provider}",
                },
            )
