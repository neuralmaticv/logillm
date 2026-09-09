from logillm.engine import evaluate_comparison
from logillm.facts import Facts
from logillm.logic.semantics import Valuation
from logillm.rules import Comparison


def ground(thresholds: dict[str, list[Comparison]], facts: Facts) -> Valuation:
    # numeric sensor readings into truth values of propositional vars
    return {
        name: all(evaluate_comparison(comparison, facts) for comparison in comparisons)
        for name, comparisons in thresholds.items()
    }
