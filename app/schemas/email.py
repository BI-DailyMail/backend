from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailAnalyzeRequest(BaseModel):
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
    summary: str
    schedule_candidates: list[ScheduleCandidate]
    dark_data_signals: list[DarkDataSignal]
    security_findings: list[SecurityFinding]
    threat_level: str
    is_spam: bool
    spam_probability: float = Field(ge=0, le=1)
    ai_reason: str
    rag_context_count: int


class EmailFeedbackRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=255)
    is_active: bool = True

    @field_validator("keyword")
    @classmethod
    def normalize_keyword(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("keyword must not be blank")
        return normalized


class EmailFeedbackResponse(BaseModel):
    id: int
    keyword: str
    is_active: bool
    created: bool
