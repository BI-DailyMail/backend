from fastapi import APIRouter

from app.services.security_detector import SECURITY_RULES

router = APIRouter()


@router.get("/rules")
def list_security_rules() -> dict[str, list[str] | str]:
    return {
        "rules": SECURITY_RULES,
        "note": "Gemini API가 설정되지 않았을 때만 로컬 보조 탐지 규칙으로 사용합니다.",
    }
