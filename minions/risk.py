"""Bot 3 — Risk

Watches Zed's positions. Flags when a thesis breaks or a stop's close.
"""


def check_positions(positions: list[dict]) -> list[str]:
    """Return alert strings for any position whose thesis is breaking."""
    alerts = []
    for p in positions:
        if p.get("unrealized_pct", 0) <= -10:
            alerts.append(f"{p['ticker']}: down {p['unrealized_pct']}% — thesis check")
        if p.get("days_to_catalyst", 99) > 14 and p.get("unrealized_pct", 0) < 0:
            alerts.append(f"{p['ticker']}: no catalyst inside two weeks and red — cut candidate")
    return alerts
