from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import product

from logillm.logic.formula import And, Formula, Iff, Implies, Not, Or, Var

Valuation = dict[str, bool]


def evaluate(formula: Formula, valuation: Valuation) -> bool:
    """Evaluate a formula under a complete valuation."""
    match formula:
        case Var(name):
            if name not in valuation:
                raise ValueError(f"Variable '{name}' has no value in the valuation!")
            return valuation[name]
        case Not(operand):
            return not evaluate(operand, valuation)
        case And(left, right):
            return evaluate(left, valuation) and evaluate(right, valuation)
        case Or(left, right):
            return evaluate(left, valuation) or evaluate(right, valuation)
        case Implies(left, right):
            return (not evaluate(left, valuation)) or evaluate(right, valuation)
        case Iff(left, right):
            return evaluate(left, valuation) == evaluate(right, valuation)
        case _:
            raise TypeError(f"Unsupported formula type: {type(formula).__name__}")


def variables(formula: Formula) -> set[str]:
    """Return the proposition names used in a formula."""
    match formula:
        case Var(name):
            return {name}
        case Not(operand):
            return variables(operand)
        case And(left, right) | Or(left, right) | Implies(left, right) | Iff(left, right):
            return variables(left) | variables(right)
        case _:
            raise TypeError(f"Unsupported formula type: {type(formula).__name__}")


def collect_variables(formulas: Iterable[Formula]) -> list[str]:
    """Return the sorted proposition names used across multiple formulas."""
    names: set[str] = set()
    for formula in formulas:
        names |= variables(formula)
    return sorted(names)


def all_valuations(names: Iterable[str]) -> Iterator[Valuation]:
    """Generate every truth-value assignment for the given proposition names."""
    ordered = list(names)
    for combination in product([False, True], repeat=len(ordered)):
        yield dict(zip(ordered, combination, strict=True))


def valuation_to_formulas(valuation: Valuation) -> list[Formula]:
    """Represent a valuation as positive or negated atomic formulas."""
    return [Var(name) if value else Not(Var(name)) for name, value in valuation.items()]


def find_model(formulas: Iterable[Formula]) -> Valuation | None:
    """Return the first model that satisfies all formulas, or None if they are unsatisfiable."""
    formulas = list(formulas)
    for valuation in all_valuations(collect_variables(formulas)):
        if all(evaluate(formula, valuation) for formula in formulas):
            return valuation
    return None


@dataclass(frozen=True)
class EntailmentResult:
    """Result of an entailment check with an optional countermodel."""

    entailed: bool
    countermodel: Valuation | None


def entails(premises: Iterable[Formula], conclusion: Formula) -> EntailmentResult:
    """Check whether every model of the premises also satisfies the conclusion."""
    premises = tuple(premises)
    names = collect_variables([*premises, conclusion])

    for valuation in all_valuations(names):
        premises_hold = all(evaluate(premise, valuation) for premise in premises)
        if premises_hold and not evaluate(conclusion, valuation):
            return EntailmentResult(entailed=False, countermodel=valuation)

    return EntailmentResult(entailed=True, countermodel=None)


@dataclass(frozen=True)
class ConsistencyResult:
    """Result of a consistency check with an optional satisfying model."""

    model: Valuation | None

    @property
    def consistent(self) -> bool:
        """Return whether the checked formulas share a model."""
        return self.model is not None


def check_consistency(formulas: Iterable[Formula]) -> ConsistencyResult:
    """Check whether formulas share a model and return it when one exists."""
    return ConsistencyResult(model=find_model(formulas))


@dataclass(frozen=True)
class TruthTableRow:
    """One valuation and the resulting truth value of a formula."""

    valuation: Valuation
    value: bool


def truth_table(formula: Formula) -> list[TruthTableRow]:
    """Return the complete truth table for a formula."""
    names = sorted(variables(formula))
    return [TruthTableRow(valuation, evaluate(formula, valuation)) for valuation in all_valuations(names)]


def format_valuation(valuation: Valuation, only_true: bool = False) -> str:
    """Format a valuation for command-line and demo output."""
    items = sorted(valuation.items())
    if only_true:
        return ", ".join(name for name, value in items if value)
    return ", ".join(f"{name}={'T' if value else 'F'}" for name, value in items)
