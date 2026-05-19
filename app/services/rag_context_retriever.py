from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email import SpamKeyword
from app.schemas.email import EmailAnalyzeRequest
from app.services.security_baseline import SecurityBaselineRule, find_matching_baseline
from app.services.text_normalizer import normalize_keyword


RagContextItem = SecurityBaselineRule | SpamKeyword


class RagContextRetriever:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_relevant_context(
        self, payload: EmailAnalyzeRequest, limit: int = 5
    ) -> list[RagContextItem]:
        text = " ".join([payload.subject, payload.body, " ".join(payload.attachment_names)])
        normalized_text = normalize_keyword(text)

        baseline_matches = find_matching_baseline(text)

        stmt = select(SpamKeyword).where(
            SpamKeyword.user_id == payload.user_id,
            SpamKeyword.is_active.is_(True),
        )
        keywords = []
        for keyword in self.db.scalars(stmt):
            normalized_keyword = keyword.keyword_normalized or normalize_keyword(keyword.keyword or "")
            if normalized_keyword and normalized_keyword in normalized_text:
                keywords.append(keyword)
        return [*baseline_matches, *keywords[:limit]]

    def format_for_prompt(self, context_items: list[RagContextItem]) -> str:
        if not context_items:
            return "기본 위험 기준 또는 사용자 추가 키워드와 일치하는 항목이 없습니다."

        lines = []
        for index, item in enumerate(context_items, start=1):
            if isinstance(item, SecurityBaselineRule):
                signals = ", ".join(item.signals)
                lines.append(
                    f"{index}. 기본 위험 기준={item.category}, 위험도={item.risk}, "
                    f"신호={signals}, 근거={item.reason}"
                )
            else:
                lines.append(f"{index}. 사용자 추가 스팸 키워드={item.keyword}")
        return "\n".join(lines)
