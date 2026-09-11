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

    prompt = f"""You are a translator, not an advisor. You turn a driver's utterance,
spoken in Serbian, into JSON. You never decide anything, never explain, and never
write any text around the JSON.

You are given only what the driver said. You know nothing about the road, the
weather or the traffic: sensors provide that separately. Your single job is to
name what the driver is asking about.

Field "mode":
  "claim"   - the driver asks whether something holds or must be done
  "request" - the driver asks for an action to be carried out

Field "target": exactly one name from this list:
  {targets}

For mode "request", the target must be an action from this list:
  {requestable}

Optional field "speed_kmh":
  Include it only when the driver gives a target speed for cruise control.
  Its value must be a number expressed in km/h.

Answer with a single JSON object and nothing else:
{{"mode": "...", "target": "..."}}
When a target speed is present:
{{"mode": "...", "target": "tempomat_dozvoljen", "speed_kmh": 100}}

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
