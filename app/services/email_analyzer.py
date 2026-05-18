from sqlalchemy.orm import Session

from app.models.email import EmailMessage, ThreatLevel
from app.schemas.email import (
    DarkDataSignal,
    EmailAnalyzeRequest,
    EmailAnalyzeResponse,
    ScheduleCandidate,
    SecurityFinding,
)
from app.services.feedback_retriever import FeedbackRetriever
from app.services.gemini_client import GeminiClient


class EmailAnalyzer:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.feedback_retriever = FeedbackRetriever(db)
        self.gemini_client = GeminiClient()

    def analyze(self, payload: EmailAnalyzeRequest) -> EmailAnalyzeResponse:
        relevant_feedback = self.feedback_retriever.find_relevant_feedback(payload)
        feedback_context = self.feedback_retriever.format_for_prompt(relevant_feedback)
        ai_result = self.gemini_client.analyze_email(
            sender=str(payload.sender),
            subject=payload.subject,
            body=payload.body,
            attachment_names=payload.attachment_names,
            feedback_context=feedback_context,
        )

        summary = ai_result["summary"]
        schedule_candidates = self._extract_schedule_candidates(payload.body)
        dark_data_signals = self._discover_dark_data(payload)
        security_findings = [
            SecurityFinding(**finding) for finding in ai_result.get("security_findings", [])
        ]
        threat_level = self._normalize_threat_level(ai_result["threat_level"])

        email = EmailMessage(
            content=self._format_mail_content(payload),
            is_dark=ai_result["is_spam"],
            dark_reason=ai_result["ai_reason"],
            security_level=threat_level,
            spam_probability=ai_result["spam_probability"],
        )
        self.db.add(email)
        self.db.commit()
        self.db.refresh(email)

        return EmailAnalyzeResponse(
            email_id=email.id,
            summary=summary,
            schedule_candidates=schedule_candidates,
            dark_data_signals=dark_data_signals,
            security_findings=security_findings,
            threat_level=threat_level,
            is_spam=ai_result["is_spam"],
            spam_probability=ai_result["spam_probability"],
            ai_reason=ai_result["ai_reason"],
            rag_context_count=len(relevant_feedback),
        )

    def _format_mail_content(self, payload: EmailAnalyzeRequest) -> str:
        attachments = ", ".join(payload.attachment_names) if payload.attachment_names else "없음"
        return "\n".join(
            [
                f"발신자: {payload.sender}",
                f"제목: {payload.subject}",
                f"첨부파일: {attachments}",
                "본문:",
                payload.body,
            ]
        )

    def _extract_schedule_candidates(self, body: str) -> list[ScheduleCandidate]:
        schedule_keywords = ["회의", "미팅", "일정", "마감", "발표", "meeting", "deadline"]
        if not any(keyword.lower() in body.lower() for keyword in schedule_keywords):
            return []

        return [
            ScheduleCandidate(
                title="메일 본문에서 일정 후보가 감지되었습니다.",
                date_text="본문 확인 필요",
                confidence=0.55,
            )
        ]

    def _discover_dark_data(self, payload: EmailAnalyzeRequest) -> list[DarkDataSignal]:
        signals: list[DarkDataSignal] = []
        duplicated_names = {
            name for name in payload.attachment_names if payload.attachment_names.count(name) > 1
        }
        for name in sorted(duplicated_names):
            signals.append(
                DarkDataSignal(
                    label="duplicated_attachment",
                    detail=f"중복 첨부파일 이름 감지: {name}",
                    severity="low",
                )
            )

        hidden_file_extensions = (".zip", ".7z", ".rar", ".xlsm", ".docm")
        for name in payload.attachment_names:
            if name.lower().endswith(hidden_file_extensions):
                signals.append(
                    DarkDataSignal(
                        label="metadata_or_macro_risk",
                        detail=f"추가 메타데이터 또는 매크로 검사가 필요한 첨부파일: {name}",
                        severity="medium",
                    )
                )
        return signals

    def _normalize_threat_level(self, value: str) -> str:
        if value in {ThreatLevel.safe.value, ThreatLevel.suspicious.value, ThreatLevel.dangerous.value}:
            return value
        return ThreatLevel.suspicious.value
