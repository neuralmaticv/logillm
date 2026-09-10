import operator
from dataclasses import dataclass

from logillm.logic.semantics import Valuation

SensorReadings = dict[str, float]


@dataclass(frozen=True)
class Comparison:
    """A numeric comparison used to ground a sensor proposition."""

    variable: str
    operator: str
    value: float


OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
}


def evaluate_comparison(comparison: Comparison, readings: SensorReadings) -> bool:
    """Evaluate one numeric comparison against the sensor readings."""
    if comparison.variable not in readings:
        raise ValueError(f"Variable '{comparison.variable}' not found in sensor readings!")

    operation = OPERATORS.get(comparison.operator)
    if operation is None:
        raise ValueError(f"Operator '{comparison.operator}' is not supported!")

    return operation(readings[comparison.variable], comparison.value)


def ground(thresholds: dict[str, list[Comparison]], readings: SensorReadings) -> Valuation:
    """Ground numeric sensor readings into truth values for sensor propositions."""
    return {
        name: all(evaluate_comparison(comparison, readings) for comparison in comparisons)
        for name, comparisons in thresholds.items()
    }
