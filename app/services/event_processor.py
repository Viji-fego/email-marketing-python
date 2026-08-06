"""Event Processor for normalizing provider-specific events to internal format.

This service converts provider-specific webhook payloads into a standardized
internal event format. This allows the tracking system to support multiple
email providers (Brevo, SendGrid, SES, SMTP) without coupling the rest of
the application to provider-specific formats.
"""

import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from app.enums import EmailEventType

logger = logging.getLogger(__name__)


def is_stale_user_agent(user_agent: str) -> bool:
    """
    Detect if user-agent contains a Chrome/Safari/Firefox version > 18 months old.
    Real browsers auto-update; stale versions signal automation.
    """
    if not user_agent:
        return False

    # Chrome version check (stale if < 90, roughly from 2021)
    chrome_match = re.search(r'Chrome/(\d+)', user_agent)
    if chrome_match:
        try:
            version = int(chrome_match.group(1))
            if version < 90:
                return True
        except (ValueError, IndexError):
            pass

    return False


def has_scanner_pattern(user_agent: str) -> bool:
    """
    Detect known scanner/proxy patterns in user-agent.
    """
    if not user_agent:
        return False

    scanner_patterns = [
        r'bot(?!tleneck)',  # bot but not bottleneck
        r'crawler',
        r'spider',
        r'scrapybot',
        r'curl',
        r'wget',
        r'python-requests',
        r'prefetch',
        r'facebookexternalhit',
    ]

    ua_lower = user_agent.lower()
    return any(re.search(pattern, ua_lower) for pattern in scanner_patterns)


def classify_open_event(
    payload: dict,
    campaign_contact,
    prefetch_threshold_seconds: int = 10
) -> str:
    """
    Classify open event as genuine, likely_prefetch, or likely_bot_scan.

    Args:
        payload: Webhook payload from Brevo
        campaign_contact: CampaignContact model instance
        prefetch_threshold_seconds: Time in seconds; opens faster than this
                                     are flagged as likely prefetch

    Returns:
        "genuine" | "likely_prefetch" | "likely_bot_scan"
    """
    # Extract event timestamp
    timestamp_unix = payload.get("ts_event") or payload.get("ts_smtp")
    if timestamp_unix:
        timestamp = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    # Check 1: Timing (prefetch signal)
    if campaign_contact.sent_at:
        # Handle timezone-naive sent_at from database
        sent_at = campaign_contact.sent_at
        if sent_at.tzinfo is None:
            # Convert naive datetime to UTC-aware
            sent_at = sent_at.replace(tzinfo=timezone.utc)

        time_to_open = (timestamp - sent_at).total_seconds()
        if time_to_open < prefetch_threshold_seconds:
            logger.info("🚫 Prefetch detected (%.1fs) | threshold=%s", time_to_open, prefetch_threshold_seconds)
            return "likely_prefetch"

    # Check 2: User-Agent staleness
    user_agent = payload.get("user_agent", "")
    if is_stale_user_agent(user_agent):
        logger.info("🚫 Stale browser detected | ua=%s", user_agent[:50])
        return "likely_bot_scan"

    # Check 3: Scanner patterns
    if has_scanner_pattern(user_agent):
        logger.info("🚫 Bot pattern detected | ua=%s", user_agent[:50])
        return "likely_bot_scan"

    return "genuine"


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
        campaign_contact_id: Optional[str] = None,
    ):
        self.event_type = event_type
        self.provider_message_id = provider_message_id
        self.timestamp = timestamp
        self.provider = provider
        self.payload = payload or {}
        self.email = email
        self.campaign_contact_id = campaign_contact_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "event_type": self.event_type.value,
            "provider_message_id": self.provider_message_id,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "email": self.email,
            "campaign_contact_id": self.campaign_contact_id,
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
            logger.info("STEP 1: Normalizing Brevo event...")
            event = payload.get("event", "").lower()
            message_id = payload.get("message-id")
            logger.info("  Event type: %s", event)
            logger.info("  Message ID: %s", message_id)

            if not message_id:
                logger.warning("✗ Event missing message-id: %s", payload)
                return None

            # Map Brevo event to internal event type
            # Note: unique_opened is Brevo's event for first-time opens (distinct from repeated opens)
            event_type_map = {
                "sent": EmailEventType.SENT,
                "delivered": EmailEventType.DELIVERED,
                "opened": EmailEventType.OPENED,
                "unique_opened": EmailEventType.OPENED,  # First-time open
                "click": EmailEventType.CLICKED,
                "hard_bounce": EmailEventType.HARD_BOUNCE,
                "soft_bounce": EmailEventType.SOFT_BOUNCE,
                "complaint": EmailEventType.SPAM,
                "unsubscribe": EmailEventType.UNSUBSCRIBED,
                "deferred": EmailEventType.DEFERRED,
                "blocked": EmailEventType.BLOCKED,
                "reply": EmailEventType.REPLIED,
                "invalid_email": EmailEventType.HARD_BOUNCE,
            }

            event_type = event_type_map.get(event)
            if not event_type:
                # Silently ignore unknown event types like "request"
                return None

            logger.info("  ✓ Event type mapped: %s", event_type.value)

            # Extract timestamp (prefer ts_event, fallback to ts_smtp, then current time)
            timestamp_unix = payload.get("ts_event") or payload.get("ts_smtp") or payload.get("date")
            if timestamp_unix:
                timestamp = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            # Extract campaign_contact_id from tags (primary lookup key)
            # Tags are sent as a list; our tag is the campaign_contact_id
            # This is especially important for open/click events where email/message-id may be unreliable
            campaign_contact_id = None
            tags = payload.get("tags")
            if tags and isinstance(tags, list) and len(tags) > 0:
                campaign_contact_id = tags[0]
                logger.info("  📌 Campaign contact ID from tags: %s", campaign_contact_id)
            elif event in ["opened", "unique_opened", "click", "clicked"]:
                logger.warning("  ⚠️  Open/click event missing tags; will require message-id fallback")

            logger.info("✓ STEP 1: Event normalized successfully")

            return InternalEvent(
                event_type=event_type,
                provider_message_id=message_id,
                timestamp=timestamp,
                provider="brevo",
                payload=payload,
                email=payload.get("email"),
                campaign_contact_id=campaign_contact_id,
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
