from sqlalchemy import Column, DateTime, String, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, gen_uuid, utcnow


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="draft")
    contact_list_id = Column(String(36), ForeignKey("contact_lists.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    is_active = Column(Enum('1', '0'), default='1', nullable=False)

    contact_list = relationship("ContactList")
