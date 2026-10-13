"""Bot 1 — Market Scout

Pulls live quotes, volume, and catalysts before open every day.
"""


def scan(tickers: list[str]) -> dict:
    """Return latest quote, volume, and any catalyst within 48h for each ticker."""
    results = {}
    for t in tickers:
        results[t] = {
            "ticker": t,
            "last": None,          # wire to market data feed
            "volume": None,
            "catalyst": None,      # wire to news wire
            "hours_since": None,
        }
    return results
