"""Evaluate only the LLM translation layer: utterance -> validated structured query.

Each --config names a provider setup built from the project configuration (.env):
  local           local model with thinking disabled
  local-thinking  local model with thinking enabled
  openai          OpenAI model
Without --config, the configured default provider is used.

With --stress, the harder valid and should-reject cases are evaluated instead,
and reported separately from the main translation metrics.
"""

import argparse
import json
import time
from collections import Counter
from dataclasses import dataclass, field

from eval_common import STRESS_CASES_FILE, configure_utf8_output, load_cases, write_csv

from logillm.config import LLMConfig, llm_config
from logillm.llm.translate import Translation, translate
from logillm.llm.validate import Query, UnsupportedQueryError, ValidationError

CONFIGS: dict[str, tuple[str, bool | None]] = {
    "local": ("local", False),
    "local-thinking": ("local", True),
    "openai": ("openai", None),
}

# prefixes of the messages validate() raises when a reply does not have the expected shape
FORMAT_ERROR_PREFIXES = ("Reply is empty", "Reply must be a single line", "Reply must be 'MODE TARGET")
ERROR_TYPES = (
    "request_error",
    "invalid_format",
    "invalid_schema",
    "unsupported",
    "wrong_mode",
    "wrong_target",
    "wrong_speed",
)
# parts of validate() messages for a target outside the knowledge base or one that cannot be requested
INVALID_TARGET_MARKERS = ("Unknown target", "cannot be requested")


@dataclass
class Result:
    name: str
    config: LLMConfig
    cases: int = 0
    valid_format: int = 0
    schema_valid: int = 0
    mode_correct: int = 0
    target_correct: int = 0
    speed_cases: int = 0
    speed_correct: int = 0
    exact_match: int = 0
    latencies: list[float] = field(default_factory=list)
    errors: Counter[str] = field(default_factory=Counter)
    mistakes: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)


def _translate(utterance: str, config: LLMConfig) -> tuple[Translation | None, str | None, str | None]:
    """Return the accepted translation, or None with the error type and the last error message."""
    try:
        return translate(utterance, config=config), None, None
    except UnsupportedQueryError as error:
        return None, "unsupported", str(error)
    except ValidationError as error:
        last_error = str(error).split("Last error: ", 1)[-1]
        kind = "invalid_format" if last_error.startswith(FORMAT_ERROR_PREFIXES) else "invalid_schema"
        return None, kind, last_error
    except (RuntimeError, TypeError) as error:
        return None, "request_error", str(error)


def _query_errors(query: Query, expected: Query) -> list[str]:
    errors = []
    if query.mode != expected.mode:
        errors.append("wrong_mode")
    if query.target != expected.target:
        errors.append("wrong_target")
    if query.speed_kmh != expected.speed_kmh:
        errors.append("wrong_speed")
    return errors


def evaluate(name: str, config: LLMConfig, cases: list[dict]) -> Result:
    result = Result(name, config)
    for case in cases:
        expected = Query(**case["expected_query"])
        start = time.perf_counter()
        translation, error, _ = _translate(case["utterance"], config)
        latency = time.perf_counter() - start
        query = translation.query if translation else None
        errors = [error] if error else _query_errors(query, expected)

        result.cases += 1
        result.latencies.append(latency)
        result.errors.update(errors)
        # an "unsupported" reply has a valid format and follows the schema, but wrong for a supported case
        result.valid_format += query is not None or error in ("invalid_schema", "unsupported")
        result.schema_valid += query is not None or error == "unsupported"
        result.speed_cases += expected.speed_kmh is not None
        if query is not None:
            result.mode_correct += query.mode == expected.mode
            result.target_correct += query.target == expected.target
            result.exact_match += query == expected
            if expected.speed_kmh is not None:
                result.speed_correct += query.speed_kmh == expected.speed_kmh
        if errors:
            result.mistakes.append(f"{case['id']}: {', '.join(errors)}; expected {expected}, got {query}")

        result.rows.append(_row(result, case, expected, translation, errors, latency))
    return result


def _row(
    result: Result,
    case: dict,
    expected: Query,
    translation: Translation | None,
    errors: list[str],
    latency: float,
) -> dict:
    """Build one CSV row describing a single case under one configuration."""
    query = translation.query if translation else None
    return {
        "config": result.name,
        "provider": result.config.provider,
        "model": result.config.model,
        "case_id": case["id"],
        "utterance": case["utterance"],
        "expected_mode": expected.mode,
        "expected_target": expected.target,
        "expected_speed_kmh": expected.speed_kmh,
        "predicted_mode": query.mode if query else None,
        "predicted_target": query.target if query else None,
        "predicted_speed_kmh": query.speed_kmh if query else None,
        "exact_match": query == expected,
        "errors": ";".join(errors),
        "attempts": len(translation.rejections) + 1 if translation else None,
        "prompt_tokens": translation.usage.prompt_tokens if translation else None,
        "completion_tokens": translation.usage.completion_tokens if translation else None,
        "cached_tokens": translation.usage.cached_tokens if translation else None,
        "latency_s": round(latency, 3),
        "reply": translation.reply.strip() if translation else None,
    }


@dataclass
class StressResult:
    name: str
    config: LLMConfig
    valid_cases: int = 0
    valid_exact: int = 0
    reject_cases: int = 0
    reject_passed: int = 0
    wrongly_accepted: int = 0
    marked_unsupported: int = 0
    invalid_targets: int = 0
    request_errors: int = 0
    latencies: list[float] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)


def _saw_invalid_target(translation: Translation | None, error_message: str | None) -> bool:
    """Return whether a rejected reply named an unknown or non-requestable target.

    For a failed translation only the error of the last attempt is known.
    """
    messages = [rejection.error for rejection in translation.rejections] if translation else [error_message or ""]
    return any(marker in message for message in messages for marker in INVALID_TARGET_MARKERS)


def evaluate_stress(name: str, config: LLMConfig, cases: list[dict]) -> StressResult:
    """Evaluate harder valid cases and cases the translation layer should reject."""
    result = StressResult(name, config)
    for case in cases:
        start = time.perf_counter()
        translation, error, message = _translate(case["utterance"], config)
        latency = time.perf_counter() - start
        query = translation.query if translation else None
        invalid_target = _saw_invalid_target(translation, message)

        result.latencies.append(latency)
        result.request_errors += error == "request_error"
        result.invalid_targets += invalid_target
        if case.get("should_reject"):
            # rejected means the model marked it unsupported or translate() gave up after its retries
            expected = "rejection"
            passed = error in ("unsupported", "invalid_format", "invalid_schema")
            result.reject_cases += 1
            result.reject_passed += passed
            result.marked_unsupported += error == "unsupported"
            result.wrongly_accepted += query is not None
        else:
            expected = Query(**case["expected_query"])
            passed = query == expected
            result.valid_cases += 1
            result.valid_exact += passed

        if not passed:
            result.mistakes.append(f"{case['id']}: expected {expected}, got {query or error}")
        result.rows.append(_stress_row(result, case, translation, error, passed, invalid_target, latency))
    return result


def _stress_row(
    result: StressResult,
    case: dict,
    translation: Translation | None,
    error: str | None,
    passed: bool,
    invalid_target: bool,
    latency: float,
) -> dict:
    """Build one CSV row describing a single stress case under one configuration."""
    query = translation.query if translation else None
    expected_query = case.get("expected_query")
    return {
        "config": result.name,
        "provider": result.config.provider,
        "model": result.config.model,
        "case_id": case["id"],
        "category": case.get("category"),
        "utterance": case["utterance"],
        "should_reject": bool(case.get("should_reject")),
        "expected_query": json.dumps(expected_query, ensure_ascii=False) if expected_query else None,
        "predicted_mode": query.mode if query else None,
        "predicted_target": query.target if query else None,
        "predicted_speed_kmh": query.speed_kmh if query else None,
        "passed": passed,
        "error": error,
        "invalid_target_seen": invalid_target,
        "attempts": len(translation.rejections) + 1 if translation else None,
        "prompt_tokens": translation.usage.prompt_tokens if translation else None,
        "completion_tokens": translation.usage.completion_tokens if translation else None,
        "cached_tokens": translation.usage.cached_tokens if translation else None,
        "latency_s": round(latency, 3),
        "reply": translation.reply.strip() if translation else None,
    }


def _percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "n/a"


def print_table(results: list[Result]) -> None:
    rows: list[tuple[str, list[str]]] = [
        ("model", [r.config.model for r in results]),
        ("cases", [str(r.cases) for r in results]),
        ("valid format", [_percent(r.valid_format, r.cases) for r in results]),
        ("schema valid", [_percent(r.schema_valid, r.cases) for r in results]),
        ("mode accuracy", [_percent(r.mode_correct, r.cases) for r in results]),
        ("target accuracy", [_percent(r.target_correct, r.cases) for r in results]),
        ("speed_kmh accuracy", [_percent(r.speed_correct, r.speed_cases) for r in results]),
        ("exact match", [_percent(r.exact_match, r.cases) for r in results]),
        ("avg latency", [f"{sum(r.latencies) / len(r.latencies):.2f} s" for r in results]),
        *((f"errors: {kind}", [str(r.errors[kind]) for r in results]) for kind in ERROR_TYPES),
    ]
    _print_rows([r.name for r in results], rows)


def print_stress_table(results: list[StressResult]) -> None:
    rows: list[tuple[str, list[str]]] = [
        ("model", [r.config.model for r in results]),
        ("harder valid cases", [str(r.valid_cases) for r in results]),
        ("harder valid exact match", [_percent(r.valid_exact, r.valid_cases) for r in results]),
        ("rejection cases", [str(r.reject_cases) for r in results]),
        ("rejection pass rate", [_percent(r.reject_passed, r.reject_cases) for r in results]),
        ("  marked unsupported", [str(r.marked_unsupported) for r in results]),
        ("incorrectly accepted", [str(r.wrongly_accepted) for r in results]),
        ("invalid/invented targets", [str(r.invalid_targets) for r in results]),
        ("request errors", [str(r.request_errors) for r in results]),
        ("avg latency", [f"{sum(r.latencies) / len(r.latencies):.2f} s" for r in results]),
    ]
    _print_rows([r.name for r in results], rows)


def _print_rows(names: list[str], rows: list[tuple[str, list[str]]]) -> None:
    header = ("metric", names)
    label_width = max(len(label) for label, _ in [header, *rows])
    widths = [max(len(values[i]) for _, values in [header, *rows]) for i in range(len(names))]

    def line(label: str, values: list[str]) -> str:
        cells = "  ".join(value.rjust(width) for value, width in zip(values, widths, strict=True))
        return f"{label.ljust(label_width)}  {cells}"

    print(line(*header))
    print("-" * len(line(*header)))
    for label, values in rows:
        print(line(label, values))


def _print_mistakes(results: list[Result] | list[StressResult]) -> None:
    for result in results:
        if result.mistakes:
            print(f"\nMistakes [{result.name}]:")
            for mistake in result.mistakes:
                print(f"  {mistake}")


def _run_main(configs: list[tuple[str, LLMConfig]]) -> int:
    cases = load_cases()
    results = []
    for name, config in configs:
        print(f"Evaluating {name} ({config.model}) on {len(cases)} cases...")
        results.append(evaluate(name, config, cases))

    print("\nTranslation evaluation\n")
    print_table(results)
    _print_mistakes(results)

    rows = [row for result in results for row in result.rows]
    print(f"\nPer-case results: {write_csv('translation', rows)}")
    return 0


def _run_stress(configs: list[tuple[str, LLMConfig]]) -> int:
    cases = load_cases(STRESS_CASES_FILE)
    results = []
    for name, config in configs:
        print(f"Stress-evaluating {name} ({config.model}) on {len(cases)} cases...")
        results.append(evaluate_stress(name, config, cases))

    print("\nTranslation stress evaluation\n")
    print_stress_table(results)
    _print_mistakes(results)

    rows = [row for result in results for row in result.rows]
    print(f"\nPer-case results: {write_csv('translation_stress', rows)}")
    return 0


def main() -> int:
    configure_utf8_output()
    parser = argparse.ArgumentParser(description="Evaluate the LLM translation layer.")
    parser.add_argument(
        "--config",
        action="append",
        choices=sorted(CONFIGS),
        help="configuration to evaluate; repeat to compare several",
    )
    parser.add_argument(
        "--stress",
        action="store_true",
        help="evaluate the harder valid and should-reject cases instead of the main cases",
    )
    args = parser.parse_args()

    try:
        if args.config:
            configs = [(name, llm_config(*CONFIGS[name])) for name in args.config]
        else:
            default = llm_config()
            configs = [(default.provider, default)]
    except ValueError as error:
        print(f"Error: {error}")
        return 1

    return _run_stress(configs) if args.stress else _run_main(configs)


if __name__ == "__main__":
    raise SystemExit(main())
