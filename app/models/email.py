from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ThreatLevel(StrEnum):
    safe = "safe"
    suspicious = "suspicious"
    dangerous = "dangerous"


class EmailMessage(Base):
    __tablename__ = "tb_mail"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_dark: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dark_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    security_level: Mapped[str | None] = mapped_column(String, nullable=True)
    spam_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SpamKeyword(Base):
    __tablename__ = "tb_spam_keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    keyword: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "tb_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
