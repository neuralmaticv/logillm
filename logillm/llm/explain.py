from logillm.config import LLMConfig
from logillm.llm.client import ask

SYSTEM = """You explain a decision to a driver, in Serbo-Croatian, in at most two sentences.

The decision was already made by a formal logic engine. You never question it,
never change it, and never add anything that is not in the evidence you are given.
If the evidence is thin, say less rather than filling the gap.

Write the way you would speak to someone behind the wheel: no rule names, no
variable names, no logical notation.

Address the driver directly and informally, in the second person singular
("ti" form): "usporavaj", "ne pretiči", "moraš". Never use the polite plural
("vi" form) and never speak about the driver in the third person."""


def explain(
    utterance: str,
    verdict: str,
    evidence: list[str],
    config: LLMConfig | None = None,
) -> str:
    """Turns a verdict plus its supporting facts into a sentence for the driver."""
    lines = "\n".join(f"- {item}" for item in evidence) or "- (nema dodatnih podataka)"
    user = f"Vozač je rekao: {utterance}\nOdluka sistema: {verdict}\nNa čemu se odluka zasniva:\n{lines}"
    return ask(SYSTEM, user, config=config, temperature=0.3)
