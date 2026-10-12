from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    full_name = Column(String, unique=True, index=True, nullable=False)
    owner = Column(String, nullable=False)
    default_branch = Column(String, default="main")
    is_private = Column(Boolean, default=False)
    webhook_active = Column(Boolean, default=True)
    webhook_id = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    language = Column(String, nullable=True)
    quality_score = Column(Integer, default=85)
    security_score = Column(Integer, default=90)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pull_requests = relationship("PullRequest", back_populates="repository", cascade="all, delete-orphan")
