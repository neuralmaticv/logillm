"""Evaluate only the formal logic layer: expected query + sensor readings -> verdict.

The LLM is never called.
"""

import time
from collections import Counter

from eval_common import configure_utf8_output, load_cases, write_csv

from logillm.llm.validate import Query
from logillm.pipeline import decide


def main() -> None:
    configure_utf8_output()
    cases = load_cases()

    times_ms: list[float] = []
    verdicts: Counter[str] = Counter()
    mistakes: list[str] = []
    rows: list[dict] = []

    for case in cases:
        query = Query(**case["expected_query"])
        start = time.perf_counter()
        try:
            verdict = decide(query, case["readings"]).verdict
        except ValueError as error:
            verdict = f"GREŠKA ({error})"
        elapsed_ms = (time.perf_counter() - start) * 1000
        times_ms.append(elapsed_ms)

        verdicts[verdict] += 1
        correct = verdict == case["expected_verdict"]
        if not correct:
            mistakes.append(f"{case['id']}: expected {case['expected_verdict']}, got {verdict}")
        rows.append(
            {
                "case_id": case["id"],
                "mode": query.mode,
                "target": query.target,
                "speed_kmh": query.speed_kmh,
                **case["readings"],
                "expected_verdict": case["expected_verdict"],
                "verdict": verdict,
                "correct": correct,
                "logic_time_ms": round(elapsed_ms, 3),
            }
        )

    correct = len(cases) - len(mistakes)
    print("Logic-only evaluation\n")
    print(f"Cases: {len(cases)}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {100 * correct / len(cases):.1f}%\n")
    print(f"Average logic time: {sum(times_ms) / len(times_ms):.1f} ms")
    print(f"Max logic time: {max(times_ms):.1f} ms\n")
    print("Verdict distribution:")
    for verdict, count in sorted(verdicts.items()):
        print(f"{verdict}: {count}")

    if mistakes:
        print("\nIncorrect verdicts:")
        for mistake in mistakes:
            print(f"  {mistake}")

    print(f"\nPer-case results: {write_csv('logic', rows)}")


if __name__ == "__main__":
    main()
