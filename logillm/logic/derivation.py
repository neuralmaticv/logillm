from dataclasses import dataclass

from logillm.logic.formula import And, Formula, Implies, Not, Or, Var
from logillm.logic.semantics import Valuation, consistency, variables


@dataclass(frozen=True)
class Step:
    rule: Formula
    variable: str
    value: bool


def holds(formula: Formula, known: Valuation) -> bool:
    """True when what is already known makes the formula true.

    A variable with no known value counts as not established.
    """
    match formula:
        case Var(name):
            return known.get(name) is True
        case Not(Var(name)):
            return known.get(name) is False
        case And(left, right):
            return holds(left, known) and holds(right, known)
        case Or(left, right):
            return holds(left, known) or holds(right, known)
        case _:
            raise TypeError(f"Forward chaining cannot use {type(formula).__name__} in a rule body.")


def _rule_parts(rule: Formula) -> tuple[Formula, str, bool] | None:
    """Splits a rule into body, derived variable and its value, if it is usable."""
    match rule:
        case Implies(body, Var(name)):
            return body, name, True
        case Implies(body, Not(Var(name))):
            return body, name, False
    return None


def derive(kb: list[Formula], facts: Valuation, max_passes: int = 20) -> tuple[Valuation, list[Step]]:
    """Forward chaining: repeats passes over the rules until nothing new appears.

    Returns everything now known, and the ordered steps that got there. Only
    rules of the form `body -> variable` are usable, which is what the ADAS
    knowledge base is made of. max_passes stops a rule that feeds itself.
    """
    known = dict(facts)
    trace: list[Step] = []

    for _ in range(max_passes):
        fired = False
        for rule in kb:
            parts = _rule_parts(rule)
            if parts is None:
                continue
            body, name, value = parts
            if name in known or not holds(body, known):
                continue
            known[name] = value
            trace.append(Step(rule, name, value))
            fired = True
        if not fired:
            break

    return known, trace


def relevant(steps: list[Step], target: str) -> list[Step]:
    """Keeps only the steps the target actually depends on.

    Walks the trace backwards from the target, collecting every step whose
    result is still needed. Rules that fired but led elsewhere are dropped.
    """
    needed = {target}
    chosen: list[Step] = []

    for step in reversed(steps):
        if step.variable in needed:
            chosen.append(step)
            needed |= variables(step.rule)

    return list(reversed(chosen))


def blocking_conditions(kb: list[Formula], target: str, known: Valuation) -> set[str]:
    """Conditions that stand between what is known and the target"""

    def walk(name: str, seen: frozenset[str]) -> set[str]:
        if known.get(name) is True:
            return set()
        if name in seen:
            return {name}

        bodies = [parts[0] for rule in kb if (parts := _rule_parts(rule)) and parts[1] == name and parts[2]]
        if not bodies:
            return {name}

        missing: set[str] = set()
        for body in bodies:
            for variable in variables(body):
                if known.get(variable) is not True:
                    missing |= walk(variable, seen | {name})
        return missing

    return walk(target, frozenset())


def conflict_core(formulas: list[Formula]) -> list[Formula]:
    """The formulas that make a set contradictory, with the rest removed.

    Drops one formula at a time and keeps the drop whenever the contradiction
    survives without it. Returns an empty list for a set that is consistent.
    """
    if consistency(formulas).consistent:
        return []

    core = list(formulas)
    index = len(core) - 1
    while index >= 0:
        candidate = core[:index] + core[index + 1 :]
        if not consistency(candidate).consistent:
            core = candidate
        index -= 1

    return core
