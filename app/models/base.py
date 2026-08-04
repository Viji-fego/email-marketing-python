import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import declarative_base

Base = declarative_base()


def gen_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)
