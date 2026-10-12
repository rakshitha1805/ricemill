from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class SecurityFinding(Base):
    __tablename__ = "security_findings"

    id = Column(Integer, primary_key=True, index=True)
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    vulnerability_type = Column(String, nullable=False) # SQL Injection, Hardcoded Secret, XSS, SSRF, Auth Bypass, Insecure Dependency
    cve_id = Column(String, nullable=True) # e.g., CVE-2024-1234
    severity = Column(String, nullable=False) # Critical, High, Medium, Low
    file_path = Column(String, nullable=False)
    line_number = Column(Integer, nullable=True)
    raw_snippet = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    risk_score = Column(Integer, default=50) # 0 to 100
    status = Column(String, default="open") # open, fixed, suppressed
    created_at = Column(DateTime, default=datetime.utcnow)

    pull_request = relationship("PullRequest", back_populates="security_findings")
