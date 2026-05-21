from fastapi import APIRouter, HTTPException
from schemas import AnalyzeRequest, AnalysisResult
from services.gemini import analyze_mail
from services.supabase_client import get_supabase

router = APIRouter(tags=["메일 분석"])


def build_dark_reason(result: AnalysisResult) -> str:
    parts = []
    for issue in result.security.issues:
        if issue.type != "safe":
            parts.append(f"{issue.title}: {issue.desc}")
    for dark in result.darkdata:
        parts.append(f"{dark.label}: {dark.reason}")
    return "\n".join(parts)


@router.post(
    "/analyze",
    summary="메일 분석",
    description="""
메일 본문을 입력하면 Gemini AI가 분석하고 결과를 Supabase에 저장합니다.

**반환 데이터:**
- `subject` : AI가 추출한 메일 제목 (15자 이내)
- `summary` : 메일 전체 내용 요약 (2~3문장)
- `security` : 보안 등급 (safe / warn / danger) 및 상세 이유
- `darkdata` : 개인정보·불필요 데이터 감지 항목 목록
""",
)
def analyze(request: AnalyzeRequest):
    try:
        result = analyze_mail(request.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini 분석 실패: {str(e)}")

    dark_reason = build_dark_reason(result)

    supabase = get_supabase()
    supabase.table("tb_mail").insert({
        "content": request.content,
        "subject": result.subject or None,
        "is_dark": len(result.darkdata) > 0,
        "dark_reason": dark_reason or None,
        "security_level": result.security.level,
    }).execute()

    return result
