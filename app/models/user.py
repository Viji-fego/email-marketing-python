from sqlalchemy import Column, DateTime, String, Enum

from app.models.base import Base, gen_uuid, utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(191), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    is_active = Column(Enum('1', '0'), default='1', nullable=False)
