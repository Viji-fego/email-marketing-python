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
                logger.warning("Failed to normalize Brevo event")
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
            logger.error("Error processing Brevo webhook: %s", e)
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
