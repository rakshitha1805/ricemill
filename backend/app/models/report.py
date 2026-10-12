from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from datetime import datetime
from app.database import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    title = Column(String, nullable=False)
    report_type = Column(String, default="full_audit") # pr_review, repository_audit, executive_summary
    pdf_filename = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
