from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ThreatLevel(StrEnum):
    safe = "safe"
    suspicious = "suspicious"
    dangerous = "dangerous"


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sender: Mapped[str] = mapped_column(String(255), index=True)
    subject: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    spam_probability: Mapped[float] = mapped_column(Float, default=0)
    is_spam: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    threat_level: Mapped[ThreatLevel] = mapped_column(
        Enum(ThreatLevel), default=ThreatLevel.safe, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserSpamFeedback(Base):
    __tablename__ = "user_spam_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_messages.id"), nullable=True, index=True
    )
    sender: Mapped[str] = mapped_column(String(255), index=True)
    subject: Mapped[str] = mapped_column(String(500), default="")
    body_excerpt: Mapped[str] = mapped_column(Text)
    is_spam: Mapped[bool] = mapped_column(Boolean, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
