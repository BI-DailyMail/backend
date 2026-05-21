from fastapi import APIRouter, HTTPException
from schemas import SpamKeyword, KeywordCreateRequest, KeywordToggleRequest
from services.supabase_client import get_supabase

router = APIRouter(tags=["스팸 키워드 관리"])


@router.get(
    "/keywords",
    response_model=list[SpamKeyword],
    summary="키워드 목록 조회",
    description="""
등록된 스팸 키워드를 최신순으로 전체 반환합니다.

**스마트 필터** 화면에서 사용합니다.
""",
)
def get_keywords():
    supabase = get_supabase()
    response = supabase.table("tb_spam_keywords").select("*").order("created_at", desc=True).execute()
    return response.data


@router.post(
    "/keywords",
    response_model=SpamKeyword,
    summary="키워드 추가",
    description="""
새로운 스팸 키워드를 등록합니다. 등록 시 기본값으로 활성화(is_active: true) 상태입니다.

**스마트 필터** 화면의 키워드 입력창에서 사용합니다.
""",
)
def add_keyword(request: KeywordCreateRequest):
    supabase = get_supabase()
    response = supabase.table("tb_spam_keywords").insert({
        "keyword": request.keyword.strip(),
        "is_active": True,
    }).execute()

    if not response.data:
        raise HTTPException(status_code=500, detail="키워드 추가 실패")
    return response.data[0]


@router.patch(
    "/keywords/{keyword_id}",
    response_model=SpamKeyword,
    summary="키워드 활성화 / 비활성화",
    description="""
특정 키워드의 활성 상태를 변경합니다.

- `is_active: true` → 활성화 (스팸 필터에 적용됨)
- `is_active: false` → 비활성화 (필터에서 제외됨)

**스마트 필터** 화면의 토글 버튼에서 사용합니다.
""",
)
def toggle_keyword(keyword_id: int, request: KeywordToggleRequest):
    supabase = get_supabase()
    response = (
        supabase.table("tb_spam_keywords")
        .update({"is_active": request.is_active})
        .eq("id", keyword_id)
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다")
    return response.data[0]


@router.delete(
    "/keywords/{keyword_id}",
    summary="키워드 삭제",
    description="""
특정 키워드를 영구 삭제합니다.

**스마트 필터** 화면의 삭제 버튼에서 사용합니다.
""",
)
def delete_keyword(keyword_id: int):
    supabase = get_supabase()
    supabase.table("tb_spam_keywords").delete().eq("id", keyword_id).execute()
    return {"message": "삭제 완료"}
