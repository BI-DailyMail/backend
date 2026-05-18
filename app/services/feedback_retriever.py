from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email import SpamKeyword
from app.schemas.email import EmailAnalyzeRequest
from app.services.security_baseline import SecurityBaselineRule, find_matching_baseline


RagContextItem = SecurityBaselineRule | SpamKeyword


class FeedbackRetriever:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_relevant_feedback(
        self, payload: EmailAnalyzeRequest, limit: int = 5
    ) -> list[RagContextItem]:
        text = " ".join(
            [payload.subject, payload.body, " ".join(payload.attachment_names)]
        ).lower()

        baseline_matches = find_matching_baseline(text)

        stmt = select(SpamKeyword).where(SpamKeyword.is_active.is_(True))
        keywords = [
            keyword
            for keyword in self.db.scalars(stmt)
            if keyword.keyword and keyword.keyword.lower() in text
        ]
        return [*baseline_matches, *keywords[:limit]]

    def format_for_prompt(self, feedback_items: list[RagContextItem]) -> str:
        if not feedback_items:
            return "기본 위험 기준 또는 사용자 추가 키워드와 일치하는 항목이 없습니다."

        lines = []
        for index, item in enumerate(feedback_items, start=1):
            if isinstance(item, SecurityBaselineRule):
                signals = ", ".join(item.signals)
                lines.append(
                    f"{index}. 기본 위험 기준={item.category}, 위험도={item.risk}, "
                    f"신호={signals}, 근거={item.reason}"
                )
            else:
                lines.append(f"{index}. 사용자 추가 스팸 키워드={item.keyword}")
        return "\n".join(lines)
