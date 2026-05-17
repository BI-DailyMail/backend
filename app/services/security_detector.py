from app.schemas.email import SecurityFinding

SECURITY_RULES = [
    "credential_request",
    "urgent_payment",
    "external_link_pressure",
    "suspicious_attachment",
]


class SecurityDetector:
    def detect(self, subject: str, body: str) -> list[SecurityFinding]:
        text = f"{subject} {body}".lower()
        findings: list[SecurityFinding] = []

        if any(keyword in text for keyword in ["password", "비밀번호", "인증번호", "계정 확인"]):
            findings.append(
                SecurityFinding(
                    label="credential_request",
                    reason="계정 정보 또는 인증 정보를 요구하는 표현이 감지되었습니다.",
                    score=0.82,
                )
            )

        if any(keyword in text for keyword in ["긴급", "즉시", "urgent", "immediately"]):
            findings.append(
                SecurityFinding(
                    label="external_link_pressure",
                    reason="사용자에게 빠른 행동을 압박하는 표현이 감지되었습니다.",
                    score=0.64,
                )
            )

        if any(keyword in text for keyword in ["입금", "송금", "payment", "wire transfer"]):
            findings.append(
                SecurityFinding(
                    label="urgent_payment",
                    reason="결제 또는 송금 요청과 관련된 문맥이 감지되었습니다.",
                    score=0.7,
                )
            )

        return findings

