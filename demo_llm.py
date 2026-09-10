import sys

from logillm.config import llm_config
from logillm.facts import Facts
from logillm.llm.explain import explain
from logillm.llm.translate import translate
from logillm.llm.validate import ValidationError, validate
from logillm.pipeline import decide

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCENARIOS: list[tuple[str, Facts]] = [
    ("magla, vozilo ispred koči", {"udaljenost": 8, "relativna_brzina": 9, "vidljivost": 30}),
    ("vedro, vozilo ispred koči", {"udaljenost": 8, "relativna_brzina": 9, "vidljivost": 500}),
    ("vedro, put slobodan", {"udaljenost": 60, "relativna_brzina": 0, "vidljivost": 500}),
]

DRIVER_INPUTS = [
    "Uključi tempomat.",
    "Treba li da kočim?",
]


def run(text: str, config) -> None:
    print(f"\nvozač:   {text}")

    raw = translate(text, config=config)
    print(f"prevod:  {raw.strip()}")

    try:
        query = validate(raw)
    except ValidationError as error:
        print(f"         ODBIJENO - {error}")
        return

    for description, facts in SCENARIOS:
        decision = decide(query, facts)
        print(f"\n  {description}")
        print(f"    presuda:     {decision.verdict}")
        for item in decision.evidence:
            print(f"    osnov:       {item}")
        explanation = explain(text, decision.verdict, list(decision.evidence), config=config)
        print(f"    objašnjenje: {explanation.strip()}")


def main() -> None:
    provider = sys.argv[1] if len(sys.argv) > 1 else None
    config = llm_config(provider)
    print(f"provajder: {config.provider} / {config.model}")

    for text in DRIVER_INPUTS:
        run(text, config)
    print()


if __name__ == "__main__":
    main()
