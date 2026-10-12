from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class ReviewComment(Base):
    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, index=True)
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    file_path = Column(String, nullable=False)
    line_number = Column(Integer, nullable=True)
    severity = Column(String, nullable=False) # Critical, High, Medium, Low
    category = Column(String, nullable=False) # Code Quality, Security, Performance, SOLID, Maintainability
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    why_it_matters = Column(Text, nullable=False)
    suggested_fix = Column(Text, nullable=True)
    example_code = Column(Text, nullable=True)
    status = Column(String, default="open") # open, resolved, ignored
    github_comment_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pull_request = relationship("PullRequest", back_populates="review_comments")
