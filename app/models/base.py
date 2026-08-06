import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import declarative_base

Base = declarative_base()


def gen_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """Serialize a datetime as an ISO string with an explicit UTC offset.

    MySQL's DATETIME column strips tzinfo on write, so values read back
    from the DB are naive but are always UTC (see utcnow()). Without the
    explicit offset, JS `Date` parses the string as local time instead
    of UTC, shifting displayed times/dates for any non-UTC timezone.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
