from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

SecurityLevel = Literal["safe", "warn", "danger"]


class SecurityIssue(BaseModel):
    type: SecurityLevel
    title: str
    desc: str


class SecurityInfo(BaseModel):
    level: SecurityLevel
    issues: list[SecurityIssue]


class DarkDataItem(BaseModel):
    label: str
    reason: str


class AnalysisResult(BaseModel):
    subject: str
    summary: str
    security: SecurityInfo
    darkdata: list[DarkDataItem]


class MailRecord(BaseModel):
    id: int
    subject: Optional[str]
    content: str
    is_dark: bool
    dark_reason: Optional[str]
    security_level: SecurityLevel
    user_id: Optional[int]
    created_at: datetime


class SpamKeyword(BaseModel):
    id: int
    keyword: str
    is_active: bool
    created_at: datetime


# 요청(Request) 스키마
class AnalyzeRequest(BaseModel):
    content: str


class MailSaveRequest(BaseModel):
    content: str
    subject: Optional[str] = None
    is_dark: bool
    dark_reason: Optional[str] = None
    security_level: SecurityLevel


class KeywordCreateRequest(BaseModel):
    keyword: str


class KeywordToggleRequest(BaseModel):
    is_active: bool
