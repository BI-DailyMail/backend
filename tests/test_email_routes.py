from collections.abc import Generator
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models.email import EmailMessage, SpamKeyword, ThreatLevel, User
from app.schemas.email import EmailAnalyzeRequest
from app.services.email_analyzer import EmailAnalyzer
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

        response = client.get("/api/emails/problems")
        assert response.status_code == 200
        assert [email["id"] for email in response.json()] == [3, 2]
    finally:
        app.dependency_overrides.clear()


def test_feedback_route_is_removed() -> None:
    client = TestClient(app)

    response = client.post("/api/feedback", json={"keyword": "test", "is_active": True})

    assert response.status_code == 404


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
        attachment_names=[],
        received_at=datetime.now(timezone.utc) - timedelta(days=400),
    )

    signals = analyzer._discover_dark_data(payload)

    labels = {signal.label for signal in signals}
    assert "stale_mail_retention" in labels
    assert "resident_registration_number" in labels
    assert "card_number" in labels
    assert "bank_account_number" in labels
    assert "verification_code" in labels
    details = " ".join(signal.detail for signal in signals)
    assert "900101-1234567" not in details
    assert "4111 1111 1111 1111" not in details
    assert "123-456-789012" not in details
