from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import Base, gen_uuid, utcnow


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
