from dataclasses import dataclass

from logillm.adas.knowledge_base import KB, SENSOR_THRESHOLDS
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
    explanation: str


def _names(items) -> str:
    return ", ".join(items) or "(ništa)"


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
        if isinstance(formula, Var) and formula.name in valuation and valuation[formula.name]
    ]
    rules = [str(formula) for formula in core if isinstance(formula, Implies)]
    return (f"sa senzora: {_names(observed)}", *rules)


def decide(query: Query, facts: Facts) -> Decision:
    """Evaluate a validated query against grounded sensor facts and the knowledge base."""
    valuation = ground(SENSOR_THRESHOLDS, facts)
    premises = [*KB, *as_formulas(valuation)]
    target = Var(query.target)
    known, trace = derive(KB, valuation)

    if query.mode == "claim":
        if entails(premises, target).entailed:
            return Decision("MORA VAŽITI", _entailed_evidence(valuation, trace, query.target))
        return Decision("NE MORA VAŽITI", _not_entailed_evidence(valuation, known, query.target))

    if consistency([*premises, target]).consistent:
        return Decision("SMIJE", ("nijedno pravilo to ne zabranjuje u ovoj situaciji",))

    core = conflict_core([*premises, target])
    return Decision("NE SMIJE", _refused_evidence(core, valuation))


def run_pipeline(utterance: str, facts: Facts, config: LLMConfig) -> PipelineResult:
    """Run translation, validation, formal evaluation and explanation."""
    translation = translate(utterance, config=config)
    query = validate(translation)
    decision = decide(query, facts)
    explanation = explain(
        utterance,
        decision.verdict,
        list(decision.evidence),
        config=config,
    ).strip()
    return PipelineResult(translation, query, decision, explanation)
