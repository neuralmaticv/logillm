from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import product

from logillm.logic.formula import And, Formula, Iff, Implies, Not, Or, Var

Valuation = dict[str, bool]


def evaluate(formula: Formula, valuation: Valuation) -> bool:
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
    names: set[str] = set()
    for formula in formulas:
        names |= variables(formula)
    return sorted(names)


def all_valuations(names: Iterable[str]) -> Iterator[Valuation]:
    ordered = list(names)
    for combination in product([False, True], repeat=len(ordered)):
        yield dict(zip(ordered, combination, strict=True))


def as_formulas(valuation: Valuation) -> list[Formula]:
    return [Var(name) if value else Not(Var(name)) for name, value in valuation.items()]


def satisfy(formulas: Iterable[Formula]) -> Valuation | None:
    formulas = list(formulas)
    for valuation in all_valuations(collect_variables(formulas)):
        if all(evaluate(formula, valuation) for formula in formulas):
            return valuation
    return None


@dataclass(frozen=True)
class EntailmentResult:
    entailed: bool
    countermodel: Valuation | None
    premises: tuple[Formula, ...]
    conclusion: Formula


def entails(premises: Iterable[Formula], conclusion: Formula) -> EntailmentResult:
    premises = tuple(premises)
    names = collect_variables([*premises, conclusion])

    for valuation in all_valuations(names):
        premises_hold = all(evaluate(premise, valuation) for premise in premises)
        if premises_hold and not evaluate(conclusion, valuation):
            return EntailmentResult(False, valuation, premises, conclusion)

    return EntailmentResult(True, None, premises, conclusion)


@dataclass(frozen=True)
class ConsistencyResult:
    consistent: bool
    model: Valuation | None
    formulas: tuple[Formula, ...]


def consistency(formulas: Iterable[Formula]) -> ConsistencyResult:
    formulas = tuple(formulas)
    model = satisfy(formulas)
    return ConsistencyResult(model is not None, model, formulas)


def is_satisfiable(formula: Formula) -> bool:
    return satisfy([formula]) is not None


def is_tautology(formula: Formula) -> bool:
    return entails([], formula).entailed


def is_contradiction(formula: Formula) -> bool:
    return not is_satisfiable(formula)


@dataclass(frozen=True)
class TruthTableRow:
    valuation: Valuation
    value: bool


def truth_table(formula: Formula) -> list[TruthTableRow]:
    names = sorted(variables(formula))
    return [TruthTableRow(valuation, evaluate(formula, valuation)) for valuation in all_valuations(names)]


def format_valuation(valuation: Valuation, only_true: bool = False) -> str:
    items = sorted(valuation.items())
    if only_true:
        return ", ".join(name for name, value in items if value)
    return ", ".join(f"{name}={'T' if value else 'F'}" for name, value in items)
