from app.services.text_normalizer import normalize_keyword


def test_normalize_keyword_ignores_spaces_and_case() -> None:
    assert normalize_keyword("개인 정보") == normalize_keyword("개인정보")
    assert normalize_keyword("  OAuth   권한 ") == "oauth권한"
