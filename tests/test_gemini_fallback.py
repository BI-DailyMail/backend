from app.services.gemini_client import GeminiClient
from app.core.config import settings


def test_gemini_client_falls_back_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "")
    client = GeminiClient()

    result = client.analyze_email(
        sender="security@example.com",
        subject="계정 확인",
        body="비밀번호와 인증번호를 즉시 입력하세요.",
        attachment_names=[],
        feedback_context="기본 위험 기준 또는 사용자 추가 키워드와 일치하는 항목이 없습니다.",
    )

    assert result["is_spam"] is True
    assert result["threat_level"] == "dangerous"
