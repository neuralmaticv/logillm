from logillm.config import LLMConfig
from logillm.llm.client import ask

SYSTEM = """Explain the system's decision to the driver in Serbo-Croatian (ijekavian), in at most two sentences.

The decision comes from a formal logic engine and is final. Use only the evidence
you are given: never question or change the decision and never add facts. If the
evidence is thin, say less rather than filling the gap.

Decision meanings:
  MORA VAŽITI     the readings and rules establish it
  NE MORA VAŽITI  the readings do not establish it; this does not mean it is false
  SMIJE           no rule forbids the requested action right now
  NE SMIJE        a rule forbids the requested action right now

Write like a short in-car driver-assistance message.
Do not mention rule names, variable names, formal logic, or logical notation.
Address the driver informally in the second person singular, using forms such
as "uspori", "ne pretiči", "možeš", "ne smiješ". Do not use the formal/plural
second-person form ("vi"/"Vi") and do not refer to the driver in the third person."""


def explain(
    utterance: str,
    verdict: str,
    evidence: list[str],
    config: LLMConfig | None = None,
) -> str:
    """Turn a verdict and its supporting evidence into a sentence for the driver."""
    lines = "\n".join(f"- {item}" for item in evidence) or "- (nema dodatnih podataka)"
    user = f"Korisnik je rekao: {utterance}\nOdluka sistema: {verdict}\nNa čemu se odluka zasniva:\n{lines}"
    return ask(SYSTEM, user, config=config, temperature=0.3)
