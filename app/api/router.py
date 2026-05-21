from fastapi import APIRouter

from app.api.routes import emails, feedback, keywords, security

api_router = APIRouter()
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(security.router, prefix="/security", tags=["security"])
api_router.include_router(keywords.router, prefix="/keywords", tags=["keywords"])
