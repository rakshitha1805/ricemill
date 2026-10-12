from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.review import ReviewComment
from app.schemas.schemas import ReviewCommentResponse

router = APIRouter(prefix="/reviews", tags=["Review Comments"])

@router.get("/pr/{pr_id}", response_model=List[ReviewCommentResponse])
def get_pr_review_comments(pr_id: int, db: Session = Depends(get_db)):
    return db.query(ReviewComment).filter(ReviewComment.pull_request_id == pr_id).all()

@router.patch("/{comment_id}/resolve", response_model=ReviewCommentResponse)
def resolve_review_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(ReviewComment).filter(ReviewComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.status = "resolved"
    db.commit()
    db.refresh(comment)
    return comment
