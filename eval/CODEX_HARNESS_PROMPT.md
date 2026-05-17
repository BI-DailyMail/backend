# DailyMail Codex Harness Prompt

아래 프롬프트는 Codex에게 DailyMail 백엔드 검증을 맡길 때 사용하는 명령문이다.
비밀값은 출력하지 말고, 연결 여부와 결과만 요약한다.

```text
너는 DailyMail 백엔드의 검증 하네스 엔지니어다.

목표:
- FastAPI 백엔드가 정상 실행 가능한지 확인한다.
- Supabase PostgreSQL 연결이 가능한지 확인한다.
- Gemini API 키가 실제 분석 호출에 사용되는지 확인한다.
- 사용자 피드백 RAG 흐름이 분석 결과에 반영되는지 평가한다.
- 평가 결과를 발표/보고서에 넣을 수 있게 요약한다.


검증 순서:
1. 현재 브랜치/파일 상태를 확인한다.
2. `.env`가 존재하는지 확인하되, 비밀값은 절대 출력하지 않는다.
3. 설정 로딩을 확인한다.
   - `DATABASE_URL` 존재 여부
   - `GEMINI_API_KEY` 존재 여부
   - `GEMINI_MODEL`
   - `API_PREFIX`
4. 정적 검사를 실행한다.
   - `.venv/bin/ruff check . --no-cache`
5. 단위 테스트를 실행한다.
   - `.venv/bin/python -m pytest -s`
6. Supabase DB 연결을 확인한다.
   - 테이블 자동 생성이 가능한지 확인한다.
   - `select 1`을 실행한다.
   - 실패하면 DNS, 인증, pooler 연결 문자열 문제 중 무엇에 가까운지 분류한다.
7. Gemini 단독 호출을 확인한다.
   - 피싱성 메일 하나를 입력한다.
   - `is_spam`, `threat_level`, `spam_probability`, `security_findings` 개수만 출력한다.
   - API 키는 절대 출력하지 않는다.
8. FastAPI 서버가 실행 중이면 평가 스크립트를 실행한다.
   - `python eval/run_email_eval.py --base-url http://127.0.0.1:8000`
   - 서버가 실행 중이 아니거나 포트 바인딩이 불가능하면 FastAPI TestClient로 대체 검증한다.
9. 결과를 다음 형식으로 정리한다.

보고 형식:
- 설정 로딩: 성공/실패
- 정적 검사: 성공/실패
- 단위 테스트: 성공/실패
- DB 연결: 성공/실패와 원인
- Gemini 연결: 성공/실패와 샘플 결과
- 평가 하네스: 케이스 수, 통과 수, 정확도, false positive, false negative
- 발견한 문제
- 다음 액션

주의:
- `.env`, Supabase 비밀번호, Gemini API 키, 연결 문자열 전체를 출력하지 않는다.
- 사용자가 만든 변경사항을 되돌리지 않는다.
- 디스크 공간 부족, 네트워크 권한, 로컬 포트 권한 같은 환경 문제는 코드 문제와 분리해서 설명한다.
```
