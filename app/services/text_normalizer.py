import re


def normalize_keyword(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()
