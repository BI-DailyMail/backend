from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.email import EmailMessage, ThreatLevel
from app.schemas.email import EmailAnalyzeRequest, EmailAnalyzeResponse, EmailResponse
from app.services.email_analyzer import EmailAnalyzer

router = APIRouter()


@router.get("", response_model=list[EmailResponse])
def list_emails(db: Session = Depends(get_db)) -> list[EmailMessage]:
    return list(
        db.scalars(
            select(EmailMessage).order_by(EmailMessage.created_at.desc(), EmailMessage.id.desc())
        )
    )


@router.get("/problems", response_model=list[EmailResponse])
def list_problem_emails(db: Session = Depends(get_db)) -> list[EmailMessage]:
    return list(
        db.scalars(
            select(EmailMessage)
            .where(
                or_(
                    EmailMessage.is_dark.is_(True),
                    EmailMessage.security_level.in_(
                        [ThreatLevel.suspicious.value, ThreatLevel.dangerous.value]
                    ),
                )
            )
            .order_by(EmailMessage.created_at.desc(), EmailMessage.id.desc())
        )
    )


@router.post("/analyze", response_model=EmailAnalyzeResponse)
def analyze_email(payload: EmailAnalyzeRequest, db: Session = Depends(get_db)) -> EmailAnalyzeResponse:
    analyzer = EmailAnalyzer(db)
    return analyzer.analyze(payload)
