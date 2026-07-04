from enum import StrEnum


class ThreatLevel(StrEnum):
    """Level of threat"""

    LOW = "NIZAK"
    HIGH = "VISOK"
    CRITICAL = "KRITIČAN"


Facts = dict[str, float | ThreatLevel]
