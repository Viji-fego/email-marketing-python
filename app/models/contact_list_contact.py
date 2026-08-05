from sqlalchemy import Column, DateTime, String, ForeignKey, Index, Enum

from app.models.base import Base, gen_uuid, utcnow


class ContactListContact(Base):
    __tablename__ = "contact_list_contacts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    contact_list_id = Column(String(36), ForeignKey("contact_lists.id"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    is_active = Column(Enum('1', '0'), default='1', nullable=False)

    __table_args__ = (
        Index('idx_contact_list_contacts_list', 'contact_list_id'),
        Index('idx_contact_list_contacts_contact', 'contact_id'),
    )
