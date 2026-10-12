from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.architecture import ArchitectureFinding
from app.schemas.schemas import ArchitectureFindingResponse

router = APIRouter(prefix="/architecture", tags=["Architecture Findings"])

@router.get("/findings", response_model=List[ArchitectureFindingResponse])
def get_architecture_findings(repository_id: Optional[int] = None, principle: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ArchitectureFinding)
    if repository_id:
        query = query.filter(ArchitectureFinding.repository_id == repository_id)
    if principle:
        query = query.filter(ArchitectureFinding.principle_violated.contains(principle))
    return query.order_by(ArchitectureFinding.created_at.desc()).all()
