"""Event Processor for normalizing provider-specific events to internal format.

This service converts provider-specific webhook payloads into a standardized
internal event format. This allows the tracking system to support multiple
email providers (Brevo, SendGrid, SES, SMTP) without coupling the rest of
the application to provider-specific formats.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from app.enums import EmailEventType

logger = logging.getLogger(__name__)


class InternalEvent:
    """Standardized internal event format."""

    def __init__(
        self,
        event_type: EmailEventType,
        provider_message_id: str,
        timestamp: datetime,
        provider: str = "brevo",
        payload: Optional[Dict[str, Any]] = None,
        email: Optional[str] = None,
    ):
        self.event_type = event_type
        self.provider_message_id = provider_message_id
        self.timestamp = timestamp
        self.provider = provider
        self.payload = payload or {}
        self.email = email

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "event_type": self.event_type.value,
            "provider_message_id": self.provider_message_id,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "email": self.email,
        }


class EventProcessor:
    """Process provider-specific webhook events into internal events."""

    @staticmethod
    def process_brevo_event(payload: Dict[str, Any]) -> Optional[InternalEvent]:
        """
        Process a Brevo webhook event.

        Brevo event format:
        {
            "event": "opened|clicked|delivered|hard_bounce|soft_bounce|complaint|unsubscribe|deferred",
            "message-id": "<message-id>",
            "email": "recipient@example.com",
            "date": 1234567890,
            "ts_event": 1234567890,
            "ts_smtp": 1234567890,
            "subject": "...",
            "uuid": "...",
            "id": 123456789
        }

        Brevo bounce status codes:
        - hard_bounce (status=4)
        - soft_bounce (status=3)
        - complaint (status=2)
        - unsubscribe (status=1)
        - deferred (status=5)
        """
        try:
            event = payload.get("event", "").lower()
            message_id = payload.get("message-id")

            if not message_id:
                logger.warning("Brevo event missing message-id: %s", payload)
                return None

            # Map Brevo event to internal event type
            event_type_map = {
                "sent": EmailEventType.SENT,
                "delivered": EmailEventType.DELIVERED,
                "opened": EmailEventType.OPENED,
                "click": EmailEventType.CLICKED,
                "hard_bounce": EmailEventType.HARD_BOUNCE,
                "soft_bounce": EmailEventType.SOFT_BOUNCE,
                "complaint": EmailEventType.SPAM,
                "unsubscribe": EmailEventType.UNSUBSCRIBED,
                "deferred": EmailEventType.DEFERRED,
                "blocked": EmailEventType.BLOCKED,
                "reply": EmailEventType.REPLIED,
            }

            event_type = event_type_map.get(event)
            if not event_type:
                logger.warning("Unknown Brevo event type: %s", event)
                return None

            # Extract timestamp (prefer ts_event, fallback to ts_smtp, then current time)
            timestamp_unix = payload.get("ts_event") or payload.get("ts_smtp") or payload.get("date")
            if timestamp_unix:
                timestamp = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            return InternalEvent(
                event_type=event_type,
                provider_message_id=message_id,
                timestamp=timestamp,
                provider="brevo",
                payload=payload,
                email=payload.get("email"),
            )

        except Exception as e:
            logger.exception("Error processing Brevo event: %s", e)
            return None

    @staticmethod
    def process_sendgrid_event(payload: Dict[str, Any]) -> Optional[InternalEvent]:
        """
        Process a SendGrid webhook event.

        SendGrid event format:
        {
            "event": "processed|dropped|delivered|deferred|bounce|open|click|spamreport|unsubscribe|group_resubscribe|group_unsubscribe",
            "email": "recipient@example.com",
            "timestamp": 1234567890,
            "smtp-id": "<message-id>",
            "message-id": "<message-id>",
            ...
        }
        """
        try:
            event = payload.get("event", "").lower()
            message_id = payload.get("smtp-id") or payload.get("message-id")

            if not message_id:
                logger.warning("SendGrid event missing message ID: %s", payload)
                return None

            # Map SendGrid event to internal event type
            event_type_map = {
                "processed": EmailEventType.SENT,
                "delivered": EmailEventType.DELIVERED,
                "deferred": EmailEventType.DEFERRED,
                "dropped": EmailEventType.BLOCKED,
                "bounce": EmailEventType.HARD_BOUNCE,
                "open": EmailEventType.OPENED,
                "click": EmailEventType.CLICKED,
                "spamreport": EmailEventType.SPAM,
                "unsubscribe": EmailEventType.UNSUBSCRIBED,
                "group_unsubscribe": EmailEventType.UNSUBSCRIBED,
                "group_resubscribe": EmailEventType.OPENED,
            }

            event_type = event_type_map.get(event)
            if not event_type:
                logger.warning("Unknown SendGrid event type: %s", event)
                return None

            timestamp_unix = payload.get("timestamp")
            if timestamp_unix:
                timestamp = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            return InternalEvent(
                event_type=event_type,
                provider_message_id=message_id,
                timestamp=timestamp,
                provider="sendgrid",
                payload=payload,
                email=payload.get("email"),
            )

        except Exception as e:
            logger.exception("Error processing SendGrid event: %s", e)
            return None

    @staticmethod
    def process_event(provider: str, payload: Dict[str, Any]) -> Optional[InternalEvent]:
        """
        Route webhook to appropriate provider processor.

        Args:
            provider: Email provider name (brevo, sendgrid, ses, smtp)
            payload: Raw webhook payload from provider

        Returns:
            Normalized internal event or None if processing fails
        """
        provider = provider.lower()

        if provider == "brevo":
            return EventProcessor.process_brevo_event(payload)
        elif provider == "sendgrid":
            return EventProcessor.process_sendgrid_event(payload)
        else:
            logger.warning("Unknown provider: %s", provider)
            return None
