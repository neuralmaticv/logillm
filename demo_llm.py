import sys

from logillm.adas.knowledge_base import KB, SENSOR_THRESHOLDS
from logillm.config import llm_config
from logillm.facts import Facts
from logillm.grounding import ground
from logillm.llm.translate import translate
from logillm.llm.validate import Query, ValidationError, validate
from logillm.logic.formula import Var
from logillm.logic.semantics import as_formulas, consistency, entails, format_valuation

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


def decide(query: Query, facts: Facts) -> str:
    premises = [*KB, *as_formulas(ground(SENSOR_THRESHOLDS, facts))]
    target = Var(query.target)

    if query.mode == "claim":
        result = entails(premises, target)
        if result.entailed:
            return "MORA VAŽITI"
        protivprimjer = format_valuation(result.countermodel or {}, only_true=True) or "(ništa)"
        return f"NE MORA VAŽITI (protivprimjer: {protivprimjer})"

    if consistency([*premises, target]).consistent:
        return "SMIJE"
    return "NE SMIJE (u sukobu s bazom znanja)"


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
        print(f"  {description:28} -> {decide(query, facts)}")


def main() -> None:
    provider = sys.argv[1] if len(sys.argv) > 1 else None
    config = llm_config(provider)
    print(f"provajder: {config.provider} / {config.model}")

    for text in DRIVER_INPUTS:
        run(text, config)
    print()


if __name__ == "__main__":
    main()
