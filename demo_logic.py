import sys

from logillm.adas.knowledge_base import (
    KB,
    SENSOR_THRESHOLDS,
    hitno_kocenje,
    losi_uslovi,
    nivo_kritican,
    nivo_visok,
    smanjena_vidljivost,
    tempomat_dozvoljen,
    usporavanje_potrebno,
    validate_vocabulary,
)
from logillm.adas.scenarios import ALL_SCENARIOS
from logillm.facts import Facts, ThreatLevel
from logillm.grounding import ground
from logillm.logic.formula import Formula, Implies
from logillm.logic.semantics import (
    as_formulas,
    consistency,
    entails,
    format_valuation,
    truth_table,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def premises_for(facts: Facts) -> list[Formula]:
    return [*KB, *as_formulas(ground(SENSOR_THRESHOLDS, facts))]


def threat_level(premises: list[Formula]) -> ThreatLevel:
    if entails(premises, nivo_kritican).entailed:
        return ThreatLevel.CRITICAL
    if entails(premises, nivo_visok).entailed:
        return ThreatLevel.HIGH
    return ThreatLevel.LOW


def show_truth_table(formula: Formula) -> None:
    section(f"Tablica istinitosti: {formula}")
    for row in truth_table(formula):
        print(f"  {format_valuation(row.valuation):45} => {'T' if row.value else 'F'}")


def show_entailment(premises: list[Formula], conclusion: Formula, title: str) -> None:
    section(title)
    result = entails(premises, conclusion)
    print(f"  tvrdnja: {conclusion}")

    if result.entailed:
        print("  presuda: MORA VAŽITI (tačno u svakom modelu premisa)")
        return

    print("  presuda: NE MORA VAŽITI (premise ovo ne garantuju)")
    true_vars = format_valuation(result.countermodel or {}, only_true=True) or "(ništa)"
    print(f"  protivprimjer, u njemu važi samo: {true_vars}")


def show_consistency(premises: list[Formula], request: Formula, title: str) -> None:
    section(title)
    result = consistency([*premises, request])
    print(f"  zahtjev: {request}")

    if result.consistent:
        print("  presuda: SMIJE (nije u sukobu s bazom znanja)")
    else:
        print("  presuda: NE SMIJE (u sukobu s bazom znanja)")


def show_scenarios() -> None:
    for scenario in ALL_SCENARIOS:
        facts = scenario.facts
        valuation = ground(SENSOR_THRESHOLDS, facts)
        premises = premises_for(facts)
        active = format_valuation(valuation, only_true=True) or "(ništa)"

        print(f"\n  {scenario.description}")
        print(f"    senzori:  {facts}")
        print(f"    važi:     {active}")
        print(f"    nivo:     {threat_level(premises)}")
        print(f"    kočenje:  {'DA' if entails(premises, hitno_kocenje).entailed else 'ne'}")
        print(f"    uspori:   {'DA' if entails(premises, usporavanje_potrebno).entailed else 'ne'}")
        print(f"    tempomat: {'SMIJE' if consistency([*premises, tempomat_dozvoljen]).consistent else 'NE SMIJE'}")


def main() -> None:
    validate_vocabulary()

    show_truth_table(Implies(smanjena_vidljivost, losi_uslovi))
    print("  Kada vidljivost nije smanjena, implikacija nije prekršena.")

    show_scenarios()

    first_scenario = ALL_SCENARIOS[0].facts
    show_entailment(
        premises_for(first_scenario),
        hitno_kocenje,
        "Da li prva situacija nalaže hitno kočenje?",
    )

    show_entailment(
        [*KB, hitno_kocenje],
        losi_uslovi,
        "Ako sistem koči, znači li to da su uslovi loši?",
    )
    print("  Sistem može kočiti i po dobrim uslovima: zabluda potvrđivanja posljedice.")

    show_consistency(
        premises_for(first_scenario),
        tempomat_dozvoljen,
        "Zahtjev vozača: uključi tempomat",
    )
    print()


if __name__ == "__main__":
    main()
