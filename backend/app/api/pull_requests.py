from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.repository import Repository
from app.models.pull_request import PullRequest
from app.models.review import ReviewComment
from app.models.security import SecurityFinding
from app.models.architecture import ArchitectureFinding
from app.schemas.schemas import PullRequestCreate, PullRequestResponse
from app.services.security_scanner import SecurityScanner
from app.services.architecture_analyzer import ArchitectureAnalyzer
from app.services.ai_engine import AICodeAnalysisEngine
from app.utils.diff_parser import DiffParser

router = APIRouter(prefix="/pull-requests", tags=["Pull Requests"])

async def run_manual_pr_analysis(pr_id: int, db: Session):
    """Runs full analysis pipeline for a PR on demand."""
    pr = db.query(PullRequest).filter(PullRequest.id == pr_id).first()
    if not pr:
        return

    pr.status = "analyzing"
    db.commit()

    diff_data = pr.diff_data or {}
    raw_diff = diff_data.get("raw", "")
    parsed_files = diff_data.get("files", [])
    if not parsed_files and raw_diff:
        parsed_files = DiffParser.parse_diff(raw_diff)

    # 1. Security scan
    sec_scanner = SecurityScanner()
    sec_res = sec_scanner.scan_diff(parsed_files, pr.repository_id, pr.id)

    # Delete existing findings before re-adding
    db.query(SecurityFinding).filter(SecurityFinding.pull_request_id == pr.id).delete()
    for sf in sec_res["findings"]:
        db.add(SecurityFinding(**sf))

    # 2. Architecture scan
    arch_analyzer = ArchitectureAnalyzer()
    arch_res = arch_analyzer.analyze_diff(parsed_files, pr.repository_id, pr.id)

    db.query(ArchitectureFinding).filter(ArchitectureFinding.pull_request_id == pr.id).delete()
    for af in arch_res["findings"]:
        db.add(ArchitectureFinding(**af))

    # 3. AI review engine
    ai_engine = AICodeAnalysisEngine()
    ai_res = await ai_engine.analyze_pr_diff(pr.title, pr.body or "", parsed_files, sec_res, arch_res)

    db.query(ReviewComment).filter(ReviewComment.pull_request_id == pr.id).delete()
    for c in ai_res.get("comments", []):
        db.add(ReviewComment(
            pull_request_id=pr.id,
            file_path=c.get("file_path", "app.py"),
            line_number=c.get("line_number", 1),
            severity=c.get("severity", "Medium"),
            category=c.get("category", "Code Quality"),
            title=c.get("title", "Review Item"),
            description=c.get("description", ""),
            why_it_matters=c.get("why_it_matters", ""),
            suggested_fix=c.get("suggested_fix", ""),
            example_code=c.get("example_code", "")
        ))

    pr.summary = ai_res.get("summary")
    pr.quality_score = ai_res.get("quality_score", 85)
    pr.security_score = ai_res.get("security_score", 90)
    pr.architecture_score = ai_res.get("architecture_score", 80)
    pr.overall_score = ai_res.get("overall_score", 85)
    pr.status = "completed"

    db.commit()

@router.get("", response_model=List[PullRequestResponse])
def get_pull_requests(repository_id: Optional[int] = None, state: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(PullRequest)
    if repository_id:
        query = query.filter(PullRequest.repository_id == repository_id)
    if state:
        query = query.filter(PullRequest.state == state)
    return query.order_by(PullRequest.created_at.desc()).all()

@router.get("/{pr_id}", response_model=PullRequestResponse)
def get_pull_request_detail(pr_id: int, db: Session = Depends(get_db)):
    pr = db.query(PullRequest).filter(PullRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pull Request not found")
    return pr

@router.post("/{pr_id}/analyze")
async def trigger_pr_analysis(pr_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    pr = db.query(PullRequest).filter(PullRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pull Request not found")
    
    background_tasks.add_task(run_manual_pr_analysis, pr_id, db)
    return {"message": "Analysis started", "pr_id": pr_id, "status": "analyzing"}
