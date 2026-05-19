from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.services.text_normalizer import normalize_keyword


BASELINE_PATH = Path(__file__).resolve().parents[1] / "data" / "security_baseline.json"


@dataclass(frozen=True)
class SecurityBaselineRule:
    category: str
    label: str
    signals: tuple[str, ...]
    risk: str
    score: float
    reason: str


@lru_cache(maxsize=1)
def load_security_baseline() -> tuple[SecurityBaselineRule, ...]:
    with BASELINE_PATH.open(encoding="utf-8") as file:
        items: list[dict[str, Any]] = json.load(file)

    return tuple(
        SecurityBaselineRule(
            category=str(item["category"]),
            label=str(item["label"]),
            signals=tuple(str(signal) for signal in item["signals"]),
            risk=str(item["risk"]),
            score=float(item["score"]),
            reason=str(item["reason"]),
        )
        for item in items
    )


def find_matching_baseline(text: str) -> list[SecurityBaselineRule]:
    normalized = normalize_keyword(text)
    return [
        rule
        for rule in load_security_baseline()
        if any(normalize_keyword(signal) in normalized for signal in rule.signals)
    ]
