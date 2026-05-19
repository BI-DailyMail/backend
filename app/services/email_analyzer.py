import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.email import EmailMessage, ThreatLevel
from app.schemas.email import (
    DarkDataSignal,
    EmailAnalyzeRequest,
    EmailAnalyzeResponse,
    ScheduleCandidate,
    SecurityFinding,
)
from app.services.gemini_client import GeminiClient
from app.services.rag_context_retriever import RagContextRetriever


STALE_MAIL_DAYS = 365


class EmailAnalyzer:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.rag_context_retriever = RagContextRetriever(db)
        self.gemini_client = GeminiClient()

    def analyze(self, payload: EmailAnalyzeRequest) -> EmailAnalyzeResponse:
        relevant_context = self.rag_context_retriever.find_relevant_context(payload)
        rag_context = self.rag_context_retriever.format_for_prompt(relevant_context)
        ai_result = self.gemini_client.analyze_email(
            sender=str(payload.sender),
            subject=payload.subject,
            body=payload.body,
            attachment_names=payload.attachment_names,
            rag_context=rag_context,
        )

        summary = ai_result["summary"]
        schedule_candidates = self._extract_schedule_candidates(payload.body)
        dark_data_signals = self._discover_dark_data(payload)
        security_findings = [
            SecurityFinding(**finding) for finding in ai_result.get("security_findings", [])
        ]
        threat_level = self._normalize_threat_level(ai_result["threat_level"])

        email = EmailMessage(
            sender=str(payload.sender),
            subject=payload.subject,
            body=payload.body,
            received_at=payload.received_at,
            is_dark=ai_result["is_spam"],
            dark_reason=ai_result["ai_reason"],
            security_level=threat_level,
            spam_probability=ai_result["spam_probability"],
            user_id=payload.user_id,
        )
        self.db.add(email)
        self.db.commit()
        self.db.refresh(email)

        return EmailAnalyzeResponse(
            email_id=email.id,
            user_id=payload.user_id,
            summary=summary,
            schedule_candidates=schedule_candidates,
            dark_data_signals=dark_data_signals,
            security_findings=security_findings,
            threat_level=threat_level,
            is_spam=ai_result["is_spam"],
            spam_probability=ai_result["spam_probability"],
            ai_reason=ai_result["ai_reason"],
            rag_context_count=len(relevant_context),
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
        signals.extend(self._discover_stale_mail(payload))
        signals.extend(self._discover_sensitive_data(payload))

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

    def _discover_stale_mail(self, payload: EmailAnalyzeRequest) -> list[DarkDataSignal]:
        if payload.received_at is None:
            return []

        received_at = self._as_aware_datetime(payload.received_at)
        age_days = (datetime.now(timezone.utc) - received_at).days
        if age_days < STALE_MAIL_DAYS:
            return []

        severity = "high" if age_days >= STALE_MAIL_DAYS * 3 else "medium"
        return [
            DarkDataSignal(
                label="stale_mail_retention",
                detail=f"{age_days}일 전에 수신된 장기 보관 메일입니다.",
                severity=severity,
            )
        ]

    def _discover_sensitive_data(self, payload: EmailAnalyzeRequest) -> list[DarkDataSignal]:
        text = f"{payload.subject}\n{payload.body}"
        signals: list[DarkDataSignal] = []

        if re.search(r"(?<!\d)\d{6}[- ]?[1-8]\d{6}(?!\d)", text):
            signals.append(
                DarkDataSignal(
                    label="resident_registration_number",
                    detail="주민등록번호 형식의 민감정보 패턴이 감지되었습니다.",
                    severity="high",
                )
            )

        if self._contains_card_number(text):
            signals.append(
                DarkDataSignal(
                    label="card_number",
                    detail="카드번호 형식의 민감정보 패턴이 감지되었습니다.",
                    severity="high",
                )
            )

        if re.search(
            r"(계좌|입금|송금|account|bank)[^\n]{0,40}(?<!\d)\d{2,6}[- ]?\d{2,6}[- ]?\d{2,8}(?!\d)",
            text,
            re.IGNORECASE,
        ):
            signals.append(
                DarkDataSignal(
                    label="bank_account_number",
                    detail="계좌번호로 보이는 금융정보 패턴이 감지되었습니다.",
                    severity="medium",
                )
            )

        if re.search(
            r"(인증번호|보안코드|otp|2fa|mfa|verification code|security code)[^\n]{0,40}(?<!\d)\d{4,8}(?!\d)",
            text,
            re.IGNORECASE,
        ):
            signals.append(
                DarkDataSignal(
                    label="verification_code",
                    detail="인증번호 또는 보안코드 형식의 민감정보 패턴이 감지되었습니다.",
                    severity="high",
                )
            )

        return signals

    def _contains_card_number(self, text: str) -> bool:
        for match in re.finditer(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text):
            digits = re.sub(r"\D", "", match.group())
            if 13 <= len(digits) <= 19 and self._passes_luhn(digits):
                return True
        return False

    def _passes_luhn(self, digits: str) -> bool:
        checksum = 0
        reverse_digits = digits[::-1]
        for index, char in enumerate(reverse_digits):
            value = int(char)
            if index % 2 == 1:
                value *= 2
                if value > 9:
                    value -= 9
            checksum += value
        return checksum % 10 == 0

    def _as_aware_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _normalize_threat_level(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {ThreatLevel.safe.value, "low", "normal"}:
            return ThreatLevel.safe.value
        if normalized in {ThreatLevel.warn.value, "warning", "suspicious", "medium"}:
            return ThreatLevel.warn.value
        if normalized in {ThreatLevel.danger.value, "dangerous", "high", "critical"}:
            return ThreatLevel.danger.value
        return ThreatLevel.warn.value
