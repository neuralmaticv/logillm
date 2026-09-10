"""ADAS inference rules and proposition names allowed in LLM output."""

from logillm.grounding import Comparison
from logillm.logic.formula import And, Formula, Implies, Not, Var
from logillm.logic.semantics import collect_variables

smanjena_vidljivost = Var("smanjena_vidljivost")
blizu = Var("blizu")
veoma_blizu = Var("veoma_blizu")
brzo_priblizavanje = Var("brzo_priblizavanje")
trazena_brzina_iznad_ogranicenja = Var("trazena_brzina_iznad_ogranicenja")
losi_uslovi = Var("losi_uslovi")
rizik_sudara = Var("rizik_sudara")
nivo_visok = Var("nivo_visok")
nivo_kritican = Var("nivo_kritican")
hitno_kocenje = Var("hitno_kocenje")
usporavanje_potrebno = Var("usporavanje_potrebno")
tempomat_dozvoljen = Var("tempomat_dozvoljen")

KB: list[Formula] = [
    Implies(smanjena_vidljivost, losi_uslovi),
    Implies(And(blizu, brzo_priblizavanje), rizik_sudara),
    Implies(rizik_sudara, nivo_visok),
    Implies(And(rizik_sudara, losi_uslovi), nivo_kritican),
    Implies(And(veoma_blizu, brzo_priblizavanje), nivo_kritican),
    Implies(nivo_kritican, hitno_kocenje),
    Implies(losi_uslovi, usporavanje_potrebno),
    Implies(rizik_sudara, usporavanje_potrebno),
    Implies(losi_uslovi, Not(tempomat_dozvoljen)),
    Implies(rizik_sudara, Not(tempomat_dozvoljen)),
    Implies(trazena_brzina_iznad_ogranicenja, Not(tempomat_dozvoljen)),
]

SENSOR_THRESHOLDS: dict[str, list[Comparison]] = {
    "blizu": [Comparison("udaljenost", "<", 15)],
    "veoma_blizu": [Comparison("udaljenost", "<", 5)],
    "brzo_priblizavanje": [Comparison("relativna_brzina", ">", 5)],
    "smanjena_vidljivost": [Comparison("vidljivost", "<", 50)],
}

SITUATION_VARS = frozenset({"smanjena_vidljivost", "blizu", "veoma_blizu", "brzo_priblizavanje"})
REQUEST_CONTEXT_VARS = frozenset({"trazena_brzina_iznad_ogranicenja"})
DERIVED_VARS = frozenset({"losi_uslovi", "rizik_sudara"})
ASSESSMENT_VARS = frozenset({"nivo_visok", "nivo_kritican"})
ACTION_VARS = frozenset({"hitno_kocenje", "usporavanje_potrebno", "tempomat_dozvoljen"})
PERMISSION_VARS = frozenset({"tempomat_dozvoljen"})
REQUESTABLE_VARS = PERMISSION_VARS

PROPOSITION_NAMES = SITUATION_VARS | REQUEST_CONTEXT_VARS | DERIVED_VARS | ASSESSMENT_VARS | ACTION_VARS
QUERY_TARGETS = PROPOSITION_NAMES - REQUEST_CONTEXT_VARS


def validate_knowledge_base() -> None:
    """Validate the boundaries between sensor propositions, derived propositions and decisions."""
    categories = (SITUATION_VARS, REQUEST_CONTEXT_VARS, DERIVED_VARS, ASSESSMENT_VARS, ACTION_VARS)
    if sum(len(category) for category in categories) != len(PROPOSITION_NAMES):
        raise ValueError("Knowledge-base categories must not overlap.")
    if not PERMISSION_VARS <= ACTION_VARS:
        raise ValueError("Every permission variable must describe an action.")

    threshold_vars = set(SENSOR_THRESHOLDS)
    if threshold_vars != SITUATION_VARS:
        raise ValueError(
            f"Sensor thresholds and situation variables disagree. "
            f"Only in thresholds: {sorted(threshold_vars - SITUATION_VARS)}. "
            f"Only in situation variables: {sorted(SITUATION_VARS - threshold_vars)}."
        )

    kb_vars = set(collect_variables(KB))
    if kb_vars != PROPOSITION_NAMES:
        raise ValueError(
            f"Proposition names and knowledge base disagree. "
            f"Only in KB: {sorted(kb_vars - PROPOSITION_NAMES)}. "
            f"Only in proposition names: {sorted(PROPOSITION_NAMES - kb_vars)}."
        )
