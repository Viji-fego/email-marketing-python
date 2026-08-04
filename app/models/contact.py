from sqlalchemy import Column, DateTime, String

from app.models.base import Base, gen_uuid, utcnow


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=True)
    email = Column(String(191), unique=True, nullable=False, index=True)
    university = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
