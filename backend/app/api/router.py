from fastapi import APIRouter
from app.api import auth, webhooks, repositories, pull_requests, reviews, security, architecture, reports, analytics, chat, websocket

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(webhooks.router)
api_router.include_router(repositories.router)
api_router.include_router(pull_requests.router)
api_router.include_router(reviews.router)
api_router.include_router(security.router)
api_router.include_router(architecture.router)
api_router.include_router(reports.router)
api_router.include_router(analytics.router)
api_router.include_router(chat.router)
api_router.include_router(websocket.router)
