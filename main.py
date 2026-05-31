import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import analyze, mails, keywords

load_dotenv()

app = FastAPI(
    title="매일메일 API",
    description="""
## 매일메일 백엔드 API

AI 기반 이메일 보안 분석 서비스 **매일메일**의 백엔드입니다.

### 주요 기능
- **메일 분석** : Gemini AI로 보안 등급 및 다크 데이터 자동 분석
- **메일 관리** : 분석된 메일 조회 및 저장
- **스팸 키워드 관리** : 스팸 필터 키워드 등록 / 수정 / 삭제
""",
    version="1.0.0",
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(mails.router, prefix="/api")
app.include_router(keywords.router, prefix="/api")
