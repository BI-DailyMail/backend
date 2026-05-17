from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.email import EmailFeedbackRequest, EmailFeedbackResponse
from app.services.feedback_service import FeedbackService

router = APIRouter()


@router.post("", response_model=EmailFeedbackResponse)
def create_feedback(
    payload: EmailFeedbackRequest, db: Session = Depends(get_db)
) -> EmailFeedbackResponse:
    service = FeedbackService(db)
    return service.create_feedback(payload)
