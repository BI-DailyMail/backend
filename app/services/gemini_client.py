import json
from typing import Any

from google import genai

from app.core.config import settings
from app.schemas.email import SecurityFinding


class GeminiEmailAnalysis(dict):
    summary: str
    is_spam: bool
    spam_probability: float
    threat_level: str
    ai_reason: str
    security_findings: list[dict[str, Any]]


class GeminiClient:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None

    def analyze_email(
        self,
        *,
        sender: str,
        subject: str,
        body: str,
        attachment_names: list[str],
        feedback_context: str,
    ) -> dict[str, Any]:
        if self._client is None:
            return self._fallback_analysis(subject=subject, body=body)

        prompt = self._build_prompt(
            sender=sender,
            subject=subject,
            body=body,
            attachment_names=attachment_names,
            feedback_context=feedback_context,
        )
        response = self._client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "OBJECT",
                    "properties": {
                        "summary": {"type": "STRING"},
                        "is_spam": {"type": "BOOLEAN"},
                        "spam_probability": {"type": "NUMBER"},
                        "threat_level": {
                            "type": "STRING",
                            "enum": ["safe", "suspicious", "dangerous"],
                        },
                        "ai_reason": {"type": "STRING"},
                        "security_findings": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "label": {"type": "STRING"},
                                    "reason": {"type": "STRING"},
                                    "score": {"type": "NUMBER"},
                                },
                                "required": ["label", "reason", "score"],
                            },
                        },
                    },
                    "required": [
                        "summary",
                        "is_spam",
                        "spam_probability",
                        "threat_level",
                        "ai_reason",
                        "security_findings",
                    ],
                },
            },
        )
        return json.loads(response.text)

    def _build_prompt(
        self,
        *,
        sender: str,
        subject: str,
        body: str,
        attachment_names: list[str],
        feedback_context: str,
    ) -> str:
        attachments = ", ".join(attachment_names) if attachment_names else "없음"
        return f"""
너는 기업 이메일 보안을 담당하는 AI 이메일 센티널이다.
아래 메일이 스팸/피싱/정상 업무 메일인지 판단하라.
반드시 사용자 피드백 사례를 우선 참고하되, 사례가 부족하면 메일 내용 자체의 보안 위험을 분석하라.

[사용자 피드백 RAG 컨텍스트]
{feedback_context}

[분석 대상 메일]
발신자: {sender}
제목: {subject}
첨부파일: {attachments}
본문:
{body}

[판단 기준]
- 사용자가 과거에 스팸이라고 지정한 패턴과 유사하면 spam_probability를 높여라.
- 사용자가 과거에 정상이라고 지정한 패턴과 유사하면 spam_probability를 낮춰라.
- 계정 정보 요구, 긴급 송금, 링크 클릭 압박, 매크로 첨부파일, 발신자 도메인 이상 여부를 근거로 삼아라.
- 출력은 지정된 JSON 스키마만 사용하라.
""".strip()

    def _fallback_analysis(self, *, subject: str, body: str) -> dict[str, Any]:
        text = f"{subject} {body}".lower()
        findings: list[SecurityFinding] = []

        if any(keyword in text for keyword in ["password", "비밀번호", "인증번호", "계정 확인"]):
            findings.append(
                SecurityFinding(
                    label="credential_request",
                    reason="계정 정보 또는 인증 정보를 요구하는 표현이 감지되었습니다.",
                    score=0.82,
                )
            )

        if any(keyword in text for keyword in ["긴급", "즉시", "urgent", "immediately"]):
            findings.append(
                SecurityFinding(
                    label="urgency_pressure",
                    reason="사용자에게 빠른 행동을 압박하는 표현이 감지되었습니다.",
                    score=0.64,
                )
            )

        spam_probability = max([finding.score for finding in findings], default=0.1)
        threat_level = "dangerous" if spam_probability >= 0.8 else "suspicious" if findings else "safe"
        summary = " ".join(body.split())[:160]

        return {
            "summary": summary,
            "is_spam": spam_probability >= 0.7,
            "spam_probability": spam_probability,
            "threat_level": threat_level,
            "ai_reason": "GEMINI_API_KEY가 없어 로컬 휴리스틱으로 임시 분석했습니다.",
            "security_findings": [finding.model_dump() for finding in findings],
        }

