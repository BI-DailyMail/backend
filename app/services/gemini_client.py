import json
from typing import Any

from google import genai

from app.core.config import settings
from app.schemas.email import SecurityFinding
from app.services.security_baseline import find_matching_baseline


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
        rag_context: str,
    ) -> dict[str, Any]:
        if self._client is None:
            return self._fallback_analysis(subject=subject, body=body)

        prompt = self._build_prompt(
            sender=sender,
            subject=subject,
            body=body,
            attachment_names=attachment_names,
            rag_context=rag_context,
        )
        try:
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
                                "enum": ["safe", "warn", "danger"],
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
        except Exception:
            return self._fallback_analysis(subject=subject, body=body)

    def _build_prompt(
        self,
        *,
        sender: str,
        subject: str,
        body: str,
        attachment_names: list[str],
        rag_context: str,
    ) -> str:
        attachments = ", ".join(attachment_names) if attachment_names else "없음"
        return f"""
너는 기업 이메일 보안을 담당하는 AI 이메일 센티널이다.
아래 메일이 스팸/피싱/정상 업무 메일인지 판단하라.
반드시 기본 위험 기준과 사용자 추가 키워드 컨텍스트를 먼저 참고하되, 사례가 부족하면 메일 내용 자체의 보안 위험을 분석하라.

[기본 기준 및 사용자 키워드 RAG 컨텍스트]
{rag_context}

[분석 대상 메일]
발신자: {sender}
제목: {subject}
첨부파일: {attachments}
본문:
{body}

[판단 기준]
- 기본 위험 기준 또는 사용자 추가 스팸 키워드와 유사하면 spam_probability를 높여라.
- 계정 정보 요구, 긴급 송금, 링크 클릭 압박, 매크로 첨부파일, 발신자 도메인 이상 여부를 근거로 삼아라.
- threat_level은 반드시 safe, warn, danger 중 하나만 사용하라.
- 출력은 지정된 JSON 스키마만 사용하라.
""".strip()

    def _fallback_analysis(self, *, subject: str, body: str) -> dict[str, Any]:
        text = f"{subject} {body}".lower()
        findings: list[SecurityFinding] = []

        for rule in find_matching_baseline(text):
            self._append_finding(
                findings,
                label=rule.label,
                reason=rule.reason,
                score=rule.score,
            )

        spam_probability = max([finding.score for finding in findings], default=0.1)
        threat_level = "danger" if spam_probability >= 0.8 else "warn" if findings else "safe"
        summary = " ".join(body.split())[:160]

        return {
            "summary": summary,
            "is_spam": spam_probability >= 0.7,
            "spam_probability": spam_probability,
            "threat_level": threat_level,
            "ai_reason": "GEMINI_API_KEY가 없어 로컬 휴리스틱으로 임시 분석했습니다.",
            "security_findings": [finding.model_dump() for finding in findings],
        }

    def _append_finding(
        self, findings: list[SecurityFinding], *, label: str, reason: str, score: float
    ) -> None:
        for index, finding in enumerate(findings):
            if finding.label == label:
                if score > finding.score:
                    findings[index] = SecurityFinding(label=label, reason=reason, score=score)
                return
        findings.append(SecurityFinding(label=label, reason=reason, score=score))
