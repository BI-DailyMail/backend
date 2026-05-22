from collections.abc import Generator
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models.email import EmailMessage, SpamKeyword, ThreatLevel, User
from app.schemas.email import EmailAnalyzeRequest
from app.services.email_analyzer import EmailAnalyzer
from app.services.gemini_client import GeminiClient
from app.services.rag_context_retriever import RagContextRetriever


def test_list_emails_and_problem_emails() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        db.add_all(
            [
                User(id=1, email="user1@example.com", name="User 1"),
                EmailMessage(
                    id=1,
                    user_id=1,
                    sender="team@example.com",
                    subject="일반 메일",
                    body="safe mail body",
                    is_dark=False,
                    security_level=ThreatLevel.safe.value,
                    spam_probability=0.1,
                ),
                EmailMessage(
                    id=2,
                    user_id=1,
                    sender="attacker@example.com",
                    subject="문제 메일",
                    body="problem mail body",
                    is_dark=True,
                    security_level=ThreatLevel.danger.value,
                    spam_probability=0.95,
                ),
                EmailMessage(
                    id=3,
                    user_id=1,
                    sender="notice@example.com",
                    subject="주의 메일",
                    body="warn mail body",
                    received_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
                    is_dark=False,
                    security_level=ThreatLevel.warn.value,
                    spam_probability=0.6,
                ),
            ]
        )
        db.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)

        response = client.get("/api/emails")
        assert response.status_code == 200
        emails = response.json()
        assert [email["id"] for email in emails] == [3, 2, 1]
        assert emails[0]["sender"] == "notice@example.com"
        assert emails[0]["subject"] == "주의 메일"
        assert emails[0]["body"] == "warn mail body"
        assert emails[0]["received_at"] is not None

        response = client.get("/api/emails", params={"limit": 1, "offset": 1})
        assert response.status_code == 200
        assert [email["id"] for email in response.json()] == [2]

        response = client.get("/api/emails/problems")
        assert response.status_code == 200
        assert [email["id"] for email in response.json()] == [3, 2]

        response = client.get("/api/emails/problems", params={"limit": 1})
        assert response.status_code == 200
        assert [email["id"] for email in response.json()] == [3]
    finally:
        app.dependency_overrides.clear()


def test_feedback_route_is_removed() -> None:
    client = TestClient(app)

    response = client.post("/api/feedback", json={"keyword": "test", "is_active": True})

    assert response.status_code == 404


def test_batch_analyze_accepts_email_list_and_saves_each_email(monkeypatch) -> None:
    def fake_analyze_email(
        self,
        *,
        sender: str,
        subject: str,
        body: str,
        attachment_names: list[str],
        rag_context: str,
    ) -> dict:
        return {
            "summary": body,
            "is_spam": "비밀번호" in body,
            "spam_probability": 0.9 if "비밀번호" in body else 0.1,
            "threat_level": "danger" if "비밀번호" in body else "safe",
            "ai_reason": "테스트 분석 결과입니다.",
            "security_findings": [],
        }

    monkeypatch.setattr(GeminiClient, "analyze_email", fake_analyze_email)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        db.add(User(id=1, email="user1@example.com", name="User 1"))
        db.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        response = client.post(
            "/api/emails/analyze/batch",
            json=[
                {
                    "user_id": 1,
                    "sender": "safe@example.com",
                    "subject": "안내",
                    "body": "정상 안내 메일입니다.",
                },
                {
                    "user_id": 1,
                    "sender": "risk@example.com",
                    "subject": "계정 확인",
                    "body": "비밀번호를 즉시 입력해주세요.",
                    "received_at": "2024-01-10T09:30:00Z",
                },
            ],
        )

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        assert [result["threat_level"] for result in results] == ["safe", "danger"]

        with TestingSessionLocal() as db:
            saved = list(db.scalars(select(EmailMessage).order_by(EmailMessage.id)))
        assert len(saved) == 2
        assert saved[0].subject == "안내"
        assert saved[1].received_at is not None
    finally:
        app.dependency_overrides.clear()


def test_batch_analyze_rolls_back_when_analysis_fails(monkeypatch) -> None:
    def fake_analyze_email(
        self,
        *,
        sender: str,
        subject: str,
        body: str,
        attachment_names: list[str],
        rag_context: str,
    ) -> dict:
        if "실패" in body:
            raise RuntimeError("analysis failed")
        return {
            "summary": body,
            "is_spam": False,
            "spam_probability": 0.1,
            "threat_level": "safe",
            "ai_reason": "테스트 분석 결과입니다.",
            "security_findings": [],
        }

    monkeypatch.setattr(GeminiClient, "analyze_email", fake_analyze_email)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        db.add(User(id=1, email="user1@example.com", name="User 1"))
        db.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/emails/analyze/batch",
            json=[
                {
                    "user_id": 1,
                    "sender": "safe@example.com",
                    "subject": "안내",
                    "body": "정상 안내 메일입니다.",
                },
                {
                    "user_id": 1,
                    "sender": "fail@example.com",
                    "subject": "실패",
                    "body": "분석 실패 케이스입니다.",
                },
            ],
        )

        assert response.status_code == 500
        with TestingSessionLocal() as db:
            saved = list(db.scalars(select(EmailMessage)))
        assert saved == []
    finally:
        app.dependency_overrides.clear()


def test_body_only_analyze_returns_result_without_saving_email(monkeypatch) -> None:
    def fake_analyze_email(
        self,
        *,
        sender: str,
        subject: str,
        body: str,
        attachment_names: list[str],
        rag_context: str,
    ) -> dict:
        return {
            "summary": body,
            "is_spam": True,
            "spam_probability": 0.88,
            "threat_level": "danger",
            "ai_reason": "본문만 분석했습니다.",
            "security_findings": [
                {
                    "label": "credential_request",
                    "reason": "비밀번호 입력 요구",
                    "score": 0.88,
                }
            ],
        }

    monkeypatch.setattr(GeminiClient, "analyze_email", fake_analyze_email)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        response = client.post(
            "/api/emails/analyze/body",
            json={"body": "비밀번호와 인증번호 123456을 즉시 입력하세요."},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["threat_level"] == "danger"
        assert result["is_spam"] is True
        assert result["rag_context_count"] >= 1
        assert any(
            signal["label"] == "verification_code" for signal in result["dark_data_signals"]
        )

        with TestingSessionLocal() as db:
            saved = list(db.scalars(select(EmailMessage)))
        assert saved == []
    finally:
        app.dependency_overrides.clear()


def test_rag_context_uses_only_current_user_keywords() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        db.add_all(
            [
                User(id=1, email="user1@example.com", name="User 1"),
                User(id=2, email="user2@example.com", name="User 2"),
                SpamKeyword(
                    id=1,
                    user_id=1,
                    keyword="사내 포털",
                    keyword_normalized="사내포털",
                    is_active=True,
                ),
                SpamKeyword(
                    id=2,
                    user_id=2,
                    keyword="사내 포털",
                    keyword_normalized="사내포털",
                    is_active=True,
                ),
                SpamKeyword(
                    id=3,
                    user_id=1,
                    keyword="비활성 키워드",
                    keyword_normalized="비활성키워드",
                    is_active=False,
                ),
            ]
        )
        db.commit()

        retriever = RagContextRetriever(db)
        payload = EmailAnalyzeRequest(
            user_id=2,
            sender="sender@example.com",
            subject="공지",
            body="사내 포털에서 확인해주세요. 비활성 키워드도 본문에 있습니다.",
            attachment_names=[],
        )

        context = retriever.find_relevant_context(payload)

    keywords = [item.keyword for item in context if isinstance(item, SpamKeyword)]
    assert keywords == ["사내 포털"]


def test_rag_context_matches_keywords_ignoring_spaces() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        db.add_all(
            [
                User(id=1, email="user1@example.com", name="User 1"),
                SpamKeyword(
                    id=1,
                    user_id=1,
                    keyword="개인 정보",
                    keyword_normalized=None,
                    is_active=True,
                ),
            ]
        )
        db.commit()

        retriever = RagContextRetriever(db)
        payload = EmailAnalyzeRequest(
            user_id=1,
            sender="sender@example.com",
            subject="확인 요청",
            body="개인정보를 바로 입력해주세요.",
            attachment_names=[],
        )

        context = retriever.find_relevant_context(payload)

    keywords = [item.keyword for item in context if isinstance(item, SpamKeyword)]
    assert keywords == ["개인 정보"]


def test_dark_data_detects_stale_mail_and_sensitive_patterns_without_leaking_values() -> None:
    analyzer = EmailAnalyzer.__new__(EmailAnalyzer)
    payload = EmailAnalyzeRequest(
        user_id=1,
        sender="sender@example.com",
        subject="오래된 문서 확인",
        body=(
            "주민등록번호 900101-1234567, 카드번호 4111 1111 1111 1111, "
            "계좌 123-456-789012, 인증번호 123456을 포함합니다."
        ),
        attachment_names=["report.pdf", "report.pdf", "report.pdf", "archive.zip"],
        received_at=datetime.now(timezone.utc) - timedelta(days=400),
    )

    signals = analyzer._discover_dark_data(payload)

    labels = {signal.label for signal in signals}
    duplicate_signals = [
        signal for signal in signals if signal.label == "duplicated_attachment"
    ]
    assert "stale_mail_retention" in labels
    assert "resident_registration_number" in labels
    assert "card_number" in labels
    assert "bank_account_number" in labels
    assert "verification_code" in labels
    assert len(duplicate_signals) == 1
    assert "report.pdf" in duplicate_signals[0].detail
    details = " ".join(signal.detail for signal in signals)
    assert "900101-1234567" not in details
    assert "4111 1111 1111 1111" not in details
    assert "123-456-789012" not in details
