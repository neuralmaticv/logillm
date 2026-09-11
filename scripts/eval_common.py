"""Helpers shared by the evaluation scripts."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
CASES_FILE = EXPERIMENTS_DIR / "eval_cases.jsonl"
STRESS_CASES_FILE = EXPERIMENTS_DIR / "eval_stress_cases.jsonl"
RESULTS_DIR = EXPERIMENTS_DIR / "results"


def configure_utf8_output() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_cases(path: Path = CASES_FILE) -> list[dict]:
    """Read one evaluation case per non-empty line."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def write_csv(prefix: str, rows: list[dict]) -> Path:
    """Write per-case rows to a timestamped CSV file in the results directory."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    # utf-8-sig so that Excel shows Serbian characters correctly
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path
