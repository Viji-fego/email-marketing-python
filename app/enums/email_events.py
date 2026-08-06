"""Email event type enums for tracking system."""

from enum import Enum


class EmailEventType(str, Enum):
    """Email event types for tracking."""

    # Sending
    SENT = "sent"
    FAILED = "failed"

    # Delivery
    DELIVERED = "delivered"
    DEFERRED = "deferred"
    BLOCKED = "blocked"

    # Engagement
    UNIQUE_OPENED = "unique_opened"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"

    # Bounces
    HARD_BOUNCE = "hard_bounce"
    SOFT_BOUNCE = "soft_bounce"

    # Suppression
    SPAM = "spam"
    UNSUBSCRIBED = "unsubscribed"

    @classmethod
    def is_engagement(cls, event_type: str) -> bool:
        """Check if event is engagement-related."""
        return event_type in (cls.UNIQUE_OPENED, cls.OPENED, cls.CLICKED, cls.REPLIED)

    @classmethod
    def is_bounce(cls, event_type: str) -> bool:
        """Check if event is a bounce."""
        return event_type in (cls.HARD_BOUNCE, cls.SOFT_BOUNCE)

    @classmethod
    def is_suppression(cls, event_type: str) -> bool:
        """Check if event is suppression-related."""
        return event_type in (cls.SPAM, cls.UNSUBSCRIBED)

    @classmethod
    def is_delivery(cls, event_type: str) -> bool:
        """Check if event is delivery-related."""
        return event_type in (cls.DELIVERED, cls.DEFERRED, cls.BLOCKED)


class DeliveryStatus(str, Enum):
    """Campaign contact delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    SPAM = "spam"
    UNSUBSCRIBED = "unsubscribed"
    FAILED = "failed"
