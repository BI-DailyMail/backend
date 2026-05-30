from app.services.security_baseline import find_matching_baseline, load_security_baseline


def test_security_baseline_has_broad_coverage() -> None:
    rules = load_security_baseline()
    categories = {rule.category for rule in rules}

    assert len(rules) >= 10
    assert "credential_theft" in categories
    assert "payment_fraud" in categories
    assert "executive_or_vendor_impersonation" in categories
    assert "suspicious_attachment" in categories


def test_security_baseline_matches_spear_phishing_payment_request() -> None:
    matches = find_matching_baseline(
        "대표님 지시입니다. 오늘 안으로 변경된 계좌로 긴급 송금 처리해주세요."
    )
    labels = {match.label for match in matches}

    assert "urgent_payment" in labels
    assert "impersonation_pressure" in labels


def test_security_baseline_does_not_match_normal_meeting() -> None:
    matches = find_matching_baseline(
        "내일 오후 2시에 프로젝트 진행 상황을 공유하는 회의를 진행하겠습니다."
    )

    assert matches == []
