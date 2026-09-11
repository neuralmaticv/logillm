import sys

from logillm.adas.knowledge_base import (
    KB,
    SENSOR_THRESHOLDS,
    hitno_kocenje,
    losi_uslovi,
    rizik_sudara,
    smanjena_vidljivost,
    tempomat_dozvoljen,
    trazena_brzina_iznad_ogranicenja,
    usporavanje_potrebno,
    validate_knowledge_base,
)
from logillm.adas.scenarios import ALL_SCENARIOS
from logillm.grounding import SensorReadings, ground
from logillm.logic.formula import Formula, Implies
from logillm.logic.semantics import (
    check_consistency,
    entails,
    format_valuation,
    truth_table,
    valuation_to_formulas,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def premises_for(readings: SensorReadings) -> list[Formula]:
    request_context = {trazena_brzina_iznad_ogranicenja.name: False}
    return [
        *KB,
        *valuation_to_formulas(ground(SENSOR_THRESHOLDS, readings)),
        *valuation_to_formulas(request_context),
    ]


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
    result = check_consistency([*premises, request])
    print(f"  zahtjev: {request}")

    if result.consistent:
        print("  presuda: SMIJE (nije u sukobu s bazom znanja)")
    else:
        print("  presuda: NE SMIJE (u sukobu s bazom znanja)")


def show_scenarios() -> None:
    for scenario in ALL_SCENARIOS:
        readings = scenario.readings
        valuation = ground(SENSOR_THRESHOLDS, readings)
        premises = premises_for(readings)
        active = format_valuation(valuation, only_true=True) or "(ništa)"
        permission_check = check_consistency([*premises, tempomat_dozvoljen])

        print(f"\n  {scenario.description}")
        print(f"    senzori:  {readings}")
        print(f"    važi:     {active}")
        print(f"    kočenje:  {'DA' if entails(premises, hitno_kocenje).entailed else 'ne'}")
        print(f"    uspori:   {'DA' if entails(premises, usporavanje_potrebno).entailed else 'ne'}")
        print(f"    tempomat: {'SMIJE' if permission_check.consistent else 'NE SMIJE'}")
        if permission_check.model is not None:
            relevant_names = (
                losi_uslovi.name,
                rizik_sudara.name,
                trazena_brzina_iznad_ogranicenja.name,
                tempomat_dozvoljen.name,
            )
            relevant_model = {name: permission_check.model[name] for name in relevant_names}
            print(f"    primjer konzistentne dodjele: {format_valuation(relevant_model)}")


def main() -> None:
    validate_knowledge_base()

    show_truth_table(Implies(smanjena_vidljivost, losi_uslovi))
    print("  Kada vidljivost nije smanjena, implikacija nije prekršena.")

    show_scenarios()

    first_scenario = ALL_SCENARIOS[0].readings
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
        "Zahtjev korisnika: uključi tempomat",
    )
    print()


if __name__ == "__main__":
    main()
