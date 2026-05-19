from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.email import EmailMessage, SpamKeyword, ThreatLevel, User
from app.schemas.email import EmailAnalyzeRequest
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
                    content="safe mail",
                    is_dark=False,
                    security_level=ThreatLevel.safe.value,
                    spam_probability=0.1,
                ),
                EmailMessage(
                    id=2,
                    user_id=1,
                    content="problem mail",
                    is_dark=True,
                    security_level=ThreatLevel.dangerous.value,
                    spam_probability=0.95,
                ),
                EmailMessage(
                    id=3,
                    user_id=1,
                    content="suspicious mail",
                    is_dark=False,
                    security_level=ThreatLevel.suspicious.value,
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
        assert [email["id"] for email in response.json()] == [3, 2, 1]

        response = client.get("/api/emails/problems")
        assert response.status_code == 200
        assert [email["id"] for email in response.json()] == [3, 2]
    finally:
        app.dependency_overrides.clear()


def test_analyze_email_saves_result(monkeypatch) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "")
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
            "/api/emails/analyze",
            json={
                "user_id": 1,
                "sender": "security@fake-bank.example",
                "subject": "긴급 계정 확인 요청",
                "body": "비밀번호와 인증번호를 즉시 입력하세요.",
                "attachment_names": [],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["email_id"] == 1
        assert body["user_id"] == 1
        assert body["is_spam"] is True

        response = client.get("/api/emails")
        assert response.status_code == 200
        assert response.json()[0]["id"] == body["email_id"]
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
