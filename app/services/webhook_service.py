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
            # Step 1: Normalize Brevo event to internal format
            internal_event = EventProcessor.process_brevo_event(payload)

            if not internal_event:
                logger.warning("Failed to process Brevo webhook payload: %s", payload)
                return (
                    True,  # Still return success (200 OK) to Brevo
                    {
                        "status": "ignored",
                        "reason": "Failed to normalize event",
                    },
                )

            # Step 2: Find campaign_contact by message ID
            campaign_contact = TrackingService.find_campaign_contact(
                db, internal_event.provider_message_id
            )

            if not campaign_contact:
                logger.warning(
                    "Campaign contact not found for message ID: %s",
                    internal_event.provider_message_id,
                )
                return (
                    True,  # Still return success (200 OK) to Brevo
                    {
                        "status": "not_found",
                        "reason": f"Campaign contact not found for {internal_event.provider_message_id}",
                    },
                )

            # Step 3: Process event
            success = TrackingService.process_event(db, campaign_contact, internal_event)

            if success:
                return (
                    True,
                    {
                        "status": "success",
                        "campaign_contact_id": campaign_contact.id,
                        "event_type": internal_event.event_type.value,
                    },
                )
            else:
                return (
                    True,  # Still return success (200 OK) to Brevo
                    {
                        "status": "error",
                        "reason": "Failed to process event",
                    },
                )

        except Exception as e:
            logger.exception("Unexpected error processing Brevo webhook: %s", e)
            return (
                True,  # Still return success (200 OK) to Brevo
                {
                    "status": "error",
                    "reason": str(e),
                },
            )

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
            # Step 1: Normalize SendGrid event to internal format
            internal_event = EventProcessor.process_sendgrid_event(payload)

            if not internal_event:
                logger.warning("Failed to process SendGrid webhook payload: %s", payload)
                return (
                    True,
                    {
                        "status": "ignored",
                        "reason": "Failed to normalize event",
                    },
                )

            # Step 2: Find campaign_contact by message ID
            campaign_contact = TrackingService.find_campaign_contact(
                db, internal_event.provider_message_id
            )

            if not campaign_contact:
                logger.warning(
                    "Campaign contact not found for message ID: %s",
                    internal_event.provider_message_id,
                )
                return (
                    True,
                    {
                        "status": "not_found",
                        "reason": f"Campaign contact not found for {internal_event.provider_message_id}",
                    },
                )

            # Step 3: Process event
            success = TrackingService.process_event(db, campaign_contact, internal_event)

            if success:
                return (
                    True,
                    {
                        "status": "success",
                        "campaign_contact_id": campaign_contact.id,
                        "event_type": internal_event.event_type.value,
                    },
                )
            else:
                return (
                    True,
                    {
                        "status": "error",
                        "reason": "Failed to process event",
                    },
                )

        except Exception as e:
            logger.exception("Unexpected error processing SendGrid webhook: %s", e)
            return (
                True,
                {
                    "status": "error",
                    "reason": str(e),
                },
            )

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
