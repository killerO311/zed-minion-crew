"""Bot 2 — Research

Deep dives on any name Zed flags — debt, shorts, catalysts, full rabbit hole.
"""


def deep_dive(ticker: str) -> dict:
    """Pull debt load, short interest, catalysts, and valuation for one name."""
    return {
        "ticker": ticker,
        "debt": None,
        "short_interest_pct": None,
        "catalysts": [],
        "valuation": None,
        "notes": "",
    }
