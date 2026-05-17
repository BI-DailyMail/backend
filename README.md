# DailyMail Backend

AI 기반 보안 특화 이메일 Agent `DailyMail`의 FastAPI 백엔드 초기 세팅입니다.

## 포함된 골격

- FastAPI API 서버
- Supabase PostgreSQL 호환 SQLAlchemy 2.x 연결 설정
- 이메일 원문 저장 모델
- Gemini API 기반 메일 스팸/피싱 분석 adapter
- 사용자 피드백을 검색해 Gemini 프롬프트에 넣는 RAG 서비스 계층
- 요약, 일정 후보 추출, 다크 데이터 분석 서비스 계층
- React/Vite 프론트엔드 연동을 위한 CORS 설정
- 기본 헬스체크 및 API 테스트

## 실행

```bash
cd DailyMail
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

API 문서는 서버 실행 후 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다.

## Supabase 연결

`.env`의 `DATABASE_URL`을 Supabase PostgreSQL 연결 문자열로 설정합니다.

```bash
DATABASE_URL=postgresql+psycopg://postgres:<password>@<host>:5432/postgres?sslmode=require
GEMINI_API_KEY=<your-gemini-api-key>
GEMINI_MODEL=gemini-2.5-flash
```

현재 백엔드는 Supabase 클라이언트를 사용하지 않고 PostgreSQL에 직접 연결합니다. 따라서 실행에 필요한 값은 `DATABASE_URL`과 `GEMINI_API_KEY`입니다.

초기 개발 단계에서는 `AUTO_CREATE_TABLES=true`로 테이블을 자동 생성합니다. 배포 전에는 Alembic 같은 migration 도구로 옮기는 것을 권장합니다.

## 주요 엔드포인트

- `GET /health`: 서버 상태 확인
- `POST /api/emails/analyze`: 사용자 피드백 RAG + Gemini 기반 이메일 분석
- `POST /api/feedback`: 사용자가 지정한 스팸/정상 판정 저장
- `GET /api/security/rules`: Gemini API 키가 없을 때 쓰는 로컬 보조 규칙 확인

## RAG 흐름

1. 사용자가 메일을 분석 요청합니다.
2. 백엔드는 같은 발신자 도메인 또는 유사 제목의 과거 사용자 피드백을 PostgreSQL에서 검색합니다.
3. 검색된 피드백을 Gemini 프롬프트의 근거 컨텍스트로 넣습니다.
4. Gemini가 JSON 형식으로 `is_spam`, `spam_probability`, `threat_level`, 근거를 반환합니다.
5. 사용자가 결과를 정정하면 `/feedback`에 저장되고 이후 분석의 RAG 컨텍스트로 사용됩니다.

## 평가 하네스

서버를 실행한 뒤 샘플 메일셋으로 분석 품질을 검증할 수 있습니다.

```bash
uvicorn app.main:app --reload
python eval/run_email_eval.py --base-url http://127.0.0.1:8000
```

평가 케이스는 `eval/email_cases.jsonl`에 한 줄 JSON 형식으로 추가합니다. 각 케이스는 기대 스팸 여부, 기대 위험도, 확률 범위를 가질 수 있고, `feedback` 배열을 넣으면 분석 전에 사용자 피드백을 먼저 저장해 RAG 반영 여부를 검증합니다.

Codex에게 검증을 맡길 때 사용할 프롬프트 명령 파일은 `eval/CODEX_HARNESS_PROMPT.md`에 있습니다.
