from logillm.config import LLMConfig
from logillm.llm.client import ask

SYSTEM = """Explain the system's decision to the driver in Serbo-Croatian (ijekavian),
in at most two sentences, like a short in-car assistance message.

The decision is final and comes from a formal logic engine. Use only the evidence
given: never question it, never add facts, and say less if the evidence is thin.

MORA VAŽITI / NE MORA VAŽITI: the readings do or do not establish it; "ne mora"
does not mean it is false. SMIJE / NE SMIJE: a rule allows or forbids the action.

Do not mention rules, variable names or logic. Address the driver informally
("uspori", "možeš", "ne smiješ"), never with "vi" or in the third person."""


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
