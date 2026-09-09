# ADAS knowledge base: inference rules for the logic layer,
# and closed vocabulary that constrains LLM output

from logillm.logic.formula import And, Formula, Implies, Not, Var
from logillm.logic.semantics import collect_variables
from logillm.rules import Comparison

magla = Var("magla")
blizu = Var("blizu")
koci_ispred = Var("koci_ispred")
smanjena_vidljivost = Var("smanjena_vidljivost")
losi_uslovi = Var("losi_uslovi")
rizik_sudara = Var("rizik_sudara")
nivo_visok = Var("nivo_visok")
nivo_kritican = Var("nivo_kritican")
hitno_kocenje = Var("hitno_kocenje")
tempomat_dozvoljen = Var("tempomat_dozvoljen")

KB: list[Formula] = [
    Implies(magla, smanjena_vidljivost),
    Implies(smanjena_vidljivost, losi_uslovi),
    Implies(And(blizu, koci_ispred), rizik_sudara),
    Implies(rizik_sudara, nivo_visok),
    Implies(And(rizik_sudara, losi_uslovi), nivo_kritican),
    Implies(nivo_kritican, hitno_kocenje),
    Implies(losi_uslovi, Not(tempomat_dozvoljen)),
]

SENSOR_THRESHOLDS: dict[str, list[Comparison]] = {
    "blizu": [Comparison("udaljenost", "<", 15)],
    "koci_ispred": [Comparison("relativna_brzina", ">", 5)],
    "magla": [Comparison("vidljivost", "<", 50)],
}

SITUATION_VARS = frozenset({"magla", "blizu", "koci_ispred"})
DERIVED_VARS = frozenset({"smanjena_vidljivost", "losi_uslovi", "rizik_sudara"})
DECISION_VARS = frozenset({"nivo_visok", "nivo_kritican", "hitno_kocenje", "tempomat_dozvoljen"})

VOCABULARY = SITUATION_VARS | DERIVED_VARS | DECISION_VARS


def validate_vocabulary() -> None:
    """The vocabulary must list exactly the variables that appear in KB."""
    kb_vars = set(collect_variables(KB))
    if kb_vars != VOCABULARY:
        raise ValueError(
            f"Vocabulary and knowledge base disagree. "
            f"Only in KB: {sorted(kb_vars - VOCABULARY)}. "
            f"Only in vocabulary: {sorted(VOCABULARY - kb_vars)}."
        )
