from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmailAnalyzeRequest(BaseModel):
    user_id: int = Field(gt=0)
    sender: EmailStr
    subject: str = Field(default="", max_length=500)
    body: str = Field(min_length=1)
    attachment_names: list[str] = Field(default_factory=list)


class ScheduleCandidate(BaseModel):
    title: str
    date_text: str
    confidence: float = Field(ge=0, le=1)


class DarkDataSignal(BaseModel):
    label: str
    detail: str
    severity: str


class SecurityFinding(BaseModel):
    label: str
    reason: str
    score: float = Field(ge=0, le=1)


class EmailAnalyzeResponse(BaseModel):
    email_id: int | None = None
    user_id: int
    summary: str
    schedule_candidates: list[ScheduleCandidate]
    dark_data_signals: list[DarkDataSignal]
    security_findings: list[SecurityFinding]
    threat_level: str
    is_spam: bool
    spam_probability: float = Field(ge=0, le=1)
    ai_reason: str
    rag_context_count: int


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str | None = None
    is_dark: bool | None = None
    dark_reason: str | None = None
    security_level: str | None = None
    spam_probability: float | None = None
    user_id: int | None = None
    created_at: datetime
