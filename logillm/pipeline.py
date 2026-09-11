import math
from dataclasses import dataclass

from logillm.adas.knowledge_base import (
    BAD_CONDITIONS_MAX_SPEED_KMH,
    KB,
    PERMISSION_VARS,
    SENSOR_THRESHOLDS,
    validate_knowledge_base,
)
from logillm.config import LLMConfig
from logillm.grounding import SensorReadings, ground
from logillm.llm.explain import explain
from logillm.llm.translate import Rejection, translate
from logillm.llm.validate import Query
from logillm.logic.derivation import Step, blocking_conditions, conflict_core, derive, relevant_steps
from logillm.logic.formula import Formula, Implies, Var
from logillm.logic.semantics import Valuation, check_consistency, entails, valuation_to_formulas, variables


@dataclass(frozen=True)
class Decision:
    verdict: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class PipelineResult:
    structured_output: str
    query: Query
    decision: Decision
    explanation: str | None
    explanation_error: str | None = None
    rejections: tuple[Rejection, ...] = ()


def _names(items) -> str:
    return ", ".join(items) or "(ništa)"


def _request_context(query: Query, readings: SensorReadings) -> Valuation:
    if query.speed_kmh is None:
        return {"trazena_brzina_iznad_ogranicenja": False, "trazena_brzina_iznad_bezbjedne": False}

    speed_limit = readings.get("ogranicenje_brzine")
    if (
        isinstance(speed_limit, bool)
        or not isinstance(speed_limit, (int, float))
        or not math.isfinite(speed_limit)
        or speed_limit <= 0
    ):
        raise ValueError("Kada je zadata tražena brzina, potrebno je navesti pozitivno ograničenje brzine.")

    return {
        "trazena_brzina_iznad_ogranicenja": query.speed_kmh > speed_limit,
        "trazena_brzina_iznad_bezbjedne": query.speed_kmh > BAD_CONDITIONS_MAX_SPEED_KMH,
    }


def _speed_evidence(query: Query, readings: SensorReadings) -> tuple[str, ...]:
    if query.speed_kmh is None:
        return ()
    speed_limit = readings["ogranicenje_brzine"]
    return (
        f"tražena brzina: {query.speed_kmh:g} km/h",
        f"ograničenje brzine: {speed_limit:g} km/h",
    )


def _safe_speed_evidence(core: list[Formula]) -> tuple[str, ...]:
    """Return the safe speed for bad conditions when it takes part in the conflict."""
    if any("trazena_brzina_iznad_bezbjedne" in variables(formula) for formula in core):
        return (f"bezbjedna brzina po lošim uslovima: {BAD_CONDITIONS_MAX_SPEED_KMH:g} km/h",)
    return ()


def _entailed_evidence(valuation: Valuation, trace: list[Step], target: str) -> tuple[str, ...]:
    """Return grounded propositions and inference rules that support the target."""
    steps = relevant_steps(trace, target)
    used = {target} if target in valuation else set()
    for step in steps:
        used |= variables(step.rule)

    observed = [name for name, value in sorted(valuation.items()) if value and name in used]
    return (f"sa senzora: {_names(observed)}", *(str(step.rule) for step in steps))


def _not_entailed_evidence(valuation: Valuation, known: Valuation, target: str) -> tuple[str, ...]:
    """Return established propositions and conditions still missing for the target."""
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
    """Return grounded sensor propositions and rules that conflict with a request."""
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


def decide(query: Query, readings: SensorReadings) -> Decision:
    """Evaluate a validated query against sensor readings and the knowledge base."""
    validate_knowledge_base()
    valuation = ground(SENSOR_THRESHOLDS, readings)
    valuation.update(_request_context(query, readings))
    premises = [*KB, *valuation_to_formulas(valuation)]
    if not check_consistency(premises).consistent:
        raise ValueError("Knowledge base and grounded sensor readings are inconsistent.")

    target = Var(query.target)
    known, trace = derive(KB, valuation)

    if query.target in PERMISSION_VARS:
        speed_evidence = _speed_evidence(query, readings)
        if check_consistency([*premises, target]).consistent:
            return Decision(
                "SMIJE",
                (*speed_evidence, "nijedno pravilo to ne zabranjuje u ovoj situaciji"),
            )
        core = conflict_core([*premises, target])
        evidence = (*speed_evidence, *_safe_speed_evidence(core), *_refused_evidence(core, valuation))
        return Decision("NE SMIJE", evidence)

    if query.mode == "claim":
        if entails(premises, target).entailed:
            return Decision("MORA VAŽITI", _entailed_evidence(valuation, trace, query.target))
        return Decision("NE MORA VAŽITI", _not_entailed_evidence(valuation, known, query.target))

    raise ValueError(f"Unsupported query mode and target: {query.mode!r}, {query.target!r}.")


def run_pipeline(utterance: str, readings: SensorReadings, config: LLMConfig) -> PipelineResult:
    """Run structured extraction, validation, formal evaluation and explanation."""
    validate_knowledge_base()
    translation = translate(utterance, config=config)
    query = translation.query
    decision = decide(query, readings)

    try:
        explanation = explain(
            utterance,
            decision.verdict,
            list(decision.evidence),
            config=config,
        ).strip()
    except (RuntimeError, TypeError) as error:
        return PipelineResult(translation.reply, query, decision, None, str(error), translation.rejections)
    return PipelineResult(translation.reply, query, decision, explanation, rejections=translation.rejections)
