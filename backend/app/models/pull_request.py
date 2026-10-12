from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    number = Column(Integer, nullable=False, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    author = Column(String, nullable=False)
    author_avatar = Column(String, nullable=True)
    head_branch = Column(String, nullable=False)
    base_branch = Column(String, nullable=False)
    state = Column(String, default="open") # open, closed, merged
    status = Column(String, default="pending") # pending, analyzing, completed, failed
    quality_score = Column(Integer, default=0)
    security_score = Column(Integer, default=0)
    architecture_score = Column(Integer, default=0)
    overall_score = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    diff_data = Column(JSON, nullable=True) # file paths, changed lines, diff content
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    repository = relationship("Repository", back_populates="pull_requests")
    review_comments = relationship("ReviewComment", back_populates="pull_request", cascade="all, delete-orphan")
    security_findings = relationship("SecurityFinding", back_populates="pull_request", cascade="all, delete-orphan")
    architecture_findings = relationship("ArchitectureFinding", back_populates="pull_request", cascade="all, delete-orphan")
