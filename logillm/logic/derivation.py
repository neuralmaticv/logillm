from dataclasses import dataclass

from logillm.logic.formula import And, Formula, Implies, Not, Or, Var
from logillm.logic.semantics import Valuation, check_consistency, variables


@dataclass(frozen=True)
class Step:
    rule: Formula
    variable: str
    value: bool


def is_established(formula: Formula, known: Valuation) -> bool:
    """Return whether the known values establish a formula as true.

    A variable with no known value counts as not established.
    """
    match formula:
        case Var(name):
            return known.get(name) is True
        case Not(Var(name)):
            return known.get(name) is False
        case And(left, right):
            return is_established(left, known) and is_established(right, known)
        case Or(left, right):
            return is_established(left, known) or is_established(right, known)
        case _:
            raise TypeError(f"Forward chaining cannot use {type(formula).__name__} in a rule body.")


def _rule_parts(rule: Formula) -> tuple[Formula, str, bool] | None:
    """Split a usable rule into its body, derived variable and truth value."""
    match rule:
        case Implies(body, Var(name)):
            return body, name, True
        case Implies(body, Not(Var(name))):
            return body, name, False

    return None


def derive(kb: list[Formula], facts: Valuation, max_passes: int = 20) -> tuple[Valuation, list[Step]]:
    """Apply forward chaining until no new values can be derived.

    Return all known values and the ordered steps that produced them. Only rules
    of the form `body -> variable` are usable. `max_passes` is a safety bound on
    the number of passes through the knowledge base.
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
            if name in known or not is_established(body, known):
                continue
            known[name] = value
            trace.append(Step(rule, name, value))
            fired = True
        if not fired:
            break

    return known, trace


def relevant_steps(steps: list[Step], target: str) -> list[Step]:
    """Keep only the derivation steps on which the target depends.

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
    """Collect unestablished conditions along rule paths leading to the target."""

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
    """Return a subset-minimal group of formulas responsible for inconsistency.

    Remove one formula at a time while the inconsistency survives. The result
    depends on input order and need not have minimum cardinality. Return an empty
    list when the complete set is consistent.
    """
    if check_consistency(formulas).consistent:
        return []

    core = list(formulas)
    index = len(core) - 1

    while index >= 0:
        candidate = core[:index] + core[index + 1 :]
        if not check_consistency(candidate).consistent:
            core = candidate
        index -= 1

    return core
