from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class ArchitectureFinding(Base):
    __tablename__ = "architecture_findings"

    id = Column(Integer, primary_key=True, index=True)
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    principle_violated = Column(String, nullable=False) # SOLID (SRP, OCP, LSP, ISP, DIP), Tight Coupling, Circular Dependency, God Object
    severity = Column(String, nullable=False) # High, Medium, Low
    component = Column(String, nullable=False) # Module or Class name
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    design_pattern_suggested = Column(String, nullable=True) # Factory, Observer, Dependency Injection, Strategy, etc.
    status = Column(String, default="open") # open, addressed, ignored
    created_at = Column(DateTime, default=datetime.utcnow)

    pull_request = relationship("PullRequest", back_populates="architecture_findings")
