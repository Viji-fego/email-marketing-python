from sqlalchemy import Column, DateTime, String

from app.models.base import Base, gen_uuid, utcnow


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=utcnow)
