from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from app.models.base import Base, gen_uuid, utcnow


class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    campaign_contact_id = Column(String(36), ForeignKey("campaign_contacts.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # sent | failed | opened | clicked | replied | bounced
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
