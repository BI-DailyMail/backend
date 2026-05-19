from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

SqliteAutoIncrementBigInteger = BigInteger().with_variant(Integer, "sqlite")


class ThreatLevel(StrEnum):
    safe = "safe"
    suspicious = "suspicious"
    dangerous = "dangerous"


class EmailMessage(Base):
    __tablename__ = "tb_mail"

    id: Mapped[int] = mapped_column(SqliteAutoIncrementBigInteger, primary_key=True, index=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_dark: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dark_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    security_level: Mapped[str | None] = mapped_column(String, nullable=True)
    spam_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tb_user.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SpamKeyword(Base):
    __tablename__ = "tb_spam_keywords"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "keyword_normalized", name="uq_spam_keywords_user_keyword_normalized"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tb_user.id"), nullable=False, index=True
    )
    keyword: Mapped[str | None] = mapped_column(String, nullable=True)
    keyword_normalized: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "tb_user"

    id: Mapped[int] = mapped_column(SqliteAutoIncrementBigInteger, primary_key=True, index=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
