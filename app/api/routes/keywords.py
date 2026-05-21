from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.keyword import SpamKeyword
from app.schemas.keyword import KeywordCreateRequest, KeywordToggleRequest, SpamKeywordResponse

router = APIRouter()


@router.get("", response_model=list[SpamKeywordResponse], summary="키워드 목록 조회")
def get_keywords(db: Session = Depends(get_db)) -> list[SpamKeyword]:
    return db.query(SpamKeyword).order_by(SpamKeyword.created_at.desc()).all()


@router.post("", response_model=SpamKeywordResponse, summary="키워드 추가")
def add_keyword(payload: KeywordCreateRequest, db: Session = Depends(get_db)) -> SpamKeyword:
    keyword = SpamKeyword(keyword=payload.keyword.strip(), is_active=True)
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


@router.patch("/{keyword_id}", response_model=SpamKeywordResponse, summary="키워드 활성화/비활성화")
def toggle_keyword(keyword_id: int, payload: KeywordToggleRequest, db: Session = Depends(get_db)) -> SpamKeyword:
    keyword = db.get(SpamKeyword, keyword_id)
    if not keyword:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다")
    keyword.is_active = payload.is_active
    db.commit()
    db.refresh(keyword)
    return keyword


@router.delete("/{keyword_id}", summary="키워드 삭제")
def delete_keyword(keyword_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    keyword = db.get(SpamKeyword, keyword_id)
    if not keyword:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다")
    db.delete(keyword)
    db.commit()
    return {"message": "삭제 완료"}
