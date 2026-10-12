from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any, Dict
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    username: str
    email: str
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    github_id: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Repository Schemas
class RepositoryBase(BaseModel):
    name: str
    full_name: str
    owner: str
    default_branch: str = "main"
    is_private: bool = False
    description: Optional[str] = None
    language: Optional[str] = None

class RepositoryCreate(RepositoryBase):
    pass

class RepositoryResponse(RepositoryBase):
    id: int
    webhook_active: bool
    webhook_id: Optional[str] = None
    quality_score: int
    security_score: int
    created_at: datetime
    open_prs_count: Optional[int] = 0
    class Config:
        from_attributes = True

# Review Comment Schemas
class ReviewCommentBase(BaseModel):
    file_path: str
    line_number: Optional[int] = None
    severity: str # Critical, High, Medium, Low
    category: str # Security, Code Quality, Performance, SOLID, Maintainability
    title: str
    description: str
    why_it_matters: str
    suggested_fix: Optional[str] = None
    example_code: Optional[str] = None

class ReviewCommentCreate(ReviewCommentBase):
    pull_request_id: int

class ReviewCommentResponse(ReviewCommentBase):
    id: int
    pull_request_id: int
    status: str
    github_comment_id: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

# Security Finding Schemas
class SecurityFindingBase(BaseModel):
    vulnerability_type: str
    cve_id: Optional[str] = None
    severity: str
    file_path: str
    line_number: Optional[int] = None
    raw_snippet: Optional[str] = None
    description: str
    recommendation: str
    risk_score: int = 50

class SecurityFindingResponse(SecurityFindingBase):
    id: int
    pull_request_id: Optional[int] = None
    repository_id: int
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

# Architecture Finding Schemas
class ArchitectureFindingBase(BaseModel):
    principle_violated: str
    severity: str
    component: str
    description: str
    recommendation: str
    design_pattern_suggested: Optional[str] = None

class ArchitectureFindingResponse(ArchitectureFindingBase):
    id: int
    pull_request_id: Optional[int] = None
    repository_id: int
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

# Pull Request Schemas
class PullRequestBase(BaseModel):
    number: int
    title: str
    body: Optional[str] = None
    author: str
    author_avatar: Optional[str] = None
    head_branch: str
    base_branch: str

class PullRequestCreate(PullRequestBase):
    repository_id: int
    diff_data: Optional[Dict[str, Any]] = None

class PullRequestResponse(PullRequestBase):
    id: int
    repository_id: int
    state: str
    status: str
    quality_score: int
    security_score: int
    architecture_score: int
    overall_score: int
    summary: Optional[str] = None
    diff_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    review_comments: List[ReviewCommentResponse] = []
    security_findings: List[SecurityFindingResponse] = []
    architecture_findings: List[ArchitectureFindingResponse] = []
    class Config:
        from_attributes = True

# Report Schemas
class ReportResponse(BaseModel):
    id: int
    pull_request_id: Optional[int] = None
    repository_id: int
    title: str
    report_type: str
    pdf_filename: Optional[str] = None
    summary: Optional[str] = None
    metrics_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    class Config:
        from_attributes = True

# Dashboard / Analytics Schemas
class DashboardMetrics(BaseModel):
    total_repositories: int
    total_pull_requests: int
    total_issues_found: int
    critical_security_alerts: int
    avg_quality_score: float
    avg_security_score: float
    avg_architecture_score: float
    technical_debt_hours: float
    recent_prs: List[PullRequestResponse]
    security_summary: Dict[str, int]
