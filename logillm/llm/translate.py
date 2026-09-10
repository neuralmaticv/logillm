import json

from logillm.adas.knowledge_base import QUERY_TARGETS, REQUESTABLE_VARS
from logillm.config import LLMConfig
from logillm.llm.client import ask

EXAMPLES: list[tuple[str, dict]] = [
    ("Uključi tempomat.", {"mode": "request", "target": "tempomat_dozvoljen"}),
    (
        "Postavi brzinu na 100 km/h.",
        {"mode": "request", "target": "tempomat_dozvoljen", "speed_kmh": 100},
    ),
    ("Mogu li uključiti tempomat?", {"mode": "claim", "target": "tempomat_dozvoljen"}),
    ("Treba li da kočim?", {"mode": "claim", "target": "hitno_kocenje"}),
    ("Treba li da usporim?", {"mode": "claim", "target": "usporavanje_potrebno"}),
    ("Jesu li uslovi loši?", {"mode": "claim", "target": "losi_uslovi"}),
    ("Prijeti li sudar?", {"mode": "claim", "target": "rizik_sudara"}),
]


def build_system_prompt() -> str:
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


def translate(text: str, config: LLMConfig | None = None) -> str:
    return ask(build_system_prompt(), text, config=config, temperature=0.0)
