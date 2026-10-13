"""Bot 4 — News Wire

CPI, earnings, Fed — anything that moves the tape inside the hour.
"""


def watch(events: list[dict]) -> list[str]:
    """Return headlines that hit inside the last hour."""
    return [e["headline"] for e in events if e.get("minutes_ago", 999) <= 60]
