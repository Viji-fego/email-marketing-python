from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON, Index, Enum

from app.models.base import Base, gen_uuid, utcnow


class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    campaign_contact_id = Column(String(36), ForeignKey("campaign_contacts.id"), nullable=False, index=True)
    provider_message_id = Column(String(100), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    provider = Column(String(50), default="brevo")
    payload = Column(JSON, nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    is_active = Column(Enum('1', '0'), default='1', nullable=False)

    __table_args__ = (
        Index('idx_event_type_created', 'event_type', 'created_at'),
        Index('idx_campaign_contact_event', 'campaign_contact_id', 'event_type'),
    )
