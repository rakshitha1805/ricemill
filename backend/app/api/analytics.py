from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.repository import Repository
from app.models.pull_request import PullRequest
from app.models.security import SecurityFinding
from app.models.review import ReviewComment
from app.schemas.schemas import DashboardMetrics, PullRequestResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/dashboard", response_model=DashboardMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    total_repos = db.query(Repository).count()
    total_prs = db.query(PullRequest).count()
    total_issues = db.query(ReviewComment).count()
    critical_security = db.query(SecurityFinding).filter(SecurityFinding.severity == "Critical").count()

    avg_qual = db.query(func.avg(PullRequest.quality_score)).scalar() or 85.0
    avg_sec = db.query(func.avg(PullRequest.security_score)).scalar() or 90.0
    avg_arch = db.query(func.avg(PullRequest.architecture_score)).scalar() or 82.0

    # Tech debt calculation heuristic: 4 hrs per Critical, 2 hrs per High, 1 hr per Medium, 0.5 hr per Low
    high_count = db.query(ReviewComment).filter(ReviewComment.severity == "High").count()
    med_count = db.query(ReviewComment).filter(ReviewComment.severity == "Medium").count()
    low_count = db.query(ReviewComment).filter(ReviewComment.severity == "Low").count()

    tech_debt_hours = (critical_security * 4.0) + (high_count * 2.5) + (med_count * 1.0) + (low_count * 0.5)

    recent_prs_db = db.query(PullRequest).order_by(PullRequest.created_at.desc()).limit(5).all()
    recent_prs = [PullRequestResponse.from_orm(pr) for pr in recent_prs_db]

    sec_summary = {
        "Critical": critical_security,
        "High": db.query(SecurityFinding).filter(SecurityFinding.severity == "High").count(),
        "Medium": db.query(SecurityFinding).filter(SecurityFinding.severity == "Medium").count(),
        "Low": db.query(SecurityFinding).filter(SecurityFinding.severity == "Low").count()
    }

    return DashboardMetrics(
        total_repositories=total_repos,
        total_pull_requests=total_prs,
        total_issues_found=total_issues,
        critical_security_alerts=critical_security,
        avg_quality_score=round(float(avg_qual), 1),
        avg_security_score=round(float(avg_sec), 1),
        avg_architecture_score=round(float(avg_arch), 1),
        technical_debt_hours=round(float(tech_debt_hours), 1),
        recent_prs=recent_prs,
        security_summary=sec_summary
    )
