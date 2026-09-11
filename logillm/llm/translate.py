import json
from dataclasses import dataclass

from logillm.adas.knowledge_base import QUERY_TARGETS, REQUESTABLE_VARS
from logillm.config import LLMConfig
from logillm.llm.client import Message, chat
from logillm.llm.validate import Query, ValidationError, validate

MAX_ATTEMPTS = 3

EXAMPLES: list[tuple[str, dict]] = [
    ("Uključi tempomat.", {"mode": "request", "target": "tempomat_dozvoljen"}),
    (
        "Postavi brzinu na 100 km/h.",
        {"mode": "request", "target": "tempomat_dozvoljen", "speed_kmh": 100},
    ),
    (
        "Da li je bezbjedno uključiti tempomat?",
        {"mode": "claim", "target": "tempomat_dozvoljen"},
    ),
    ("Da li je potrebno hitno kočenje?", {"mode": "claim", "target": "hitno_kocenje"}),
    (
        "Da li treba da smanjim brzinu?",
        {"mode": "claim", "target": "usporavanje_potrebno"},
    ),
    ("Da li su uslovi za vožnju loši?", {"mode": "claim", "target": "losi_uslovi"}),
    ("Postoji li opasnost od sudara?", {"mode": "claim", "target": "rizik_sudara"}),
]

FEEDBACK = """Your reply was rejected by the validator: {error}
Translate the driver's utterance again and answer with a single corrected JSON object and nothing else."""


@dataclass(frozen=True)
class Rejection:
    """A reply that failed validation and the error sent back to the model."""

    reply: str
    error: str


@dataclass(frozen=True)
class Translation:
    """The accepted reply, its validated query and the replies rejected before it."""

    reply: str
    query: Query
    rejections: tuple[Rejection, ...]


def build_system_prompt() -> str:
    """Build instructions and examples for structured query extraction."""
    targets = ", ".join(sorted(QUERY_TARGETS))
    requestable = ", ".join(sorted(REQUESTABLE_VARS))
    examples = "\n\n".join(
        f"Input: {text}\nOutput: {json.dumps(reply, ensure_ascii=False)}" for text, reply in EXAMPLES
    )

    prompt = f"""Your only task is to convert the driver's utterance, given in Serbo-Croatian,
into exactly one JSON object. Return only valid JSON. Do not use Markdown, code fences,
explanation, advice, or any text before or after the JSON.

Your task is only to identify what the driver is asking about. The utterance is your
only input. Road conditions, weather, distance, speed and traffic state come from
sensors, so never guess them from the utterance and never decide whether something
is safe, required or allowed.

JSON fields:

- "mode":
  Decide by the form of the utterance, not by its topic.
  Use "request" when the driver tells the system to do something ("Uključi...",
  "Postavi...").
  Use "claim" when the driver asks a question, including whether an action is safe
  or allowed ("Da li je bezbjedno uključiti tempomat?").

- "target":
  Must be exactly one value from this list: {targets}
  If "mode" is "request", the target must be one of: {requestable}

- "speed_kmh":
  Optional. Include it only when the driver explicitly gives a requested
  cruise-control speed. The value must be a number in km/h.

Examples:

{examples}"""
    return prompt


def translate(text: str, config: LLMConfig | None = None, max_attempts: int = MAX_ATTEMPTS) -> Translation:
    """Translate a driver's utterance into a validated query.

    A reply that fails validation is sent back to the model together with the
    validation error, so the model can correct it in the next attempt. Raise
    ValidationError when none of the attempts produces a valid reply.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    messages: list[Message] = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": text},
    ]
    rejections: list[Rejection] = []

    for _ in range(max_attempts):
        reply = chat(messages, config=config, temperature=0.0)
        try:
            query = validate(reply)
        except ValidationError as error:
            rejections.append(Rejection(reply, str(error)))
            messages += [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": FEEDBACK.format(error=error)},
            ]
        else:
            return Translation(reply, query, tuple(rejections))

    raise ValidationError(f"No valid reply after {max_attempts} attempts. Last error: {rejections[-1].error}")
