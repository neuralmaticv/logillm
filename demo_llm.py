import sys

from logillm.adas.scenarios import LLM_SCENARIOS
from logillm.config import llm_config
from logillm.llm.explain import explain
from logillm.llm.translate import translate
from logillm.llm.validate import ValidationError, validate
from logillm.pipeline import decide

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DRIVER_INPUTS = [
    "Uključi tempomat.",
    "Postavi tempomat na 100 km/h.",
    "Postoji li opasnost od sudara?",
    "Da li treba da smanjim brzinu?",
]


def run(text: str, config) -> None:
    print(f"\nvozač:   {text}")

    structured_output = translate(text, config=config)
    print(f"strukturirani izlaz: {structured_output.strip()}")

    try:
        query = validate(structured_output)
    except ValidationError as error:
        print(f"         ODBIJENO - {error}")
        return

    for scenario in LLM_SCENARIOS:
        decision = decide(query, scenario.readings)
        print(f"\n  {scenario.description}")
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
