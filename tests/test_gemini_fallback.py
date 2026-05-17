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
        feedback_context="사용자 피드백 사례가 아직 없습니다.",
    )

    assert result["is_spam"] is True
    assert result["threat_level"] == "dangerous"
