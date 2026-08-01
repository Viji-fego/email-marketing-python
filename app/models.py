import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(191), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=True)
    email = Column(String(191), unique=True, nullable=False, index=True)
    university = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=utcnow)


class CampaignContact(Base):
    __tablename__ = "campaign_contacts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    contact_id = Column(String(36), ForeignKey("contacts.id"), nullable=False)
    status = Column(String(50), default="pending")  # pending | sent | failed
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    campaign = relationship("Campaign")
    contact = relationship("Contact")


class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    campaign_contact_id = Column(String(36), ForeignKey("campaign_contacts.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # sent | failed | opened | clicked | replied | bounced
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
