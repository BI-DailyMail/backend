from app.schemas.email import SecurityFinding
from app.services.security_baseline import find_matching_baseline, load_security_baseline

SECURITY_RULES = [rule.label for rule in load_security_baseline()]


class SecurityDetector:
    def detect(self, subject: str, body: str) -> list[SecurityFinding]:
        text = f"{subject} {body}".lower()
        return [
            SecurityFinding(label=rule.label, reason=rule.reason, score=rule.score)
            for rule in find_matching_baseline(text)
        ]
