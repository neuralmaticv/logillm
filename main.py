from logillm.engine import run_engine
from logillm.facts import Facts
from logillm.rules import THREAT_RULES

SCENARIOS: list[Facts] = [
    {"udaljenost": 3, "relativna_brzina": 10},
    {"udaljenost": 10, "relativna_brzina": 0},
    {"udaljenost": 20, "relativna_brzina": 8},
]


def show(facts: Facts) -> None:
    results, trace = run_engine(THREAT_RULES, facts)
    decision = results.get("nivo_prijetnje", "(nema odluke)")

    print(f"ulaz:   {facts}")
    print(f"odluka: nivo_prijetnje = {decision}")
    print("trace (pravila, po prioritetu):")
    for rule in trace:
        print(f"   - {rule.name} (prioritet {rule.priority}) -> {rule.result_value}")
    print("-" * 60)


def main() -> None:
    print("=== ADAS: procjena prijetnje ===")
    print("-" * 60)
    for facts in SCENARIOS:
        show(facts)


if __name__ == "__main__":
    main()
