from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_CASES_PATH = Path(__file__).with_name("email_cases.jsonl")


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    expected_is_spam: bool
    actual_is_spam: bool | None
    expected_threat_level: str | None
    actual_threat_level: str | None
    spam_probability: float | None
    failures: list[str]


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                cases.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
    return cases


def post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def analyze_case(base_url: str, case: dict[str, Any], timeout: float) -> dict[str, Any]:
    payload = {
        "user_id": case.get("user_id", 1),
        "sender": case["sender"],
        "subject": case.get("subject", ""),
        "body": case["body"],
        "attachment_names": case.get("attachment_names", []),
    }
    return post_json(f"{base_url}/api/emails/analyze", payload, timeout)


def evaluate_case(case: dict[str, Any], actual: dict[str, Any]) -> EvalResult:
    failures: list[str] = []
    expected_is_spam = bool(case["expected_is_spam"])
    actual_is_spam = actual.get("is_spam")
    expected_threat_level = case.get("expected_threat_level")
    expected_threat_levels = case.get("expected_threat_levels")
    actual_threat_level = actual.get("threat_level")
    spam_probability = actual.get("spam_probability")

    if actual_is_spam != expected_is_spam:
        failures.append(f"is_spam expected {expected_is_spam}, got {actual_is_spam}")

    if expected_threat_level and actual_threat_level != expected_threat_level:
        failures.append(
            f"threat_level expected {expected_threat_level}, got {actual_threat_level}"
        )

    if expected_threat_levels and actual_threat_level not in expected_threat_levels:
        failures.append(
            f"threat_level expected one of {expected_threat_levels}, got {actual_threat_level}"
        )

    probability_min = case.get("expected_probability_min")
    if probability_min is not None and (
        spam_probability is None or spam_probability < probability_min
    ):
        failures.append(f"spam_probability expected >= {probability_min}, got {spam_probability}")

    probability_max = case.get("expected_probability_max")
    if probability_max is not None and (
        spam_probability is None or spam_probability > probability_max
    ):
        failures.append(f"spam_probability expected <= {probability_max}, got {spam_probability}")

    return EvalResult(
        case_id=case["id"],
        passed=not failures,
        expected_is_spam=expected_is_spam,
        actual_is_spam=actual_is_spam,
        expected_threat_level=expected_threat_level,
        actual_threat_level=actual_threat_level,
        spam_probability=spam_probability,
        failures=failures,
    )


def run_eval(base_url: str, cases_path: Path, timeout: float) -> list[EvalResult]:
    cases = load_cases(cases_path)
    results: list[EvalResult] = []

    for case in cases:
        actual = analyze_case(base_url, case, timeout)
        results.append(evaluate_case(case, actual))

    return results


def print_report(results: list[EvalResult], elapsed_seconds: float) -> None:
    total = len(results)
    passed = sum(result.passed for result in results)
    failed = total - passed
    false_positive = sum(
        result.expected_is_spam is False and result.actual_is_spam is True for result in results
    )
    false_negative = sum(
        result.expected_is_spam is True and result.actual_is_spam is False for result in results
    )

    print("DailyMail email evaluation")
    print(f"Cases: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Accuracy: {passed / total:.2%}" if total else "Accuracy: n/a")
    print(f"False positives: {false_positive}")
    print(f"False negatives: {false_negative}")
    print(f"Elapsed: {elapsed_seconds:.2f}s")
    print()

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {result.case_id} "
            f"is_spam={result.actual_is_spam} "
            f"threat={result.actual_threat_level} "
            f"prob={result.spam_probability}"
        )
        for failure in result.failures:
            print(f"  - {failure}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DailyMail email analysis evaluation cases.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--fail-under", type=float, default=0.8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = time.perf_counter()

    try:
        results = run_eval(args.base_url.rstrip("/"), args.cases, args.timeout)
    except URLError as exc:
        print(
            f"Could not reach API at {args.base_url}. Start the server with "
            f"`uvicorn app.main:app --reload` first. Error: {exc}",
            file=sys.stderr,
        )
        return 2

    elapsed = time.perf_counter() - start
    print_report(results, elapsed)

    total = len(results)
    accuracy = sum(result.passed for result in results) / total if total else 0
    return 0 if accuracy >= args.fail_under else 1


if __name__ == "__main__":
    raise SystemExit(main())
