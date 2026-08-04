"""Webhook routes for receiving email provider events.

Routes:
- POST /webhooks/brevo - Receive Brevo webhook events
"""

import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_db
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/brevo")
async def receive_brevo_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive webhook events from Brevo.

    Brevo sends POST requests with event data whenever:
    - Email is sent
    - Email is delivered
    - Email is opened
    - Link is clicked
    - Email bounces (hard/soft)
    - User complains (marks as spam)
    - User unsubscribes
    - And more...

    We always return 200 OK to Brevo immediately after initial validation.
    Errors are logged internally and do not affect the response.

    Webhook payload example:
    ```json
    {
        "event": "opened",
        "message-id": "<message-id>",
        "email": "recipient@example.com",
        "ts_event": 1234567890,
        "date": 1234567890,
        "ts_smtp": 1234567890,
        "subject": "Email subject",
        "uuid": "unique-id",
        "id": 123456789
    }
    ```
    """
    try:
        # Parse request body
        payload = await request.json()

        # LOG: Incoming webhook payload
        logger.info("=" * 80)
        logger.info("BREVO WEBHOOK RECEIVED")
        logger.info("=" * 80)
        logger.info("Event Type: %s", payload.get("event"))
        logger.info("Message ID: %s", payload.get("message-id"))
        logger.info("Email: %s", payload.get("email"))
        logger.info("Timestamp (ts_event): %s", payload.get("ts_event"))

        # Log full webhook payload in JSON format
        import json
        logger.info("FULL WEBHOOK PAYLOAD:")
        logger.info(json.dumps(payload, indent=2, default=str))
        logger.info("=" * 80)

        # Validate payload has required fields
        if not payload.get("message-id"):
            logger.warning("❌ BREVO WEBHOOK - Missing message-id")
            return {
                "status": "ignored",
                "reason": "Missing message-id",
            }

        # Process webhook event
        logger.info("🔄 Processing webhook through WebhookService...")
        success, response = WebhookService.process_brevo_webhook(db, payload)

        # LOG: Response
        logger.info("=" * 80)
        logger.info("WEBHOOK PROCESSING RESULT")
        logger.info("=" * 80)
        logger.info("Status: %s", response.get("status"))
        logger.info("Event Type: %s", response.get("event_type"))
        logger.info("Campaign Contact ID: %s", response.get("campaign_contact_id"))
        logger.info("Reason/Error: %s", response.get("reason"))

        import json
        logger.info("FULL RESPONSE:")
        logger.info(json.dumps(response, indent=2, default=str))
        logger.info("=" * 80)

        # Always return 200 OK (even on errors)
        return response

    except ValueError as e:
        # JSON parsing error
        logger.warning("❌ Invalid JSON in webhook request: %s", e)
        return {
            "status": "error",
            "reason": "Invalid JSON",
        }
    except Exception as e:
        # Unexpected error - still return 200 OK
        logger.exception("❌ Unexpected error in webhook handler: %s", e)
        return {
            "status": "error",
            "reason": "Internal server error",
        }


@router.post("/sendgrid")
async def receive_sendgrid_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive webhook events from SendGrid (future support).

    SendGrid sends webhook events for various email events.
    This endpoint follows the same pattern as Brevo for consistency.
    """
    try:
        # Parse request body
        payload = await request.json()

        # Validate payload has required fields
        if not payload.get("smtp-id") and not payload.get("message-id"):
            logger.warning("SendGrid webhook missing message ID")
            return {
                "status": "ignored",
                "reason": "Missing message ID",
            }

        # Process webhook event
        success, response = WebhookService.process_sendgrid_webhook(db, payload)

        # Always return 200 OK
        return response

    except ValueError as e:
        logger.warning("Invalid JSON in SendGrid webhook: %s", e)
        return {
            "status": "error",
            "reason": "Invalid JSON",
        }
    except Exception as e:
        logger.exception("Unexpected error in SendGrid webhook handler: %s", e)
        return {
            "status": "error",
            "reason": "Internal server error",
        }


@router.get("/health")
def webhook_health():
    """Health check endpoint for webhook service."""
    return {"status": "healthy"}
