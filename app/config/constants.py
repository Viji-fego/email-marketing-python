"""
Application Constants

Centralized constants used across the application.
"""

# ============================================================================
# Campaign Status Values
# ============================================================================

CAMPAIGN_STATUS_DRAFT = "draft"
CAMPAIGN_STATUS_SCHEDULED = "scheduled"
CAMPAIGN_STATUS_SENT = "sent"
CAMPAIGN_STATUS_ARCHIVED = "archived"

CAMPAIGN_STATUSES = [
    CAMPAIGN_STATUS_DRAFT,
    CAMPAIGN_STATUS_SCHEDULED,
    CAMPAIGN_STATUS_SENT,
    CAMPAIGN_STATUS_ARCHIVED,
]

# ============================================================================
# Email/Campaign Contact Status Values
# ============================================================================

CONTACT_STATUS_PENDING = "pending"
CONTACT_STATUS_SENT = "sent"
CONTACT_STATUS_FAILED = "failed"
CONTACT_STATUS_BOUNCED = "bounced"

CONTACT_STATUSES = [
    CONTACT_STATUS_PENDING,
    CONTACT_STATUS_SENT,
    CONTACT_STATUS_FAILED,
    CONTACT_STATUS_BOUNCED,
]

# ============================================================================
# Email Event Types
# ============================================================================

EVENT_TYPE_SENT = "sent"
EVENT_TYPE_FAILED = "failed"
EVENT_TYPE_OPENED = "opened"
EVENT_TYPE_CLICKED = "clicked"
EVENT_TYPE_REPLIED = "replied"
EVENT_TYPE_BOUNCED = "bounced"
EVENT_TYPE_UNSUBSCRIBED = "unsubscribed"

EMAIL_EVENT_TYPES = [
    EVENT_TYPE_SENT,
    EVENT_TYPE_FAILED,
    EVENT_TYPE_OPENED,
    EVENT_TYPE_CLICKED,
    EVENT_TYPE_REPLIED,
    EVENT_TYPE_BOUNCED,
    EVENT_TYPE_UNSUBSCRIBED,
]

# ============================================================================
# Validation Rules
# ============================================================================

# Email
MIN_EMAIL_LENGTH = 5
MAX_EMAIL_LENGTH = 191

# Campaign Name
MIN_CAMPAIGN_NAME_LENGTH = 1
MAX_CAMPAIGN_NAME_LENGTH = 255

# Contact Name
MIN_CONTACT_NAME_LENGTH = 1
MAX_CONTACT_NAME_LENGTH = 255

# Contact University
MIN_UNIVERSITY_LENGTH = 1
MAX_UNIVERSITY_LENGTH = 255

# Password
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# ============================================================================
# API Response Messages
# ============================================================================

MSG_SUCCESS = "Success"
MSG_CREATED = "Resource created successfully"
MSG_UPDATED = "Resource updated successfully"
MSG_DELETED = "Resource deleted successfully"
MSG_NOT_FOUND = "Resource not found"
MSG_UNAUTHORIZED = "Unauthorized"
MSG_FORBIDDEN = "Forbidden"
MSG_VALIDATION_ERROR = "Validation error"
MSG_SERVER_ERROR = "Internal server error"
