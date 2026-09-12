import math
from dataclasses import dataclass

from logillm.adas.knowledge_base import QUERY_TARGETS, REQUESTABLE_VARS, SPEED_TARGETS

MODES = frozenset({"claim", "request"})
UNSUPPORTED = "unsupported"
MAX_PARTS = 3


class ValidationError(Exception):
    """The model returned something the logic layer must not accept."""


class UnsupportedQueryError(ValidationError):
    """The model marked the utterance as outside the supported ADAS queries."""


@dataclass(frozen=True)
class Query:
    mode: str
    target: str
    speed_kmh: float | None = None


def strip_reasoning(text: str) -> str:
    """Remove an optional reasoning block emitted by a model.

    Treat content after the last closing tag as the answer. If the model emitted
    only an opening tag, keep the content that appeared before it.
    """
    if "</think>" in text:
        return text.rsplit("</think>", 1)[1].strip()
    if "<think>" in text:
        # The model opened a reasoning block but did not close it.
        return text.split("<think>", 1)[0].strip()
    return text.strip()


def strip_code_fence(text: str) -> str:
    """Remove one optional Markdown code fence from a model reply."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines[1:]).strip()


def _parts(raw: str) -> list[str]:
    """Split the reply into whitespace-separated parts of a single line."""
    text = strip_code_fence(strip_reasoning(raw))
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValidationError("Reply is empty.")
    if len(lines) > 1:
        raise ValidationError(f"Reply must be a single line but has {len(lines)} lines.")

    parts = lines[0].split()
    if len(parts) > MAX_PARTS:
        raise ValidationError(
            f"Reply must be 'MODE TARGET [SPEED]' with at most {MAX_PARTS} parts "
            f"but has {len(parts)}: {parts}. SPEED must be a bare number without a unit."
        )
    return parts


def _mode(parts: list[str]) -> str:
    mode = parts[0]
    if mode not in MODES:
        raise ValidationError(f"Unknown mode {mode!r}. Allowed: {sorted(MODES)}.")
    return mode


def _target(parts: list[str]) -> str:
    if len(parts) < 2:
        raise ValidationError("Reply must name a target after the mode.")

    target = parts[1]
    if target not in QUERY_TARGETS:
        raise ValidationError(f"Unknown target {target!r}.")
    return target


def _speed(parts: list[str], target: str) -> float | None:
    if len(parts) < MAX_PARTS:
        return None
    if target not in SPEED_TARGETS:
        raise ValidationError(f"Target {target!r} does not accept a speed.")

    try:
        value = float(parts[2])
    except ValueError as error:
        raise ValidationError(f"Speed {parts[2]!r} must be a bare number without a unit.") from error
    if not math.isfinite(value) or value <= 0:
        raise ValidationError("Speed must be a positive finite number.")
    return value


def validate(raw: str) -> Query:
    """Convert a raw model reply into a query accepted by the logic layer.

    A reply is one line: 'MODE TARGET [SPEED]' or the single word 'unsupported'.
    Raise UnsupportedQueryError when the model marks the utterance as unsupported.
    """
    parts = _parts(raw)
    if parts[0] == UNSUPPORTED:
        if len(parts) != 1:
            raise ValidationError(f"A reply of {UNSUPPORTED!r} must stand alone.")
        raise UnsupportedQueryError("The utterance is outside the supported ADAS queries.")

    mode = _mode(parts)
    target = _target(parts)
    if mode == "request" and target not in REQUESTABLE_VARS:
        raise ValidationError(f"Target {target!r} cannot be requested.")
    return Query(mode=mode, target=target, speed_kmh=_speed(parts, target))
