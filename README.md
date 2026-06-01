# 매일메일 Backend

> AI 기반 스마트 이메일 보안 센티널 — FastAPI 백엔드

---

## 👥 팀원 소개 & 역할

| 이름 | 소속 | 담당 영역 |
|------|------|-----------|
| 정한묵 | LG전자 | 조장, 기말발표 |
| 김지연 | 정보시스템학과 22 | 아키텍처 설계, 문서화 |
| 양병현 | 정보시스템학과 23 | 개발, 중간발표 |
| 홍예원 | 정보시스템학과 24 | 개발 |

---

## 📌 서비스 개요

Gemini AI가 메일 본문을 분석하고, `app/data/security_baseline.json`의 기본 위험 기준과 사용자 정의 스팸 키워드를 RAG 컨텍스트로 활용해 피싱·스팸 여부와 보안 위험도를 판단합니다.

---

## 🛠️ 기술 스택

| 구분 | 기술 |
|------|------|
| **Framework** | FastAPI |
| **AI** | Google Gemini 2.5 Flash |
| **DB** | Supabase (PostgreSQL) |
| **ORM** | SQLAlchemy 2.x |
| **설정 관리** | pydantic-settings |
| **배포** | Railway |

---

## 📁 프로젝트 구조

```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── emails.py      # 메일 분석·조회 엔드포인트
│   │       ├── keywords.py    # 스팸 키워드 CRUD
│   │       └── security.py    # 보안 규칙 조회
│   ├── core/
│   │   └── config.py          # 환경 변수 설정
│   ├── data/
│   │   └── security_baseline.json  # 기본 위험 기준 (RAG 1차 컨텍스트)
│   ├── db/                    # SQLAlchemy 세션·초기화
│   ├── models/                # DB 모델 (EmailMessage, SpamKeyword)
│   ├── schemas/               # Pydantic 요청·응답 스키마
│   ├── services/
│   │   ├── email_analyzer.py      # 분석 오케스트레이터
│   │   ├── gemini_client.py       # Gemini API 어댑터
│   │   ├── rag_context_retriever.py  # 키워드 RAG 검색
│   │   ├── security_baseline.py   # baseline.json 로더
│   │   ├── security_detector.py   # 로컬 보조 규칙 탐지
│   │   └── text_normalizer.py     # 키워드 정규화
│   └── main.py                # FastAPI 앱 진입점
├── eval/
│   ├── email_cases.jsonl      # 평가 케이스셋
│   └── run_email_eval.py      # 평가 하네스
├── tests/                     # 단위 테스트
├── requirements.txt
└── Procfile                   # Railway 배포 설정
```

---

## 🔌 API 엔드포인트

### 헬스체크

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 서버 상태 확인 |

### 메일

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/emails` | 전체 메일 조회 (최신순, `limit`·`offset` 지원) |
| `GET` | `/api/emails/problems` | 위험·주의·다크 데이터 메일 조회 |
| `POST` | `/api/emails/analyze` | 단일 메일 Gemini 분석 후 DB 저장 |
| `POST` | `/api/emails/analyze/batch` | 최대 50개 메일 일괄 분석 |
| `POST` | `/api/emails/analyze/body` | 본문 빠른 분석 (DB 저장 없음) |

### 스팸 키워드

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/keywords` | 키워드 목록 조회 |
| `POST` | `/api/keywords` | 키워드 추가 |
| `PATCH` | `/api/keywords/{id}` | 키워드 활성화·비활성화 |
| `DELETE` | `/api/keywords/{id}` | 키워드 삭제 |

### 보안 규칙

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/security/rules` | 로컬 보조 규칙 목록 확인 |

**보안 등급 기준**

| 값 | 설명 |
|----|------|
| `safe` | 위험 신호가 거의 없는 정상 메일 |
| `warn` | 의심 신호가 있어 확인이 필요한 메일 |
| `danger` | 피싱·스팸·정보 탈취 가능성이 높은 고위험 메일 |

---

## 🗄️ DB 스키마 (Supabase PostgreSQL)

**tb_mail**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | int8 (PK) | |
| sender | varchar | 발신자명 |
| subject | varchar | 메일 제목 |
| body | varchar | 메일 본문 |
| received_at | timestamptz | 수신 시각 |
| is_dark | bool | 다크 데이터 여부 |
| dark_reason | varchar | 다크 데이터·보안 분석 이유 |
| security_level | varchar | `safe` / `warn` / `danger` |
| spam_probability | float | 스팸 확률 (0~1) |
| user_id | int8 | 사용자 FK |
| created_at | timestamptz | |

**tb_spam_keywords**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | int8 (PK) | |
| keyword | varchar | 스팸 키워드 |
| keyword_normalized | varchar | 공백 제거 정규화 값 |
| is_active | bool | 활성 여부 |
| user_id | int8 | 사용자 FK |
| created_at | timestamptz | |

**tb_user**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | int8 (PK) | |
| email | varchar | |
| name | varchar | |
| created_at | timestamptz | |

---

## 🧠 RAG 흐름

벡터 DB 없이 Supabase에 저장된 키워드를 Gemini 프롬프트에 주입하는 경량 RAG 구조입니다.

1. `app/data/security_baseline.json`에 기본 위험 기준 14개 범주 보유
2. 사용자가 메일 분석 요청 시 `user_id`와 함께 전송
3. 백엔드가 메일 제목·본문에서 baseline + 사용자 활성 키워드 매칭
4. 매칭된 항목을 Gemini 프롬프트 컨텍스트로 주입
5. Gemini가 `is_spam`, `spam_probability`, `threat_level`, 근거를 JSON으로 반환
6. 분석 결과를 `tb_mail`에 저장

> 키워드 비교는 공백 제거 normalized 값으로 수행합니다. (`개인 정보` = `개인정보`)

**baseline 위험 범주 (14개)**
계정·인증 정보 탈취 / 계정 잠김·보안 경고 사칭 / 긴급 송금·계좌 변경 / 임원·거래처 사칭 / 긴급성 압박 / 외부 링크·정보 입력 유도 / 단축 URL·목적지 은닉 / 브랜드·도메인 사칭 / 배송·통관·세금 환급 사칭 / 당첨·보상·상품권 사기 / 악성 첨부파일 / OAuth 권한 탈취 / QR 피싱 / 민감 개인정보 요청

---

## 🕵️ 다크 데이터 탐지 기준

| 조건 | 설명 |
|------|------|
| 장기 보관 | `received_at` 기준 365일 이상 지난 메일 |
| 민감정보 패턴 | 주민등록번호·계좌번호·카드번호·인증번호 형식 감지 |
| 의심 첨부파일 | 압축 파일·매크로 문서 등 추가 검사 필요 확장자 |
| 중복 첨부파일 | 동일 파일명 중복 감지 |

> 민감정보 탐지 시 실제 값은 응답에 포함되지 않으며 패턴 감지 여부만 반환합니다.

---

## ⚙️ 로컬 실행 방법

### 1. 가상환경 설치

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 아래 값 입력:

```
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

> Direct connection은 IPv6 문제가 발생할 수 있으므로 **Session pooler** 연결 문자열을 권장합니다.

### 3. 개발 서버 실행

```bash
uvicorn app.main:app --reload
```

API 문서: `http://127.0.0.1:8000/docs`

---

## 🧪 평가 하네스

샘플 메일셋으로 분석 품질을 검증합니다.

```bash
uvicorn app.main:app --reload
python eval/run_email_eval.py --base-url http://127.0.0.1:8000
```

평가 케이스는 `eval/email_cases.jsonl`에 한 줄 JSON 형식으로 추가합니다.

---

## 🚀 배포 (Railway)

`Procfile`에 정의된 명령으로 Railway가 자동 실행합니다.

Railway 환경 변수에 `DATABASE_URL`, `GEMINI_API_KEY`, `ALLOWED_ORIGINS`(Vercel 프론트 도메인 포함)을 설정해야 합니다.
