# DailyMail Backend

AI 기반 보안 특화 이메일 Agent `DailyMail`의 FastAPI 백엔드입니다.
Gemini가 메일 본문을 분석하고, Supabase에 저장된 위험 키워드를 RAG 컨텍스트로 활용해 피싱/스팸 여부와 보안 위험도를 판단합니다.

## 포함된 골격

- FastAPI API 서버
- Supabase PostgreSQL + SQLAlchemy 2.x 연결 설정
- 실제 Supabase 스키마(`tb_mail`, `tb_spam_keywords`, `tb_user`)에 맞춘 저장 모델
- Gemini API 기반 메일 스팸/피싱 분석 adapter
- `app/data/security_baseline.json`의 기본 위험 기준과 사용자 추가 키워드를 검색해 Gemini 프롬프트에 넣는 RAG 서비스 계층
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

## 환경 변수

`.env`의 `DATABASE_URL`을 Supabase PostgreSQL 연결 문자열로 설정합니다.
Direct connection이 IPv6 문제로 실패할 수 있으므로 로컬 개발에서는 Session pooler 연결 문자열을 권장합니다.

```bash
APP_NAME=DailyMail API
APP_ENV=local
DEBUG=true
API_PREFIX=/api
AUTO_CREATE_TABLES=false

DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<password>@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres?sslmode=require

GEMINI_API_KEY=<your-gemini-api-key>
GEMINI_MODEL=gemini-2.5-flash

ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

현재 백엔드는 Supabase 클라이언트를 사용하지 않고 PostgreSQL에 직접 연결합니다. 따라서 실행에 필요한 값은 `DATABASE_URL`과 `GEMINI_API_KEY`입니다.

Supabase에 이미 테이블이 만들어져 있으면 `AUTO_CREATE_TABLES=false`를 사용합니다. 배포 전에는 Alembic 같은 migration 도구로 옮기는 것을 권장합니다.

## Supabase 스키마

현재 서비스는 다음 테이블을 기준으로 동작합니다.

```text
tb_mail
- id
- content
- is_dark
- dark_reason
- security_level
- spam_probability
- user_id
- created_at

tb_spam_keywords
- id
- keyword
- is_active
- created_at

tb_user
- id
- email
- name
- created_at
```

## 주요 엔드포인트

- `GET /health`: 서버 상태 확인
- `POST /api/emails/analyze`: 스팸 키워드 RAG + Gemini 기반 이메일 분석
- `POST /api/feedback`: 사용자가 추가한 스팸 키워드 저장 또는 활성 상태 갱신
- `GET /api/security/rules`: Gemini API 키가 없을 때 쓰는 로컬 보조 규칙 확인

## RAG 흐름

DailyMail의 RAG는 벡터 DB 기반 검색이 아니라, Supabase에 저장된 활성 스팸 키워드를 검색해 Gemini 프롬프트에 주입하는 초기 RAG 구조입니다.

1. 서비스가 `app/data/security_baseline.json`에 기본 위험 기준을 가지고 있습니다.
2. 사용자가 메일 분석을 요청합니다.
3. 백엔드는 메일 제목, 본문, 첨부파일명에서 기본 위험 기준과 활성 키워드가 일치하는 항목을 검색합니다.
4. 검색된 키워드를 Gemini 프롬프트의 근거 컨텍스트로 넣습니다.
5. Gemini가 JSON 형식으로 `is_spam`, `spam_probability`, `threat_level`, 근거를 반환합니다.
6. 분석 결과는 `tb_mail`에 저장됩니다.
7. 사용자가 스팸 키워드를 보내면 `/feedback`을 통해 `tb_spam_keywords`에 저장되고 이후 분석의 RAG 컨텍스트로 사용됩니다. 이미 존재하는 키워드면 새 row를 만들지 않고 활성 상태만 갱신합니다.

## 초기 RAG 기준 데이터

사용자 피드백이 쌓이기 전에도 Gemini가 참고할 기준 데이터가 필요합니다. 그래서 기본 피싱/스팸 패턴은 `app/data/security_baseline.json`에 파일로 관리하고, 사용자가 추가한 키워드는 `tb_spam_keywords`에 저장합니다.
이 baseline은 90% 이상 탐지를 목표로 넓은 위험 신호를 커버하되, 실제 탐지율은 `eval/email_cases.jsonl` 같은 대표 케이스셋으로 반복 측정합니다.

현재 baseline은 다음 범주를 포함합니다.

- 계정/인증 정보 탈취
- 계정 잠김 및 보안 경고 사칭
- 긴급 송금, 계좌 변경, 미결제 인보이스
- 임원/거래처 사칭형 스피어피싱
- 긴급성 압박
- 외부 링크 클릭 및 정보 입력 유도
- 단축 URL 또는 목적지 은닉
- 브랜드/도메인 사칭
- 배송, 통관, 세금 환급 사칭
- 당첨, 보상, 상품권 사기
- 악성 첨부파일 및 매크로 문서
- OAuth 권한 탈취
- QR 피싱
- 민감 개인정보 요청

예시:

```json
[
  {
    "category": "credential_theft",
    "signals": ["비밀번호", "인증번호", "계정 확인"],
    "risk": "dangerous",
    "reason": "인증 정보나 로그인 정보를 요구하는 메일은 계정 탈취 목적의 피싱 가능성이 높습니다."
  },
  {
    "category": "payment_fraud",
    "signals": ["긴급 송금", "계좌 변경", "입금"],
    "risk": "dangerous",
    "reason": "송금 압박이나 계좌 변경 요청은 BEC 또는 스피어피싱에서 자주 나타나는 패턴입니다."
  }
]
```

이 구조에서는 파일의 기본 위험 기준이 1차 RAG 컨텍스트가 되고, 사용자가 추가하는 키워드가 개인화된 피드백 데이터로 누적됩니다. 이후에는 임베딩과 벡터 검색을 붙여 키워드 일치 방식에서 의미 기반 검색으로 확장할 수 있습니다.

## 평가 하네스

서버를 실행한 뒤 샘플 메일셋으로 분석 품질을 검증할 수 있습니다.

```bash
uvicorn app.main:app --reload
python eval/run_email_eval.py --base-url http://127.0.0.1:8000
```

평가 케이스는 `eval/email_cases.jsonl`에 한 줄 JSON 형식으로 추가합니다. 각 케이스는 기대 스팸 여부, 기대 위험도, 확률 범위를 가질 수 있고, `feedback` 배열을 넣으면 분석 전에 사용자 피드백을 먼저 저장해 RAG 반영 여부를 검증합니다.

현재 하네스는 실제 DB에 피드백 키워드를 저장합니다. 동일 키워드는 중복 row를 만들지 않고 활성 상태만 갱신하지만, 평가 전용 키워드가 운영 데이터에 남을 수 있으므로 정식 회귀 테스트로 확장할 때는 테스트 전용 DB나 cleanup 전략을 추가하는 것을 권장합니다.

Codex에게 검증을 맡길 때 사용할 프롬프트 명령 파일은 `eval/CODEX_HARNESS_PROMPT.md`에 있습니다.
