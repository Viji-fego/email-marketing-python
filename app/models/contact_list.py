from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, Enum, Text, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, gen_uuid, utcnow


class ContactList(Base):
    __tablename__ = "contact_lists"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    contact_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    is_active = Column(Enum('1', '0'), default='1', nullable=False, index=True)

    contacts = relationship("Contact", secondary="contact_list_contacts", viewonly=True)
    user = relationship("User")

    __table_args__ = (
        Index('idx_contact_lists_user_id_active', 'user_id', 'is_active'),
    )
