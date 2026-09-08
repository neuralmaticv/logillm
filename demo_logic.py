import sys

from logillm.logic.formula import And, Formula, Implies, Not, Var
from logillm.logic.semantics import (
    Valuation,
    as_formulas,
    consistency,
    entails,
    format_valuation,
    truth_table,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

magla = Var("magla")
blizu = Var("blizu")
koci_ispred = Var("koci_ispred")
smanjena_vidljivost = Var("smanjena_vidljivost")
losi_uslovi = Var("losi_uslovi")
rizik_sudara = Var("rizik_sudara")
nivo_kritican = Var("nivo_kritican")
hitno_kocenje = Var("hitno_kocenje")
tempomat_dozvoljen = Var("tempomat_dozvoljen")

KB: list[Formula] = [
    Implies(magla, smanjena_vidljivost),
    Implies(smanjena_vidljivost, losi_uslovi),
    Implies(And(blizu, koci_ispred), rizik_sudara),
    Implies(And(rizik_sudara, losi_uslovi), nivo_kritican),
    Implies(nivo_kritican, hitno_kocenje),
    Implies(losi_uslovi, Not(tempomat_dozvoljen)),
]

SITUATION: Valuation = {"magla": True, "blizu": True, "koci_ispred": True}


def section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


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


def main() -> None:
    situation = [*KB, *as_formulas(SITUATION)]

    show_truth_table(Implies(magla, smanjena_vidljivost))
    print("  Bez magle pravilo nije prekršeno, pa je implikacija tačna.")

    show_entailment(situation, hitno_kocenje, "Da li situacija nalaže hitno kočenje?")

    show_entailment(
        [*KB, hitno_kocenje],
        losi_uslovi,
        "Ako sistem koči, znači li to da su uslovi loši?",
    )
    print("  Sistem može kočiti i po dobrim uslovima: zabluda potvrđivanja posljedice.")

    show_consistency(situation, tempomat_dozvoljen, "Zahtjev vozača: uključi tempomat")
    print()


if __name__ == "__main__":
    main()
