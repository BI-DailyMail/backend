from fastapi import APIRouter, HTTPException
from schemas import MailRecord, MailSaveRequest
from services.supabase_client import get_supabase

router = APIRouter(tags=["메일 관리"])


@router.get(
    "/mails",
    response_model=list[MailRecord],
    summary="전체 메일 목록 조회",
    description="""
Supabase에 저장된 모든 분석 메일을 최신순으로 반환합니다.

**받은 메일함** 화면에서 사용합니다.
""",
)
def get_mails():
    supabase = get_supabase()
    response = supabase.table("tb_mail").select("*").order("created_at", desc=True).execute()
    return response.data


@router.get(
    "/mails/problems",
    response_model=list[MailRecord],
    summary="문제 메일만 조회",
    description="""
보안 등급이 위험(danger) 또는 주의(warn)이거나, 다크 데이터가 감지된 메일만 반환합니다.

**다크 데이터** 화면과 **보안 센터** 화면에서 사용합니다.
""",
)
def get_problematic_mails():
    supabase = get_supabase()
    response = (
        supabase.table("tb_mail")
        .select("*")
        .or_("security_level.neq.safe,is_dark.eq.true")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


@router.post(
    "/mails",
    response_model=MailRecord,
    summary="분석 결과 저장",
    description="""
분석된 메일 데이터를 Supabase `tb_mail` 테이블에 직접 저장합니다.

> `/api/analyze`는 분석 + 저장을 동시에 처리합니다.
> 이 엔드포인트는 분석 없이 저장만 필요할 때 사용합니다.
""",
)
def save_mail(request: MailSaveRequest):
    supabase = get_supabase()
    response = supabase.table("tb_mail").insert({
        "content": request.content,
        "subject": request.subject,
        "is_dark": request.is_dark,
        "dark_reason": request.dark_reason,
        "security_level": request.security_level,
    }).execute()

    if not response.data:
        raise HTTPException(status_code=500, detail="메일 저장 실패")
    return response.data[0]
