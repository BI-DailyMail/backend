from google import genai
import json
import os
from schemas import AnalysisResult

PROMPT_TEMPLATE = """아래 이메일을 분석해서 반드시 JSON만 반환하세요. 다른 텍스트나 마크다운 없이 JSON만.

{{
  "subject": "메일 핵심을 담은 짧은 제목 (15자 이내)",
  "summary": "메일 전체 내용을 2-3문장으로 요약",
  "security": {{
    "level": "safe 또는 warn 또는 danger 중 하나",
    "issues": [
      {{ "type": "warn 또는 danger 또는 safe 중 하나", "title": "항목명", "desc": "왜 수상한지 구체적 이유" }}
    ]
  }},
  "darkdata": [
    {{ "label": "발견된 항목 이름", "reason": "이 항목이 다크 데이터로 분류된 구체적 이유" }}
  ]
}}

이메일:
{text}"""


def analyze_mail(text: str) -> AnalysisResult:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=PROMPT_TEMPLATE.format(text=text),
    )

    raw = response.text.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    return AnalysisResult(**data)
