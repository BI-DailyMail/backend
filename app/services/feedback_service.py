from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.email import SpamKeyword
from app.schemas.email import EmailFeedbackRequest, EmailFeedbackResponse


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_feedback(self, payload: EmailFeedbackRequest) -> EmailFeedbackResponse:
        existing = self.db.scalar(
            select(SpamKeyword).where(func.lower(SpamKeyword.keyword) == payload.keyword.lower())
        )

        if existing:
            existing.is_active = payload.is_active
            self.db.commit()
            self.db.refresh(existing)
            return EmailFeedbackResponse(
                id=existing.id,
                keyword=existing.keyword or payload.keyword,
                is_active=bool(existing.is_active),
                created=False,
            )

        feedback = SpamKeyword(keyword=payload.keyword, is_active=payload.is_active)
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)

        return EmailFeedbackResponse(
            id=feedback.id,
            keyword=feedback.keyword or payload.keyword,
            is_active=bool(feedback.is_active),
            created=True,
        )
