import json
from dataclasses import dataclass

from logillm.adas.knowledge_base import VOCABULARY

MODES = frozenset({"claim", "request"})


class ValidationError(Exception):
    """The model returned something the logic layer must not accept."""


@dataclass(frozen=True)
class Query:
    mode: str
    target: str


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
        data = json.loads(strip_code_fence(raw))
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
    if target not in VOCABULARY:
        raise ValidationError(f"Unknown target {target!r}.")
    return target


def validate(raw: str) -> Query:
    """Turns a raw model reply into a query the logic layer may act on."""
    data = _parse(raw)
    return Query(mode=_mode(data), target=_target(data))
