from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.email import EmailAnalyzeRequest, EmailAnalyzeResponse
from app.services.email_analyzer import EmailAnalyzer

router = APIRouter()


@router.post("/analyze", response_model=EmailAnalyzeResponse)
def analyze_email(payload: EmailAnalyzeRequest, db: Session = Depends(get_db)) -> EmailAnalyzeResponse:
    analyzer = EmailAnalyzer(db)
    return analyzer.analyze(payload)

