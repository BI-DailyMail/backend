from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.email import EmailMessage, ThreatLevel
from app.schemas.email import (
    EmailAnalyzeRequest,
    EmailAnalyzeResponse,
    EmailBodyAnalyzeRequest,
    EmailBodyAnalyzeResponse,
    EmailResponse,
)
from app.services.email_analyzer import EmailAnalyzer

router = APIRouter()
EmailBatchPayload = Annotated[list[EmailAnalyzeRequest], Body(min_length=1, max_length=50)]
PaginationLimit = Annotated[int, Query(ge=1, le=100)]
PaginationOffset = Annotated[int, Query(ge=0)]


@router.get("", response_model=list[EmailResponse])
def list_emails(
    limit: PaginationLimit = 50,
    offset: PaginationOffset = 0,
    db: Session = Depends(get_db),
) -> list[EmailMessage]:
    return list(
        db.scalars(
            select(EmailMessage).order_by(EmailMessage.created_at.desc(), EmailMessage.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.get("/problems", response_model=list[EmailResponse])
def list_problem_emails(
    limit: PaginationLimit = 50,
    offset: PaginationOffset = 0,
    db: Session = Depends(get_db),
) -> list[EmailMessage]:
    return list(
        db.scalars(
            select(EmailMessage)
            .where(
                or_(
                    EmailMessage.is_dark.is_(True),
                    EmailMessage.security_level.in_(
                        [ThreatLevel.warn.value, ThreatLevel.danger.value]
                    ),
                )
            )
            .order_by(EmailMessage.created_at.desc(), EmailMessage.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.post("/analyze", response_model=EmailAnalyzeResponse)
def analyze_email(payload: EmailAnalyzeRequest, db: Session = Depends(get_db)) -> EmailAnalyzeResponse:
    analyzer = EmailAnalyzer(db)
    return analyzer.analyze(payload)


@router.post("/analyze/batch", response_model=list[EmailAnalyzeResponse])
def analyze_email_batch(
    payload: EmailBatchPayload, db: Session = Depends(get_db)
) -> list[EmailAnalyzeResponse]:
    analyzer = EmailAnalyzer(db)
    return analyzer.analyze_many(payload)


@router.post("/analyze/body", response_model=EmailBodyAnalyzeResponse)
def analyze_email_body(
    payload: EmailBodyAnalyzeRequest, db: Session = Depends(get_db)
) -> EmailBodyAnalyzeResponse:
    analyzer = EmailAnalyzer(db)
    return analyzer.analyze_body(payload)
