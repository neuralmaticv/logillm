import sys

from logillm.adas.knowledge_base import KB, SENSOR_THRESHOLDS
from logillm.config import llm_config
from logillm.facts import Facts
from logillm.grounding import ground
from logillm.llm.explain import explain
from logillm.llm.translate import translate
from logillm.llm.validate import Query, ValidationError, validate
from logillm.logic.derivation import conflict_core, derive, relevant
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


def decide(query: Query, facts: Facts) -> tuple[str, list[str]]:
    """Returns the verdict and the facts it rests on, for the explanation step."""
    valuation = ground(SENSOR_THRESHOLDS, facts)
    premises = [*KB, *as_formulas(valuation)]
    target = Var(query.target)
    observed = format_valuation(valuation, only_true=True) or "(ništa posebno)"

    if query.mode == "claim":
        result = entails(premises, target)
        if result.entailed:
            _, trace = derive(KB, valuation)
            rules = [str(step.rule) for step in relevant(trace, query.target)]
            return "MORA VAŽITI", [f"senzori pokazuju: {observed}", *rules]

        other = format_valuation(result.countermodel or {}, only_true=True) or "(ništa)"
        return "NE MORA VAŽITI", [
            f"senzori pokazuju: {observed}",
            f"moguć je slučaj u kojem važi samo: {other}",
        ]

    if consistency([*premises, target]).consistent:
        return "SMIJE", [f"senzori pokazuju: {observed}", "nijedno pravilo to ne zabranjuje"]

    core = conflict_core([*premises, target])
    return "NE SMIJE", [f"senzori pokazuju: {observed}", *(str(formula) for formula in core)]


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
        verdict, evidence = decide(query, facts)
        print(f"\n  {description}")
        print(f"    presuda:     {verdict}")
        for item in evidence:
            print(f"    osnov:       {item}")
        print(f"    objašnjenje: {explain(text, verdict, evidence, config=config).strip()}")


def main() -> None:
    provider = sys.argv[1] if len(sys.argv) > 1 else None
    config = llm_config(provider)
    print(f"provajder: {config.provider} / {config.model}")

    for text in DRIVER_INPUTS:
        run(text, config)
    print()


if __name__ == "__main__":
    main()
