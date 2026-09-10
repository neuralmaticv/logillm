from dataclasses import dataclass

from logillm.facts import Facts


@dataclass(frozen=True)
class Scenario:
    description: str
    facts: Facts


SMANJENA_VIDLJIVOST_I_RIZIK = Scenario(
    "smanjena vidljivost, vozilo je blizu i brzo mu se približavamo",
    {
        "udaljenost": 12,
        "relativna_brzina": 6,
        "vidljivost": 30,
        "ogranicenje_brzine": 130,
    },
)

RIZIK_PRI_DOBROJ_VIDLJIVOSTI = Scenario(
    "dobra vidljivost, vozilo je blizu i brzo mu se približavamo",
    {
        "udaljenost": 12,
        "relativna_brzina": 6,
        "vidljivost": 500,
        "ogranicenje_brzine": 130,
    },
)

KRITICNA_UDALJENOST = Scenario(
    "dobra vidljivost, vozilo je veoma blizu i brzo mu se približavamo",
    {
        "udaljenost": 3,
        "relativna_brzina": 10,
        "vidljivost": 500,
        "ogranicenje_brzine": 130,
    },
)

SMANJENA_VIDLJIVOST_BEZ_RIZIKA = Scenario(
    "smanjena vidljivost, vozilo ostaje na sigurnoj udaljenosti",
    {
        "udaljenost": 42,
        "relativna_brzina": 0,
        "vidljivost": 30,
        "ogranicenje_brzine": 130,
    },
)

SIGURNA_UDALJENOST = Scenario(
    "dobra vidljivost, vozilo ostaje na sigurnoj udaljenosti",
    {
        "udaljenost": 42,
        "relativna_brzina": 0,
        "vidljivost": 500,
        "ogranicenje_brzine": 130,
    },
)

ALL_SCENARIOS = (
    SMANJENA_VIDLJIVOST_I_RIZIK,
    RIZIK_PRI_DOBROJ_VIDLJIVOSTI,
    KRITICNA_UDALJENOST,
    SMANJENA_VIDLJIVOST_BEZ_RIZIKA,
    SIGURNA_UDALJENOST,
)

LLM_SCENARIOS = (
    SMANJENA_VIDLJIVOST_I_RIZIK,
    KRITICNA_UDALJENOST,
    SIGURNA_UDALJENOST,
)
