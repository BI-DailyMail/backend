from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.email import UserSpamFeedback
from app.schemas.email import EmailAnalyzeRequest


class FeedbackRetriever:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_relevant_feedback(
        self, payload: EmailAnalyzeRequest, limit: int = 5
    ) -> list[UserSpamFeedback]:
        sender_domain = payload.sender.split("@")[-1]
        subject_terms = [term for term in payload.subject.split() if len(term) >= 2][:3]

        filters = [UserSpamFeedback.sender.ilike(f"%@{sender_domain}")]
        filters.extend(UserSpamFeedback.subject.ilike(f"%{term}%") for term in subject_terms)

        stmt = (
            select(UserSpamFeedback)
            .where(or_(*filters))
            .order_by(UserSpamFeedback.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def format_for_prompt(self, feedback_items: list[UserSpamFeedback]) -> str:
        if not feedback_items:
            return "사용자 피드백 사례가 아직 없습니다."

        lines = []
        for index, item in enumerate(feedback_items, start=1):
            label = "스팸" if item.is_spam else "정상"
            note = f" / 메모: {item.note}" if item.note else ""
            lines.append(
                f"{index}. 판정={label}, 발신자={item.sender}, 제목={item.subject}, "
                f"본문 일부={item.body_excerpt[:300]}{note}"
            )
        return "\n".join(lines)

