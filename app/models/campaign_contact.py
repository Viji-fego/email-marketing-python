from sqlalchemy import Column, DateTime, ForeignKey, String, Index, Enum
from sqlalchemy.orm import relationship

from app.models.base import Base, gen_uuid, utcnow


class CampaignContact(Base):
    __tablename__ = "campaign_contacts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id"), nullable=False)
    provider_message_id = Column(String(100), unique=True, nullable=True, index=True)

    status = Column(String(50), default="pending", index=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    bounced_at = Column(DateTime, nullable=True)
    unsubscribed_at = Column(DateTime, nullable=True)
    last_event = Column(String(50), nullable=True)
    last_event_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    is_active = Column(Enum('1', '0'), default='1', nullable=False)

    campaign = relationship("Campaign")
    contact = relationship("Contact")

    __table_args__ = (
        Index('idx_campaign_status', 'campaign_id', 'status'),
        Index('idx_provider_message_id', 'provider_message_id'),
    )
