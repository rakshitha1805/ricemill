import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.review import ReviewComment
from app.models.report import Report
from app.schemas.schemas import ReportResponse
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/reports", tags=["Reports"])
REPORTS_DIR = os.path.join(os.getcwd(), "generated_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

@router.post("/pr/{pr_id}/generate", response_model=ReportResponse)
def generate_pr_pdf_report(pr_id: int, db: Session = Depends(get_db)):
    pr = db.query(PullRequest).filter(PullRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pull Request not found")
    
    repo = db.query(Repository).filter(Repository.id == pr.repository_id).first()
    repo_name = repo.full_name if repo else "unknown/repo"
    comments = db.query(ReviewComment).filter(ReviewComment.pull_request_id == pr_id).all()

    filename = f"report_pr_{pr_id}_{pr.number}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    comments_list = [
        {
            "severity": c.severity,
            "category": c.category,
            "file_path": c.file_path,
            "title": c.title
        } for c in comments
    ]

    ReportGenerator.generate_pr_pdf_report(
        pr_title=pr.title,
        repo_name=repo_name,
        author=pr.author,
        quality_score=pr.quality_score,
        security_score=pr.security_score,
        arch_score=pr.architecture_score,
        overall_score=pr.overall_score,
        summary=pr.summary or "CodeGuard AI Automated Pull Request Review Report",
        comments=comments_list,
        output_filepath=filepath
    )

    report = Report(
        pull_request_id=pr.id,
        repository_id=pr.repository_id,
        title=f"Audit Report: PR #{pr.number} - {pr.title}",
        report_type="pr_review",
        pdf_filename=filename,
        summary=pr.summary,
        metrics_json={
            "quality_score": pr.quality_score,
            "security_score": pr.security_score,
            "architecture_score": pr.architecture_score,
            "overall_score": pr.overall_score
        }
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

@router.get("/download/{filename}")
def download_pdf_report(filename: str):
    filepath = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)
