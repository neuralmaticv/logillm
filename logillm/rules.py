from dataclasses import dataclass

from logillm.facts import ThreatLevel


@dataclass(frozen=True)
class Comparison:
    variable: str
    operator: str  # < | > | <= | >= | ==
    value: float


@dataclass(frozen=True)
class Rule:
    name: str
    conditions: list[Comparison]
    result_fact: str
    result_value: float | ThreatLevel


THREAT_RULES: list[Rule] = [
    Rule(
        name="Critical Threat",
        conditions=[Comparison(variable="udaljenost", operator="<", value=5)],
        result_fact="nivo_prijetnje",
        result_value=ThreatLevel.CRITICAL,
    ),
    Rule(
        name="High Threat",
        conditions=[
            Comparison(variable="udaljenost", operator=">=", value=5),
            Comparison(variable="udaljenost", operator="<", value=15),
        ],
        result_fact="nivo_prijetnje",
        result_value=ThreatLevel.HIGH,
    ),
    Rule(
        name="Low Threat",
        conditions=[Comparison(variable="relativna_brzina", operator=">", value=5)],
        result_fact="nivo_prijetnje",
        result_value=ThreatLevel.LOW,
    ),
]
