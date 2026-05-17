from app.services.security_detector import SecurityDetector


def test_detects_credential_request() -> None:
    detector = SecurityDetector()

    findings = detector.detect("계정 확인", "비밀번호와 인증번호를 즉시 입력하세요.")

    assert findings
    assert findings[0].label == "credential_request"
