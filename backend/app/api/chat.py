from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.pull_request import PullRequest
from app.models.review import ReviewComment
from app.services.ai_engine import AICodeAnalysisEngine

router = APIRouter(prefix="/chat", tags=["AI Chat Assistant"])

class ChatRequest(BaseModel):
    pr_id: int
    question: str

class ChatResponse(BaseModel):
    answer: str

@router.post("", response_model=ChatResponse)
async def ask_pr_chat_assistant(payload: ChatRequest, db: Session = Depends(get_db)):
    pr = db.query(PullRequest).filter(PullRequest.id == payload.pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pull Request not found")

    comments = db.query(ReviewComment).filter(ReviewComment.pull_request_id == payload.pr_id).all()
    comments_list = [{"title": c.title, "severity": c.severity, "description": c.description} for c in comments]

    engine = AICodeAnalysisEngine()
    answer = await engine.answer_developer_chat(payload.question, pr.title, comments_list)
    return ChatResponse(answer=answer)
