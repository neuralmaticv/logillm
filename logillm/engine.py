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


def evaluate_rule(rule: Rule, facts: Facts) -> bool:
    return all(evaluate_comparison(cond, facts) for cond in rule.conditions)


def run_engine(rules: list[Rule], facts: Facts) -> tuple[Facts, list[Rule]]:
    trace: list[Rule] = []
    results = facts.copy()
    decided: set[str] = set()

    for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
        if evaluate_rule(rule, results):
            trace.append(rule)
            if rule.result_fact not in decided:
                results[rule.result_fact] = rule.result_value
                decided.add(rule.result_fact)

    return results, trace
