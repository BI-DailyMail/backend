from sqlalchemy.orm import Session

from app.models.email import UserSpamFeedback
from app.schemas.email import EmailFeedbackRequest, EmailFeedbackResponse


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_feedback(self, payload: EmailFeedbackRequest) -> EmailFeedbackResponse:
        feedback = UserSpamFeedback(
            email_message_id=payload.email_message_id,
            sender=str(payload.sender),
            subject=payload.subject,
            body_excerpt=payload.body_excerpt,
            is_spam=payload.is_spam,
            note=payload.note,
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)

        return EmailFeedbackResponse(id=feedback.id, is_spam=feedback.is_spam)
