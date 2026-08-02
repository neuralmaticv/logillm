import operator

from logillm.facts import Facts
from logillm.rules import Comparison, Rule

OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
}


def evaluate_comparison(comparison: Comparison, facts: Facts) -> bool:
    if comparison.variable not in facts:
        raise ValueError(f"Variable '{comparison.variable}' not found in facts!")

    fact_value = facts[comparison.variable]
    op_func = OPERATORS.get(comparison.operator)

    if op_func is None:
        raise ValueError(f"Operator '{comparison.operator}' is not supported!")

    return op_func(fact_value, comparison.value)


def evaluate_rule(rule, facts: Facts) -> bool:
    return all(evaluate_comparison(cond, facts) for cond in rule.conditions)


def run_engine(rules, facts: Facts) -> tuple[Facts, list[Rule]]:
    trace: list[Rule] = []
    results = facts.copy()

    for rule in rules:
        if evaluate_rule(rule, results):
            results[rule.result_fact] = rule.result_value
            trace.append(rule)

    return results, trace
