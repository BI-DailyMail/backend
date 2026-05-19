from fastapi import APIRouter

from app.api.routes import emails, security

api_router = APIRouter()
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(security.router, prefix="/security", tags=["security"])
