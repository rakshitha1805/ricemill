from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.repository import Repository
from app.models.pull_request import PullRequest
from app.schemas.schemas import RepositoryCreate, RepositoryResponse

router = APIRouter(prefix="/repositories", tags=["Repositories"])

@router.get("", response_model=List[RepositoryResponse])
def get_repositories(db: Session = Depends(get_db)):
    repos = db.query(Repository).all()
    res = []
    for r in repos:
        open_count = db.query(PullRequest).filter(PullRequest.repository_id == r.id, PullRequest.state == "open").count()
        r_dict = RepositoryResponse.from_orm(r)
        r_dict.open_prs_count = open_count
        res.append(r_dict)
    return res

@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def connect_repository(repo_in: RepositoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Repository).filter(Repository.full_name == repo_in.full_name).first()
    if existing:
        return existing
    
    repo = Repository(
        name=repo_in.name,
        full_name=repo_in.full_name,
        owner=repo_in.owner,
        default_branch=repo_in.default_branch,
        is_private=repo_in.is_private,
        description=repo_in.description,
        language=repo_in.language or "TypeScript",
        webhook_active=True,
        webhook_id="wh_mock_10293"
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo

@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo
