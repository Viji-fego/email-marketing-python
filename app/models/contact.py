from sqlalchemy import Column, DateTime, String, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, gen_uuid, utcnow


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    email = Column(String(191), nullable=False, index=True)
    university = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    is_active = Column(Enum('1', '0'), default='1', nullable=False)

    user = relationship("User")
