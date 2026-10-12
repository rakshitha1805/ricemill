from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.security import SecurityFinding
from app.schemas.schemas import SecurityFindingResponse

router = APIRouter(prefix="/security", tags=["Security Findings"])

@router.get("/findings", response_model=List[SecurityFindingResponse])
def get_security_findings(repository_id: Optional[int] = None, severity: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(SecurityFinding)
    if repository_id:
        query = query.filter(SecurityFinding.repository_id == repository_id)
    if severity:
        query = query.filter(SecurityFinding.severity == severity)
    return query.order_by(SecurityFinding.created_at.desc()).all()
