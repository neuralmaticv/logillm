import json
import math
from dataclasses import dataclass

from logillm.adas.knowledge_base import QUERY_TARGETS, REQUESTABLE_VARS

MODES = frozenset({"claim", "request"})
REQUIRED_FIELDS = frozenset({"mode", "target"})
OPTIONAL_FIELDS = frozenset({"speed_kmh"})
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS
SPEED_TARGETS = frozenset({"tempomat_dozvoljen"})


class ValidationError(Exception):
    """The model returned something the logic layer must not accept."""


@dataclass(frozen=True)
class Query:
    mode: str
    target: str
    speed_kmh: float | None = None


def strip_reasoning(text: str) -> str:
    """Drops a reasoning block emitted by models.

    Everything after the closing tag </think> is the actual answer.
    """
    if "</think>" in text:
        return text.rsplit("</think>", 1)[1].strip()
    if "<think>" in text:
        # opening tag with no closing one: the model never finished thinking
        return text.split("<think>", 1)[0].strip()
    return text.strip()


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines[1:]).strip()


def _parse(raw: str) -> dict:
    try:
        data = json.loads(strip_code_fence(strip_reasoning(raw)))
    except json.JSONDecodeError as error:
        raise ValidationError(f"Reply is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise ValidationError(f"Reply is not a JSON object but {type(data).__name__}.")
    return data


def _mode(data: dict) -> str:
    mode = data.get("mode")
    if mode not in MODES:
        raise ValidationError(f"Unknown mode {mode!r}. Allowed: {sorted(MODES)}.")
    return mode


def _target(data: dict) -> str:
    target = data.get("target")
    if target not in QUERY_TARGETS:
        raise ValidationError(f"Unknown target {target!r}.")
    return target


def _speed(data: dict, target: str) -> float | None:
    if "speed_kmh" not in data:
        return None
    value = data["speed_kmh"]
    if target not in SPEED_TARGETS:
        raise ValidationError(f"Target {target!r} does not accept a speed.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("Field 'speed_kmh' must be a number.")
    if not math.isfinite(value) or value <= 0:
        raise ValidationError("Field 'speed_kmh' must be a positive finite number.")
    return float(value)


def validate(raw: str) -> Query:
    """Turns a raw model reply into a query the logic layer may act on."""
    data = _parse(raw)
    fields = set(data)
    if not REQUIRED_FIELDS <= fields or not fields <= ALLOWED_FIELDS:
        raise ValidationError(
            f"Reply must contain {sorted(REQUIRED_FIELDS)} "
            f"and may contain {sorted(OPTIONAL_FIELDS)}. "
            f"Missing: {sorted(REQUIRED_FIELDS - fields)}. "
            f"Unexpected: {sorted(fields - ALLOWED_FIELDS)}."
        )

    mode = _mode(data)
    target = _target(data)
    if mode == "request" and target not in REQUESTABLE_VARS:
        raise ValidationError(f"Target {target!r} cannot be requested.")
    return Query(mode=mode, target=target, speed_kmh=_speed(data, target))
