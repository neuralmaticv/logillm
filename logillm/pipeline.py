import math
from dataclasses import dataclass

from logillm.adas.knowledge_base import (
    KB,
    PERMISSION_VARS,
    SENSOR_THRESHOLDS,
    validate_vocabulary,
)
from logillm.config import LLMConfig
from logillm.facts import Facts
from logillm.grounding import ground
from logillm.llm.explain import explain
from logillm.llm.translate import translate
from logillm.llm.validate import Query, validate
from logillm.logic.derivation import Step, blocking_conditions, conflict_core, derive, relevant
from logillm.logic.formula import Formula, Implies, Var
from logillm.logic.semantics import Valuation, as_formulas, consistency, entails, variables


@dataclass(frozen=True)
class Decision:
    verdict: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class PipelineResult:
    translation: str
    query: Query
    decision: Decision
    explanation: str | None
    explanation_error: str | None = None


def _names(items) -> str:
    return ", ".join(items) or "(ništa)"


def _request_context(query: Query, facts: Facts) -> Valuation:
    if query.speed_kmh is None:
        return {"trazena_brzina_iznad_ogranicenja": False}

    speed_limit = facts.get("ogranicenje_brzine")
    if (
        isinstance(speed_limit, bool)
        or not isinstance(speed_limit, (int, float))
        or not math.isfinite(speed_limit)
        or speed_limit <= 0
    ):
        raise ValueError("Za postavljanje brzine tempomata potrebno je navesti pozitivno ograničenje brzine.")

    return {"trazena_brzina_iznad_ogranicenja": query.speed_kmh > speed_limit}


def _speed_evidence(query: Query, facts: Facts) -> tuple[str, ...]:
    if query.speed_kmh is None:
        return ()
    speed_limit = facts["ogranicenje_brzine"]
    return (
        f"tražena brzina: {query.speed_kmh:g} km/h",
        f"ograničenje brzine: {speed_limit:g} km/h",
    )


def _entailed_evidence(valuation: Valuation, trace: list[Step], target: str) -> tuple[str, ...]:
    """Rules that led to the target, and only the readings those rules use."""
    steps = relevant(trace, target)
    used = {target} if target in valuation else set()
    for step in steps:
        used |= variables(step.rule)

    observed = [name for name, value in sorted(valuation.items()) if value and name in used]
    return (f"sa senzora: {_names(observed)}", *(str(step.rule) for step in steps))


def _not_entailed_evidence(valuation: Valuation, known: Valuation, target: str) -> tuple[str, ...]:
    """What was established and which conditions for the target are missing."""
    derived = [name for name, value in sorted(known.items()) if value and name not in valuation]
    missing = sorted(blocking_conditions(KB, target, known))

    evidence: list[str] = []
    if derived:
        evidence.append(f"utvrđeno je: {_names(derived)}")
    evidence.append(f"nije utvrđeno: {target}")
    if missing:
        evidence.append(f"jer nije ispunjeno: {_names(missing)}")
    return tuple(evidence)


def _refused_evidence(core: list[Formula], valuation: Valuation) -> tuple[str, ...]:
    """Readings and rules that cause a conflict."""
    observed = [
        formula.name
        for formula in core
        if (
            isinstance(formula, Var)
            and formula.name in SENSOR_THRESHOLDS
            and formula.name in valuation
            and valuation[formula.name]
        )
    ]
    rules = [str(formula) for formula in core if isinstance(formula, Implies)]
    sensor_evidence = (f"sa senzora: {_names(observed)}",) if observed else ()
    return (*sensor_evidence, *rules)


def decide(query: Query, facts: Facts) -> Decision:
    """Evaluate a validated query against grounded sensor facts and the knowledge base."""
    validate_vocabulary()
    valuation = ground(SENSOR_THRESHOLDS, facts)
    valuation.update(_request_context(query, facts))
    premises = [*KB, *as_formulas(valuation)]
    if not consistency(premises).consistent:
        raise ValueError("Knowledge base and grounded sensor facts are inconsistent.")

    target = Var(query.target)
    known, trace = derive(KB, valuation)

    if query.target in PERMISSION_VARS:
        speed_evidence = _speed_evidence(query, facts)
        if consistency([*premises, target]).consistent:
            return Decision(
                "SMIJE",
                (*speed_evidence, "nijedno pravilo to ne zabranjuje u ovoj situaciji"),
            )
        core = conflict_core([*premises, target])
        return Decision("NE SMIJE", (*speed_evidence, *_refused_evidence(core, valuation)))

    if query.mode == "claim":
        if entails(premises, target).entailed:
            return Decision("MORA VAŽITI", _entailed_evidence(valuation, trace, query.target))
        return Decision("NE MORA VAŽITI", _not_entailed_evidence(valuation, known, query.target))

    raise ValueError(f"Unsupported query mode and target: {query.mode!r}, {query.target!r}.")


def run_pipeline(utterance: str, facts: Facts, config: LLMConfig) -> PipelineResult:
    """Run translation, validation, formal evaluation and explanation."""
    validate_vocabulary()
    translation = translate(utterance, config=config)
    query = validate(translation)
    decision = decide(query, facts)
    try:
        explanation = explain(
            utterance,
            decision.verdict,
            list(decision.evidence),
            config=config,
        ).strip()
    except (RuntimeError, TypeError) as error:
        return PipelineResult(translation, query, decision, None, str(error))
    return PipelineResult(translation, query, decision, explanation)
